from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static
from .views import send_message, inbox
from django.contrib import messages
from django.shortcuts import redirect

class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, 'Has cerrado sesión correctamente.')
        return response

    def get_next_page(self):
      return 'home'

urlpatterns = [
    path('',views.home,name='home'),
    path('register/',views.register,name='register'),   
    path('login/',LoginView.as_view(template_name='twitter/login.html'),name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('delete/<int:post_id>/', views.delete, name = 'delete'),
    path('profile/<str:username>/', views.profile, name = 'profile'),
    path('editar/', views.editar, name = 'editar'),
    path('follow/<str:username>/', views.follow, name = 'follow'),
    path('unfollow/<str:username>/', views.unfollow, name = 'unfollow'),
    path('buscar/', views.buscar_usuarios, name='buscar_usuarios'), 
    path('mensajes/enviar/', views.send_message, name='send_message'),
    path('inbox/', inbox, name='inbox'),
    path('mentions/', views.mentions, name='mentions'),
    path('retweet/<int:post_id>/', views.retweet, name='retweet'),
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)   
