from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import re

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
# Create your models here.

class Profiles(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.CharField(default = "Hola, Unet",max_length=200)
    image = models.ImageField(default='Default.png')
    
    def __str__(self):
        return f'Perfil de {self.user.username}'
    
    def following(self):
        user_ids = Relationship.objects.filter(from_user=self.user)\
                                    .values_list('to_user_id', flat=True)
        return User.objects.filter(id__in=user_ids)
    
    def followers(self):
        user_ids = Relationship.objects.filter(to_user=self.user)\
                                    .values_list('from_user_id', flat=True)
        return User.objects.filter(id__in=user_ids)
  

    @receiver(post_save, sender=User)
    def create_profile(sender, instance, created, **kwargs):
        if created:
            Profiles.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_profile(sender, instance, **kwargs):
        instance.profiles.save()

    
    

class Post(models.Model):
    timestamp = models.DateTimeField(default = timezone.now)
    content = models.CharField(max_length=200)  # Cambiado a CharField
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'posts')
    image = models.ImageField(upload_to='posts/', null=True, blank=True)  # Nuevo campo de imagen
     # Campo para identificar el post original en caso de ser un retweet (reenviado)
    retweet = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='retweets')

    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return self.content
    
    def get_mentions(self):
        return [match[1:] for match in re.findall(r'@\w+', self.content)]
    
class Relationship(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'relationships')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'related_to')
    
    def __str__(self):
        return f'{self.from_user} to {self.to_user}'   


class DirectMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"De {self.sender} a {self.receiver} - {self.timestamp}"
    
    
    
class Mention(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='mentions')
    mentioned_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentions')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mentioned_user.username} mencionada en el post {self.post.id}"    