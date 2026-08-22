from django.contrib import admin
from django.urls import path, include
from bunker_core.views import (global_dashboard_view, backup_database, list_backups,
                               restore_database, health_check, movil_estado, movil_assets,
                               movil_app, movil_sw, movil_manifest, movil_selftest, panel_datos,
                               briefing, briefing_seen, stats_timeline)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/books/', include('catalog.urls')),
    path('api/movies/', include('movies.urls')),
    path('api/dashboard/', global_dashboard_view, name='dashboard'),
    path('api/health/', health_check, name='health_check'),
    path('api/briefing/', briefing, name='briefing'),
    path('api/briefing/seen/', briefing_seen, name='briefing_seen'),
    path('api/stats/timeline/', stats_timeline, name='stats_timeline'),
    # Todo lo que muestra el panel, en un GET que no escribe. Ver `panel_datos`.
    path('api/panel/', panel_datos, name='panel_datos'),
    path('api/movil/estado/', movil_estado, name='movil_estado'),
    path('api/movil/assets/', movil_assets, name='movil_assets'),

    # --- TRANSMISOR DE CAMPO ---
    # sw.js is served from /movil/ and not /static/ because that is what scopes it.
    path('movil/', movil_app, name='movil_app'),
    # Literal, NOT `<str:nombre>`: the natural parametrised reading of "asset/<name>" reads a
    # client-supplied path under BASE_DIR, and `..%2f..%2fsettings.py` walks straight to a
    # hardcoded SECRET_KEY. Three files, named in MOVIL_ASSETS; a parameter buys nothing.
    # `movil_app` renders the same template — the APK cannot render the raw `{{ }}`.
    path('movil/asset/app.html', movil_app, name='movil_asset_app'),
    path('movil/sw.js', movil_sw, name='movil_sw'),
    path('movil/manifest.json', movil_manifest, name='movil_manifest'),
    path('movil/selftest/', movil_selftest, name='movil_selftest'),

    # The consultation surface. Same view and same template as `/movil/` — see its docstring.
    # A real Django route, which is what `bunker-responde.md`'s criterion asks for by its own
    # wording, and it works in a plain browser with no APK involved.
    path('panel/', movil_app, name='panel'),
    path('posada/', include('posada.urls')),
    path('api/music/', include('disquera.urls')),
    path('api/chess/', include('chess_study.urls')),

    # --- RUTAS DEL PROTOCOLO DE EVACUACIÓN ---
    path('api/backup/', backup_database, name='backup'),
    path('api/backups/', list_backups, name='list_backups'),
    path('api/restore/', restore_database, name='restore'),
]
