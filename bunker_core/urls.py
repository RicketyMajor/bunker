from django.contrib import admin
from django.urls import path, include
from catalog.views import scanner_view
from bunker_core.views import (global_dashboard_view, backup_database, list_backups,
                               restore_database, health_check, movil_estado,
                               movil_app, movil_sw, movil_manifest, movil_selftest)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/books/', include('catalog.urls')),
    path('api/movies/', include('movies.urls')),
    path('scanner/', scanner_view, name='scanner'),
    path('api/dashboard/', global_dashboard_view, name='dashboard'),
    path('api/health/', health_check, name='health_check'),
    path('api/movil/estado/', movil_estado, name='movil_estado'),

    # --- TRANSMISOR DE CAMPO ---
    # sw.js is served from /movil/ and not /static/ because that is what scopes it.
    path('movil/', movil_app, name='movil_app'),
    path('movil/sw.js', movil_sw, name='movil_sw'),
    path('movil/manifest.json', movil_manifest, name='movil_manifest'),
    path('movil/selftest/', movil_selftest, name='movil_selftest'),
    path('posada/', include('posada.urls')),
    path('api/music/', include('disquera.urls')),
    path('api/chess/', include('chess_study.urls')),

    # --- RUTAS DEL PROTOCOLO DE EVACUACIÓN ---
    path('api/backup/', backup_database, name='backup'),
    path('api/backups/', list_backups, name='list_backups'),
    path('api/restore/', restore_database, name='restore'),
]
