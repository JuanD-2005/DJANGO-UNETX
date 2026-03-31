# Unet/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import re


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════════

class Profile(models.Model):
    """
    Extensión 1-a-1 del User de Django.
    Nota: renombrado de 'Profiles' a 'Profile' (convención singular en Django).
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    bio = models.CharField(max_length=200, default='¡Hola, soy nuevo en UnetX!')
    image = models.ImageField(
        upload_to='profiles/',
        default='profiles/default.png',
    )

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self) -> str:
        return f'@{self.user.username}'

    def following(self) -> models.QuerySet:
        """Usuarios a quienes este perfil sigue."""
        return User.objects.filter(
            related_to__from_user=self.user
        ).select_related('profile')

    def followers(self) -> models.QuerySet:
        """Usuarios que siguen a este perfil."""
        return User.objects.filter(
            relationships__to_user=self.user
        ).select_related('profile')

    @property
    def following_count(self) -> int:
        return Relationship.objects.filter(from_user=self.user).count()

    @property
    def followers_count(self) -> int:
        return Relationship.objects.filter(to_user=self.user).count()


# Signals fuera de la clase — esto es lo correcto
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Usamos get_or_create para robustez (ej: usuarios creados vía shell)
    profile, _ = Profile.objects.get_or_create(user=instance)
    profile.save()


# ══════════════════════════════════════════════════════════════════════════════
# POST (Tweet)
# ══════════════════════════════════════════════════════════════════════════════

class Post(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        db_index=True,
    )
    content = models.TextField(max_length=280)  # TextField > CharField para Postgres
    image = models.ImageField(upload_to='posts/', null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    # Self-referential FK para retweets
    retweet_of = models.ForeignKey(  # renombrado de 'retweet' → más explícito
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='retweets',
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        indexes = [
            models.Index(fields=['-timestamp']),          # feed principal
            models.Index(fields=['user', '-timestamp']),   # perfil de usuario
        ]

    def __str__(self) -> str:
        return f'@{self.user.username}: {self.content[:50]}'

    @property
    def is_retweet(self) -> bool:
        return self.retweet_of is not None

    @property
    def like_count(self) -> int:
        return self.likes.count()

    @property
    def retweet_count(self) -> int:
        return self.retweets.count()

    def get_mentions(self) -> list[str]:
        """Retorna lista de usernames mencionados (sin el @)."""
        return re.findall(r'@(\w+)', self.content)


# ══════════════════════════════════════════════════════════════════════════════
# LIKE
# ══════════════════════════════════════════════════════════════════════════════

class Like(models.Model):
    """
    Modelo explícito para likes (mejor que ManyToMany implícito
    porque permite agregar campos como timestamp fácilmente).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        # Un usuario solo puede dar like una vez a cada post
        unique_together = ('user', 'post')
        indexes = [
            models.Index(fields=['post']),  # para contar likes por post
        ]

    def __str__(self) -> str:
        return f'@{self.user.username} ♥ Post#{self.post_id}'


# ══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP (Follow)
# ══════════════════════════════════════════════════════════════════════════════

class Relationship(models.Model):
    """
    Representa que `from_user` sigue a `to_user`.
    """
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='relationships',  # user.relationships.all() → a quién sigo
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='related_to',     # user.related_to.all() → quién me sigue
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Relación'
        verbose_name_plural = 'Relaciones'
        # Evita follows duplicados a nivel de base de datos
        unique_together = ('from_user', 'to_user')
        indexes = [
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
        ]

    def __str__(self) -> str:
        return f'@{self.from_user.username} → @{self.to_user.username}'


# ══════════════════════════════════════════════════════════════════════════════
# DIRECT MESSAGE
# ══════════════════════════════════════════════════════════════════════════════

class DirectMessage(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages',
    )
    content = models.TextField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False)  # útil para notificaciones

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Mensaje Directo'
        verbose_name_plural = 'Mensajes Directos'
        indexes = [
            # Para cargar la conversación entre dos usuarios eficientemente
            models.Index(fields=['sender', 'receiver', 'timestamp']),
        ]

    def __str__(self) -> str:
        return f'@{self.sender.username} → @{self.receiver.username} ({self.timestamp:%Y-%m-%d %H:%M})'


# ══════════════════════════════════════════════════════════════════════════════
# MENTION
# ══════════════════════════════════════════════════════════════════════════════

class Mention(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='mentions',
    )
    mentioned_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mentions',
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mención'
        verbose_name_plural = 'Menciones'
        unique_together = ('post', 'mentioned_user')
        indexes = [
            models.Index(fields=['mentioned_user', '-timestamp']),
        ]

    def __str__(self) -> str:
        return f'@{self.mentioned_user.username} en Post#{self.post_id}'