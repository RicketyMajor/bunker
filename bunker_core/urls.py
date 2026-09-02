import os

from django.contrib import admin
from django.urls import path, include
from bunker_core.views import (global_dashboard_view, backup_database,
                               restore_database, health_check, movil_estado, movil_assets,
                               movil_app, movil_sw, movil_manifest, movil_selftest,
                               briefing, briefing_seen, stats_timeline)

urlpatterns = [
    path('api/books/', include('books.urls')),
    path('api/movies/', include('movies.urls')),
    path('api/dashboard/', global_dashboard_view, name='dashboard'),
    path('api/health/', health_check, name='health_check'),
    path('api/briefing/', briefing, name='briefing'),
    path('api/briefing/seen/', briefing_seen, name='briefing_seen'),
    path('api/stats/timeline/', stats_timeline, name='stats_timeline'),
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
    #
    # Since the 2026-08-27 split it shows ONE block: the historical series over books, movies
    # and music. `/api/panel/` and its four Posada blocks left with La Posada.
    path('panel/', movil_app, name='panel'),
    path('api/music/', include('music.urls')),

    # --- RUTAS DEL PROTOCOLO DE EVACUACIÓN ---
    path('api/backup/', backup_database, name='backup'),
    path('api/restore/', restore_database, name='restore'),
]

# --- /admin/, WHICH IS NOT MOUNTED BY DEFAULT ---
#
# `/admin/` is not under `/api/`, so `bunker_core/auth.py` never sees it; and since the port
# became `0.0.0.0:8009` (2026-09-01) its 41 routes were reachable from the LAN. Measured
# 2026-09-02: `GET /admin/` answered 302 from `127.0.0.1` and from `192.168.0.8` alike.
#
# It is inert today and NOT by design: there are 0 users, 0 superusers and 0 staff. One single
# command arms it, and `README.md` documents that command as an optional step. A risk whose
# trigger is written into the project's own README is not hypothetical.
#
# IT IS CLOSED BY NOT MOUNTING IT, not with an IP guard. That was tried first and there is a
# measurement for why it does not work: with Docker publishing the port, the container sees
# `172.19.0.1` for anything arriving through the host's loopback and the REAL address for
# anything arriving from the LAN — so `REMOTE_ADDR` cannot tell "Alonso on his laptop" from
# "somebody on the Wi-Fi", and the one address that would work (the bridge gateway) changes when
# the network is recreated and would open by itself the day Docker enables the userland proxy for
# everything. A guard that fails OPEN on a configuration change I cannot see is not a guard.
#
# Nor is it deleted: `books/admin.py`, `movies/admin.py` and `music/admin.py` register their
# models, and `decisions/log.md:184` records that the three watcher models are edited FROM THE
# ADMIN. Deleting it would leave Alonso with no way in but a shell.
#
# The value is literally `1`. Anything else — `true`, `si`, empty — leaves the admin closed
# SILENTLY, which is the sharp edge here: `bunker doctor` covers it by reporting on every run
# whether it is mounted.
BUNKER_ADMIN = os.environ.get('BUNKER_ADMIN') == '1'

if BUNKER_ADMIN:
    urlpatterns.insert(0, path('admin/', admin.site.urls))
