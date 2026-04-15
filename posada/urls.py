from django.urls import path
from . import views

urlpatterns = [
    path('api/status/', views.guild_status, name='guild_status'),
    path('api/session/start/', views.start_session, name='start_session'),
    path('api/session/complete/', views.complete_session, name='complete_session'),
    path('api/adventurer/create/', views.create_adventurer,
         name='create_adventurer'),
    path('api/guild/consolidate/', views.consolidate_guild_wealth,
         name='consolidate_wealth'),
    path('api/adventurer/delete/<int:adv_id>/',
         views.delete_adventurer, name='delete_adventurer'),
    path('api/tavern/', views.tavern_recruits, name='tavern_recruits'),
]
