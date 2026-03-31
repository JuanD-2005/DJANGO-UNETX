# Unet/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.core.mail import EmailMessage
from django.conf import settings

from .models import Profile, Post, Like, Relationship, DirectMessage, Mention
from .forms import UserRegisterForm, PostForm, ProfileUpdateForm, UserUpdateForm


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS PRIVADOS
# Funciones de soporte que no son vistas. Prefijo _ indica uso interno.
# ══════════════════════════════════════════════════════════════════════════════

def _process_mentions(post: Post) -> None:
    """
    Parsea @menciones del contenido y crea objetos Mention en bulk.
    bulk_create + ignore_conflicts delega la deduplicación a Postgres
    usando el unique_together definido en el modelo — cero loops extra.
    """
    usernames = post.get_mentions()
    if not usernames:
        return
    mentioned_users = User.objects.filter(username__in=usernames)
    Mention.objects.bulk_create(
        [Mention(post=post, mentioned_user=u) for u in mentioned_users],
        ignore_conflicts=True,
    )


def _send_email_async(subject: str, body: str, to: list[str]) -> None:
    """
    Wrapper de email con fail_silently=True.
    El email nunca debe cortar el flujo principal de la aplicación.
    En producción (Fase 3) esto se reemplaza por Celery + SES/Resend.
    """
    if not to or not any(to):
        return
    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=to,
        ).send(fail_silently=True)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — REGISTRO
# ══════════════════════════════════════════════════════════════════════════════

def register(request):
    """
    FBV deliberada: UserRegisterForm tiene lógica custom (validación de email
    único, etc.). Un CreateView genérico requeriría más overrides que código
    ahorra — punto de equilibrio donde FBV es más limpio.
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'¡Cuenta creada para @{user.username}! Ya puedes iniciar sesión.')
            return redirect('login')
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = UserRegisterForm()
    return render(request, 'twitter/register.html', {'form': form})


# ══════════════════════════════════════════════════════════════════════════════
# FEED PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def home(request):
    """
    FBV deliberada: mezcla creación de Post (POST) + listado paginado (GET).
    Separar en CreateView + ListView requeriría lógica de redirección entre
    vistas que complica más de lo que simplifica.

    ── Anti-N+1 Strategy ───────────────────────────────────────────────────────
    Sin optimizar, Django hace 1 query por post para obtener user, y otra
    por user para obtener profile → O(2n) queries en el feed.

    Con select_related('user__profile', 'retweet_of__user__profile'):
      → 1 sola query con JOINs resuelve user + profile + post original.

    Con Prefetch('likes'): → 1 query extra para TODOS los likes del feed.

    Total: 3 queries fijas independientemente del tamaño del feed. ✓
    ────────────────────────────────────────────────────────────────────────────
    """
    # IDs de usuarios seguidos (query plana, sin traer objetos User completos)
    following_ids = Relationship.objects.filter(
        from_user=request.user
    ).values_list('to_user_id', flat=True)

    posts_qs = (
        Post.objects
        .filter(Q(user_id__in=following_ids) | Q(user=request.user))
        .select_related(
            'user',
            'user__profile',
            'retweet_of',
            'retweet_of__user',
            'retweet_of__user__profile',
        )
        .prefetch_related(
            Prefetch('likes', queryset=Like.objects.only('user_id', 'post_id'))
        )
        .order_by('-timestamp')
    )

    paginator = Paginator(posts_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Set de IDs de posts ya likeados por el usuario actual en esta página.
    # Permite al template hacer {% if post.id in liked_post_ids %} en O(1).
    liked_post_ids = set(
        Like.objects.filter(
            user=request.user,
            post_id__in=[p.id for p in page_obj.object_list],
        ).values_list('post_id', flat=True)
    )

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            _process_mentions(post)
            messages.success(request, '¡Post publicado!')
            return redirect('home')
        messages.error(request, 'No se pudo publicar el post.')
    else:
        form = PostForm()

    # Sugerencias: excluye al usuario actual y a quienes ya sigue.
    # annotate + Count evita N+1 al calcular num_followers en Python.
    suggested_users = (
        User.objects
        .exclude(id=request.user.id)
        .exclude(id__in=following_ids)
        .select_related('profile')
        .annotate(num_followers=Count('related_to'))
        .order_by('-num_followers')[:5]
    )

    return render(request, 'twitter/newsfeed.html', {
        'page_obj': page_obj,
        'form': form,
        'suggested_users': suggested_users,
        'liked_post_ids': liked_post_ids,
    })


# ══════════════════════════════════════════════════════════════════════════════
# POSTS — DELETE / LIKE / RETWEET
# ══════════════════════════════════════════════════════════════════════════════

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    CBV: DeleteView maneja GET (confirmación) + POST (borrado) + redirect.
    UserPassesTestMixin bloquea la vista ANTES de ejecutar cualquier lógica
    si test_func() retorna False — más seguro que un if dentro de la FBV.

    FIX DE SEGURIDAD: La FBV original no verificaba dueño del post.
    Cualquier usuario autenticado podía borrar posts ajenos haciendo
    POST a /delete/<id>/.
    """
    model = Post
    template_name = 'twitter/post_confirm_delete.html'
    success_url = reverse_lazy('home')
    pk_url_kwarg = 'post_id'

    def test_func(self):
        """Solo el dueño del post puede borrarlo."""
        return self.request.user == self.get_object().user

    def form_valid(self, form):
        messages.success(self.request, 'Post eliminado.')
        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(self.request, 'No puedes eliminar posts de otros usuarios.')
        return redirect('home')


