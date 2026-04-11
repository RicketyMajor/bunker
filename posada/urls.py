from django.urls import path
from . import views

urlpatterns = [
    path('api/status/', views.guild_status, name='guild_status'),
    path('api/session/complete/', views.complete_session, name='complete_session'),
]
