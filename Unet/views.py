from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .models import Profile, Post, Relationship, DirectMessage,  Mention
from .forms import UserRegisterForm, PostForm, ProfileUpdateForm, UserUpdateForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth.views import LogoutView
from django.db.models import Count
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib import messages


def buscar_usuarios(request):
    query = request.GET.get('q', '')
    usuarios = []
    if query:
        usuarios = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query)
        )
    context = {
        'usuarios': usuarios,
        'query': query,
    }
    return render(request, 'twitter/buscar.html', context)


class CustomLogoutView(LogoutView):
    http_method_names = ['get', 'post']

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count
from .models import Post, Mention, Relationship
from .forms import PostForm
from django.contrib.auth.models import User

from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import render, redirect
from .models import Post, Relationship, Mention
from .forms import PostForm
from .forms import UserRegisterForm
from django.http import HttpResponse


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        print("🟢 POST recibido")
        if form.is_valid():
            user = form.save()
            print("✅ Usuario creado:", user.username)
            messages.success(request, f'Cuenta creada para {user.username}')
            return redirect('login')
        else:
            print("❌ Errores del formulario:", form.errors)
    else:
        form = UserRegisterForm()
        print("🟡 Carga inicial de la página de registro")

    return render(request, 'twitter/register.html', {'form': form})

@login_required
def home(request):
       # Obtener los usuarios a los que sigue el usuario autenticado
    following_users = User.objects.filter(related_to__from_user=request.user)

    print("🟢 Entró a register view")

    # Obtener los posts de los usuarios seguidos + los del usuario autenticado
    posts = Post.objects.filter(Q(user__in=following_users) | Q(user=request.user)).order_by('-timestamp')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            return redirect('home')
    else:
        form = PostForm()
        

    # Obtener los 4 usuarios con más seguidores
    suggested_users = User.objects.annotate(
        num_followers=Count('related_to')
    ).order_by('-num_followers')[:4]

    # Obtener los 4 usuarios con más posts
    most_active_users = User.objects.annotate(
        num_posts=Count('posts')
    ).order_by('-num_posts')[:4]

    context = {
        'posts': posts,
        'form': form,
        'suggested_users': suggested_users,
        'most_active_users': most_active_users,
    }

    return render(request, 'twitter/newsfeed.html', context)



def delete(request,post_id):
    post = Post.objects.get(id=post_id)
    post.delete()
    return redirect('home')

def profile(request, username):
    # Obtiene el usuario cuyo perfil se quiere ver
    user_profile = get_object_or_404(User, username=username)
    # Obtiene los posts de ese usuario, ordenados por fecha descendente
    posts = user_profile.posts.all().order_by('-timestamp')
    
    # Consulta para obtener los 4 usuarios con más seguidores
    # Se asume que en el modelo Relationship el campo to_user tiene related_name='related_to'
    suggested_users = User.objects.annotate(
        num_followers=Count('related_to')
    ).order_by('-num_followers')[:4]
    
    context = {
        'user': user_profile,
        'posts': posts,
        'suggested_users': suggested_users,
    }
    return render(request, 'twitter/profile.html', context)

@login_required
def editar(request):
    # Asegurarse de que el usuario tenga un perfil (si no, se crea)
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
            return redirect('profile', username=request.user.username)
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'twitter/editar.html', context)

@login_required
def follow(request, username):
    current_user = request.user
    to_user = get_object_or_404(User, username=username)
    rel = Relationship(from_user=current_user, to_user=to_user)
    rel.save()

    # Configurar el contenido del correo electrónico
    subject = 'Nuevo seguidor en nuestra plataforma'
    message = f'Hola {to_user.first_name},\n\n{current_user.first_name} ha comenzado a seguirte.'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [to_user.email]

    # Crear y enviar el correo electrónico
    email = EmailMessage(subject, message, from_email, recipient_list)
    try:
        email.send(fail_silently=False)
        messages.success(request, 'Has comenzado a seguir a este usuario y se le ha notificado por correo electrónico.')
    except Exception as e:
        messages.error(request, f'Se ha producido un error al enviar el correo electrónico: {e}')

    return redirect('home')

@login_required
def unfollow(request, username):
    current_user = request.user
    to_user = User.objects.get(username=username)
    to_user_id = to_user.id 
    rel = Relationship.objects.get(from_user=current_user.id, to_user=to_user_id)
    rel.delete()
    return redirect('home')

@login_required
def send_message(request):
    following_users = User.objects.filter(  # Lista de usuarios seguidos
        id__in=Relationship.objects.filter(from_user=request.user).values_list('to_user', flat=True)
    )

    if request.method == 'POST':
        receiver_id = request.POST.get('receiver')
        content = request.POST.get('content', '').strip()

        if not receiver_id:
            messages.error(request, "Debes seleccionar un destinatario.")
            return redirect('send_message')

        receiver = get_object_or_404(User, id=receiver_id)

        if len(content) > 200:
            messages.error(request, "El mensaje no puede tener más de 200 caracteres.")
        elif content:
            DirectMessage.objects.create(sender=request.user, receiver=receiver, content=content)

            # Enviar notificación por correo
            subject = 'Nuevo mensaje en tu bandeja de entrada'
            message = f'Hola {receiver.first_name},\n\nHas recibido un nuevo mensaje de {request.user.first_name}: "{content}".'
            email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [receiver.email])
            email.send(fail_silently=False)

            messages.success(request, "Mensaje enviado con éxito.")
            return redirect('inbox')

    return render(request, 'twitter/send_message.html', {'following_users': following_users})

@login_required
def inbox(request):
    messages_received = DirectMessage.objects.filter(receiver=request.user).order_by('-timestamp')
    messages_sent = DirectMessage.objects.filter(sender=request.user).order_by('-timestamp')
    return render(request, 'twitter/inbox.html', {'messages_received': messages_received, 'messages_sent': messages_sent})

@login_required
def mentions(request):
    # Filtra las menciones donde el usuario mencionado es el usuario actual
    mention_list = Mention.objects.filter(mentioned_user=request.user).order_by('-timestamp')
    return render(request, 'twitter/mentions.html', {'mentions': mention_list})

@login_required
def retweet(request, post_id):
    original_post = get_object_or_404(Post, id=post_id)
    # Crea un nuevo post que reenvía el post original. 
    # Puedes copiar el contenido o dejarlo en blanco para solo referenciar el post original.
    new_post = Post.objects.create(
        user=request.user,
        retweet=original_post,
        content=original_post.content  # O podrías permitir agregar contenido adicional
    )
    return redirect('home')