@login_required
def like_post(request, post_id):
    """
    FBV: Toggle atómico de like usando get_or_create.

    Por qué get_or_create y no un if/else:
    → Es atómico a nivel de BD (SELECT + INSERT en una transacción).
    → Evita race condition si el usuario hace doble-click rápido.
    → El unique_together del modelo es la última línea de defensa.
    """
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    # Redirige a la página de donde vino (feed, perfil, etc.)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def retweet(request, post_id):
    """
    FBV: Crea un Post que referencia al original vía retweet_of.

    FIX: La vista original usaba el campo 'retweet' (nombre viejo)
    que no existe en el modelo refactorizado → crasheaba en producción.

    get_or_create previene retweets duplicados del mismo usuario
    sobre el mismo post, respaldado por un posible unique_together futuro.
    """
    original_post = get_object_or_404(Post, id=post_id)

    if original_post.user == request.user:
        messages.warning(request, 'No puedes retweetear tu propio post.')
        return redirect('home')

    _, created = Post.objects.get_or_create(
        user=request.user,
        retweet_of=original_post,
        defaults={'content': original_post.content},
    )
    if created:
        messages.success(request, 'Retweet publicado.')
    else:
        messages.info(request, 'Ya retweeteaste este post.')

    return redirect('home')


# ══════════════════════════════════════════════════════════════════════════════
# PERFIL
# ══════════════════════════════════════════════════════════════════════════════

class ProfileView(LoginRequiredMixin, DetailView):
    """
    CBV: DetailView es ideal — muestra 1 objeto con contexto enriquecido.

    ── Anti-N+1 Strategy ───────────────────────────────────────────────────────
    NO hacemos prefetch_related('posts') en get_queryset() porque los posts
    se paginan: prefetchar todos cargaría la historia completa en memoria.
    En su lugar, los posts del perfil tienen su propio queryset optimizado
    en get_context_data() con su propio select_related.
    ────────────────────────────────────────────────────────────────────────────
    """
    model = User
    template_name = 'twitter/profile.html'
    context_object_name = 'user_profile'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        # Solo necesitamos el User + su Profile en 1 JOIN
        return User.objects.select_related('profile')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_profile = self.object

        # Posts paginados con sus propios JOINs — separado del queryset del User
        posts_qs = (
            Post.objects
            .filter(user=user_profile)
            .select_related('user', 'user__profile', 'retweet_of', 'retweet_of__user')
            .prefetch_related(
                Prefetch('likes', queryset=Like.objects.only('user_id', 'post_id'))
            )
            .order_by('-timestamp')
        )
        paginator = Paginator(posts_qs, 10)
        page_obj = paginator.get_page(self.request.GET.get('page', 1))

        # exists() es más eficiente que count() > 0 o filter().first()
        is_following = Relationship.objects.filter(
            from_user=self.request.user,
            to_user=user_profile,
        ).exists()

        suggested_users = (
            User.objects
            .exclude(id=self.request.user.id)
            .select_related('profile')
            .annotate(num_followers=Count('related_to'))
            .order_by('-num_followers')[:5]
        )

        ctx.update({
            'page_obj': page_obj,
            'is_following': is_following,
            'suggested_users': suggested_users,
            # Usamos las properties del modelo — no hacemos count() extra aquí
            'followers_count': user_profile.profile.followers_count,
            'following_count': user_profile.profile.following_count,
        })
        return ctx


