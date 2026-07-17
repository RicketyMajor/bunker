from django.contrib import admin
from django.urls import path, include
from catalog.views import scanner_view
from bunker_core.views import global_dashboard_view, backup_database, restore_database, health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/books/', include('catalog.urls')),
    path('api/movies/', include('movies.urls')),
    path('scanner/', scanner_view, name='scanner'),
    path('api/dashboard/', global_dashboard_view, name='dashboard'),
    path('api/health/', health_check, name='health_check'),
    path('posada/', include('posada.urls')),
    path('api/music/', include('disquera.urls')),
    path('api/chess/', include('chess_study.urls')),

    # --- RUTAS DEL PROTOCOLO DE EVACUACIÓN ---
    path('api/backup/', backup_database, name='backup'),
    path('api/restore/', restore_database, name='restore'),
]
