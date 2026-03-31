from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import messages

from . import views

class CustomLogoutView(LogoutView):
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, f'¡Hasta pronto, @{request.user.username}!')
        return super().dispatch(request, *args, **kwargs)

    def get_next_page(self):
        return 'login'

# SIN app_name = 'unet' para mantener compatibilidad con los templates existentes.

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='twitter/login.html'), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    path('', views.home, name='home'),

    path('post/<int:post_id>/delete/', views.PostDeleteView.as_view(), name='delete'),
    path('post/<int:post_id>/like/', views.like_post, name='like'),
    path('post/<int:post_id>/retweet/', views.retweet, name='retweet'),

    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('editar/', views.editar, name='editar'),

    path('follow/<str:username>/', views.follow, name='follow'),
    path('unfollow/<str:username>/', views.unfollow, name='unfollow'),

    path('buscar/', views.BuscarUsuariosView.as_view(), name='buscar_usuarios'),

    path('mensajes/enviar/', views.send_message, name='send_message'),
    path('inbox/', views.InboxView.as_view(), name='inbox'),

    path('mentions/', views.MentionsView.as_view(), name='mentions'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)