@login_required
def editar(request):
    """
    FBV deliberada: dos formularios simultáneos (UserUpdateForm + ProfileUpdateForm).
    Un FormView o UpdateView solo gestiona 1 form por defecto. Agregar el segundo
    requeriría overrides de get_form, form_valid, get_context_data que duplican
    el código que ya tenemos aquí de forma legible.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('profile', username=request.user.username)
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    return render(request, 'twitter/editar.html', {'u_form': u_form, 'p_form': p_form})


# ══════════════════════════════════════════════════════════════════════════════
# FOLLOW / UNFOLLOW
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def follow(request, username):
    """
    FBV: Acción pura (no renderiza template) → CBV no aporta nada aquí.

    FIX: La vista original hacía Relationship(...).save() directamente.
    Con unique_together en el modelo, si el usuario hacía doble-submit
    obtenía un IntegrityError 500. get_or_create es atómico y seguro.
    """
    to_user = get_object_or_404(User, username=username)

    if to_user == request.user:
        messages.warning(request, 'No puedes seguirte a ti mismo.')
        return redirect('profile', username=username)

    _, created = Relationship.objects.get_or_create(
        from_user=request.user,
        to_user=to_user,
    )
    if created:
        messages.success(request, f'Ahora sigues a @{username}.')
        _send_email_async(
            subject='Nuevo seguidor en UnetX',
            body=(
                f'Hola {to_user.first_name or to_user.username},\n\n'
                f'@{request.user.username} ha comenzado a seguirte.'
            ),
            to=[to_user.email] if to_user.email else [],
        )
    else:
        messages.info(request, f'Ya sigues a @{username}.')

    return redirect('profile', username=username)


@login_required
def unfollow(request, username):
    """
    FIX: La vista original usaba .get() sin try/except → DoesNotExist 500
    si la relación no existía. .delete() sobre un queryset filtrado
    retorna (count, {}) y nunca lanza excepción.
    """
    to_user = get_object_or_404(User, username=username)
    deleted_count, _ = Relationship.objects.filter(
        from_user=request.user,
        to_user=to_user,
    ).delete()

    if deleted_count:
        messages.success(request, f'Dejaste de seguir a @{username}.')
    else:
        messages.warning(request, f'No seguías a @{username}.')

    return redirect('profile', username=username)


# ══════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA
# ══════════════════════════════════════════════════════════════════════════════

class BuscarUsuariosView(ListView):
    """
    CBV: ListView gestiona la paginación automáticamente con paginate_by.
    La búsqueda se inyecta en get_queryset() — patrón estándar de Django.
    No requiere LoginRequired: la búsqueda puede ser pública.
    """
    model = User
    template_name = 'twitter/buscar.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return User.objects.none()  # Evita cargar todos los usuarios si no hay búsqueda
        return (
            User.objects
            .filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
            .select_related('profile')
            .order_by('username')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '')
        return ctx


# ══════════════════════════════════════════════════════════════════════════════
# MENSAJES DIRECTOS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def send_message(request):
    """
    FBV: Lógica de negocio personalizada — validar que el receptor sea
    un usuario seguido. Un CreateView requeriría overrides de form_valid
    y get_form_kwargs que igualan o superan este código en complejidad.

    FIX DE SEGURIDAD: La vista original no validaba que el receiver fuera
    un usuario seguido → cualquiera podía enviar DMs a cualquiera.
    """
    following_users = (
        User.objects
        .filter(related_to__from_user=request.user)
        .select_related('profile')
        .order_by('username')
    )

    if request.method == 'POST':
        receiver_id = request.POST.get('receiver')
        content = request.POST.get('content', '').strip()

        if not receiver_id:
            messages.error(request, 'Selecciona un destinatario.')
            return redirect('send_message')

        receiver = get_object_or_404(User, id=receiver_id)

        # Validación de negocio: solo puedes escribir a usuarios que sigues
        if not following_users.filter(id=receiver.id).exists():
            messages.error(request, 'Solo puedes enviar mensajes a usuarios que sigues.')
            return redirect('send_message')

        if not content:
            messages.error(request, 'El mensaje no puede estar vacío.')
            return redirect('send_message')

        DirectMessage.objects.create(
            sender=request.user,
            receiver=receiver,
            content=content,
        )
        _send_email_async(
            subject=f'Nuevo mensaje de @{request.user.username} en UnetX',
            body=(
                f'Hola {receiver.first_name or receiver.username},\n\n'
                f'@{request.user.username} te envió: "{content[:150]}"'
            ),
            to=[receiver.email] if receiver.email else [],
        )
        messages.success(request, f'Mensaje enviado a @{receiver.username}.')
        return redirect('inbox')

    return render(request, 'twitter/send_message.html', {'following_users': following_users})


class InboxView(LoginRequiredMixin, ListView):
    """
    CBV: ListView con paginación automática para mensajes recibidos.

    Anti-N+1: select_related('sender__profile') resuelve sender + profile
    de cada mensaje en 1 JOIN — sin esto sería 1 query por mensaje.
    Los enviados se cargan en get_context_data con su propio select_related.
    """
    model = DirectMessage
    template_name = 'twitter/inbox.html'
    context_object_name = 'messages_received'
    paginate_by = 25

    def get_queryset(self):
        return (
            DirectMessage.objects
            .filter(receiver=self.request.user)
            .select_related('sender', 'sender__profile')
            .order_by('-timestamp')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['messages_sent'] = (
            DirectMessage.objects
            .filter(sender=self.request.user)
            .select_related('receiver', 'receiver__profile')
            .order_by('-timestamp')[:25]
        )
        return ctx


# ══════════════════════════════════════════════════════════════════════════════
# MENCIONES
# ══════════════════════════════════════════════════════════════════════════════

class MentionsView(LoginRequiredMixin, ListView):
    """
    CBV: ListView puro. El queryset optimizado resuelve la cadena
    Mention → Post → User → Profile en 1 JOIN gracias a select_related.
    Sin esto: 1 query por mención para obtener el post, y otra para el user.
    """
    model = Mention
    template_name = 'twitter/mentions.html'
    context_object_name = 'mentions'
    paginate_by = 20

    def get_queryset(self):
        return (
            Mention.objects
            .filter(mentioned_user=self.request.user)
            .select_related(
                'post',
                'post__user',
                'post__user__profile',
            )
            .order_by('-timestamp')
        )