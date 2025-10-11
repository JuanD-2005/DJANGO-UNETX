from django.contrib import admin
from .models import Profiles, Post, Relationship 
# Register your models here.

admin.site.register(Profiles)
admin.site.register(Post)
admin.site.register(Relationship)
