import hashlib
import io
import json
import logging
import os
import secrets
from django.conf import settings
from django.core.management import call_command
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.utils.timezone import localdate
from datetime import timedelta
from books.models import Book, ReadingSession, AnnualRecord as BookAnnualRecord
from movies.models import Movie, MovieAnnualRecord
from music.models import Album, MusicAnnualRecord

logger = logging.getLogger(__name__)

# Las apps que entran en la capsula del tiempo. `bunker_core` entro el 2026-08-19, cuando
# BunkerState le dio su primer modelo: sin el, un restore devuelve la fecha de ultima entrada
# vacia y el briefing vuelve a anunciar todos los logros como nuevos.
BACKUP_APPS = ('catalog', 'movies', 'disquera', 'bunker_core')
# DELETED 2026-09-02: `BACKUP_DIR = '/app/backups'` and the `bunker_backups_data` volume.
#
# Nothing had written there since 2026-08-29 (the in-image cron was removed because it never fired
# on nights the laptop was off) and — counted 2026-09-02 across the whole tree — nothing READ it
# either: `list_backups` had not ONE consumer (there is no `API_BACKUPS` constant, in the TUI, the
# PWA, the APK or the scripts), and the only live call to `/api/restore/` is
# `cli/tui/screens.py:686`, which does NOT send `filename` and therefore always restored
# `ROOT_BACKUP`. The branch that read the volume was unreachable from day one.
#
# The 8 historical capsules (2026-07-17 to 2026-08-29) were copied first to
# `~/dev/respaldos/bunker-historico/`, md5-verified one by one. The volume still exists in Docker:
# `docker volume rm bunker_backups_data` whenever Alonso wants, nothing mounts it any more.
#
# THE 8th ONE WAS ONLY VISIBLE ONCE THE MOUNT WENT: `./backups/` exists on the host, is gitignored
# and root-owned, and the volume was mounted ON TOP of it. Unmounting revealed a capsule from
# 2026-07-17 that no listing of the volume could ever have shown.
#
# The live backup is `scripts/respaldo_pilas.sh` under its user timer, writing to
# `~/dev/respaldos/bunker/` — outside the container on purpose, so it survives a `down -v`.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Lo que escribe el backup manual de la TUI, y el destino por defecto de restore.
ROOT_BACKUP = os.path.join(PROJECT_ROOT, 'bunker_backup.json')


def _reject_if_bad_token(request):
    """Devuelve un JsonResponse de error si el token no es valido, o None si lo es.

    Falla cerrado: sin BUNKER_BACKUP_TOKEN configurado no se atiende la peticion. Antes caia a
    un valor por defecto escrito en el codigo, que es publico y por tanto no protege nada.
    """
    expected = os.environ.get("BUNKER_BACKUP_TOKEN")
    if not expected:
        return JsonResponse(
            {"error": "BUNKER_BACKUP_TOKEN no esta configurado en el servidor."}, status=503)

    received = request.headers.get("X-Bunker-Token") or ""
    if not secrets.compare_digest(received, expected):
        return JsonResponse(
            {"error": "Acceso denegado: Token de seguridad inválido o ausente."}, status=403)
    return None


def global_dashboard_view(request):
    """BFF: Agrega los datos de los tres módulos de inventario, bloque a bloque.

    Cada bloque va en su propio `try`: un módulo que falle deja su hueco vacío en vez de
    tumbar el panel entero. Hasta el 2026-08-27 agregaba cinco módulos; posada y ajedrez se
    fueron a sus propios repositorios y con ellos los logros, que los evaluaba `posada`.
    """
    today = localdate()

    data = {
        "books": {}, "movies": {}, "music": {}, "feed": []
    }
    feed = []

    # 1. SECTOR LITERARIO
    try:
        books = Book.objects.all()
        data["books"]["total"] = books.count()
        data["books"]["read"] = books.filter(is_read=True).count()
        # No `hours` here. The Disquera below carries the reason in its own comment: the
        # minute ledgers were deleted on 2026-08-14 for being "a number nobody types
        # honestly". All three sectors then went on inventing one by exactly that standard —
        # `pages * 1.5 / 60`, `watched * 2`, `listened * 0.75` — and the books figure summed
        # EVERY book in the vault, read or not, under the label "Horas de Lectura Est.".
        # Removed 2026-08-29, along with the `Sum` aggregate that fed only this line.
        
        # Calculate reading streak
        from books.models import ReadingSession
        sessions = ReadingSession.objects.filter(pages_read__gt=0).values_list('date', flat=True).distinct()
        session_dates = set(sessions)
        
        streak = 0
        if today in session_dates:
            check_date = today
        elif (today - timedelta(days=1)) in session_dates:
            check_date = today - timedelta(days=1)
        else:
            check_date = None
            
        if check_date:
            while check_date in session_dates:
                streak += 1
                check_date -= timedelta(days=1)
        
        data["books"]["streak"] = streak
        
        top_book = books.filter(personal_rating__isnull=False).order_by('-personal_rating').first()
        if top_book:
            data["books"]["top_rated"] = {"title": top_book.title, "rating": float(top_book.personal_rating)}

    except Exception as e:
        feed.append(f"[red]Error Libros:[/] {str(e)[:40]}")

    # 2. VIDEOCLUB
    try:
        movies = Movie.objects.all()
        data["movies"]["total"] = movies.count()
        data["movies"]["watched"] = movies.filter(is_watched=True).count()
        
        top_movie = movies.filter(personal_rating__isnull=False).order_by('-personal_rating').first()
        if top_movie:
            data["movies"]["top_rated"] = {"title": top_movie.title, "rating": float(top_movie.personal_rating)}
            
    except Exception as e:
        feed.append(f"[red]Error Videoclub:[/] {str(e)[:40]}")

    # 3. DISQUERA
    try:
        albums = Album.objects.all()
        data["music"]["total"] = albums.count()
        data["music"]["listened"] = albums.filter(is_listened=True).count()

        # Albums listened this week. This used to sum ListeningEntry.minutes_listened; the
        # minute ledger was removed because an album is the unit that gets logged, and a
        # count of records is the same fact without a number nobody types honestly.
        start_of_week = today - timedelta(days=today.weekday())
        data["music"]["albums_week"] = MusicAnnualRecord.objects.filter(
            date_listened__gte=start_of_week).count()


        top_album = albums.filter(personal_rating__isnull=False).order_by('-personal_rating').first()
        if top_album:
            data["music"]["top_rated"] = {"title": top_album.title, "rating": float(top_album.personal_rating)}
            
    except Exception as e:
        feed.append(f"[red]Error Disquera:[/] {str(e)[:40]}")

    # Los bloques 4 (Ajedrez), 5 (Posada) y 6 (Logros) estaban aquí hasta la separación del
    # 2026-08-27. Los logros se fueron con ellos: `evaluate_achievements` es de posada y sus
    # contadores contaban sesiones de Deep Work, puzzles y rachas de hábitos.

    # 7. TRÁFICO DE RED (FEED GLOBAL SEGURO)
    # Ambos registros guardan su propio title (son historicos inmutables y su FK es SET_NULL),
    # asi que no hace falta ir al libro/pelicula para mostrarlo.
    try:
        for rb in BookAnnualRecord.objects.order_by('-date_finished')[:3]:
            feed.append(f"[green]📚 Leído:[/] {rb.title[:25]}")
    except Exception:
        logger.warning("Fallo el feed de Biblioteca", exc_info=True)

    try:
        # date_watched, no date_finished: ese era el nombre equivocado que hacia fallar el
        # bloque entero en silencio, por lo que "Visto" nunca aparecio en el dashboard.
        for rm in MovieAnnualRecord.objects.order_by('-date_watched')[:2]:
            feed.append(f"[yellow]🎬 Visto:[/] {rm.title[:25]}")
    except Exception:
        logger.warning("Fallo el feed de Videoclub", exc_info=True)

    data["feed"] = feed
    return JsonResponse(data, status=200)


@csrf_exempt
def backup_database(request):
    """Genera una cápsula de tiempo (JSON) de la base de datos de los módulos de inventario."""
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido."}, status=405)

    rejected = _reject_if_bad_token(request)
    if rejected:
        return rejected

    try:
        with open(ROOT_BACKUP, 'w', encoding='utf-8') as f:
            call_command('dumpdata', *BACKUP_APPS, format='json', indent=4, stdout=f)

        return JsonResponse({"message": "Cápsula de seguridad generada con éxito.", "path": ROOT_BACKUP}, status=200)
    except Exception as e:
        logger.exception("Fallo generando el backup")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def restore_database(request):
    """Restores the Bunker from `bunker_backup.json`, in the repository root.

    It no longer accepts `filename`: the branch that read the `bunker_backups_data` volume had not
    a single caller, and nothing fed that volume. To restore ANOTHER capsule, the live path — and
    the one `install.sh` uses — is to copy it into the container and load it:

        docker compose cp <capsula>.json web:/tmp/c.json
        docker compose exec -T web python manage.py loaddata --ignorenonexistent /tmp/c.json
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido."}, status=405)

    rejected = _reject_if_bad_token(request)
    if rejected:
        return rejected

    # REFUSE `filename` LOUDLY instead of ignoring it. Nothing sends it today, but a caller that
    # did would be asking for capsule X and would silently get the WHOLE DATABASE REPLACED from
    # `bunker_backup.json` instead. That is the one failure mode this endpoint must not have:
    # `loaddata` over live rows is not undoable from here.
    pedido = (request.POST.get('filename') or '').strip()
    if not pedido and request.body:
        try:
            pedido = (json.loads(request.body).get('filename') or '').strip()
        except (ValueError, AttributeError):
            pedido = ''
    if pedido:
        return JsonResponse(
            {"error": "Esta ruta ya no acepta `filename`: restaura siempre desde "
                      f"{os.path.basename(ROOT_BACKUP)}. Para otra cápsula, cárgala con "
                      "`docker compose cp` + `manage.py loaddata --ignorenonexistent`."},
            status=400)

    backup_path = ROOT_BACKUP

    if not os.path.exists(backup_path):
        return JsonResponse({"error": f"No se encontró la cápsula '{os.path.basename(backup_path)}'."}, status=404)

    try:
        # ignorenonexistent: TODA capsula automatica anterior al 2026-08-27 nombra modelos de
        # `posada` y `chess_study`, cuyas apps ya no estan instaladas. Sin la bandera loaddata
        # lanza DeserializationError y este endpoint devuelve 500 — medido conduciendo la vista
        # sobre una base desechable: 6 capsulas de 6, ninguna restaurable. Con ella entran las
        # filas del Bunker y las ajenas se descartan.
        #
        # Descartar en silencio es exactamente el fallo que este endpoint existe para evitar, asi
        # que el conteo de loaddata viaja en la respuesta: "Installed N object(s)" es la unica
        # forma de que el usuario vea que una capsula de 955 objetos aporto 409.
        salida = io.StringIO()
        call_command('loaddata', backup_path, ignorenonexistent=True, verbosity=2, stdout=salida)
        instalados = next((l for l in salida.getvalue().splitlines() if 'Installed' in l), '')
        return JsonResponse(
            {"message": f"Búnker restaurado a su estado original. {instalados}".strip(),
             "restored_from": backup_path}, status=200)
    except Exception as e:
        logger.exception("Fallo restaurando desde %s", backup_path)
        return JsonResponse({"error": str(e)}, status=500)


def health_check(request):
    """Endpoint ultra-ligero para verificar la infraestructura."""
    from django.db import connection
    import time
    
    start_time = time.time()
    db_ok = True
    try:
        # Check simple de DB
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False
        
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return JsonResponse({
        "status": "ok",
        "db": db_ok,
        "latency_ms": elapsed_ms
    }, status=200 if db_ok else 503)


def movil_app(request):
    """The PWA. One template, one bundled script, no CDN.

    Serves THREE routes: `/movil/` (capture), `/movil/asset/app.html` (what the APK caches) and
    `/panel/` (consultation). One template because the APK loads exactly one hardcoded URL
    (`MainActivity.kt`) and a second template is the second page to keep in sync that killed the
    original panel. The client reads `location.pathname` and shows the right surface.
    """
    return render(request, 'movil/app.html')


# The three files the APK installs and runs in its WebView. Declared once, at module level,
# because the manifest hashes them and the asset route serves them: two readers of one fact.
MOVIL_ASSETS = {
    "app.html": "bunker_core/templates/movil/app.html",
    # The BUILT bundles, not the sources, since 2026-08-21. The APK must install what the page
    # actually loads, and `app.html` now loads one script instead of two.
    #
    # The KEYS stay plain filenames with no directory. `AssetStore.prepararGeneracion` refuses a
    # key containing '/' — it is the trust boundary, a `..` there writes outside filesDir — and
    # `AssetStore.handler` resolves a request by `substringAfterLast('/')` anyway, so a nested
    # key would buy nothing and break the download.
    "main.js": "bunker_core/static/movil/dist/main.js",
    "selftest.js": "bunker_core/static/movil/dist/selftest.js",
}


def movil_assets(request):
    """The manifest the APK compares against what it has installed.

    A hash of the contents rather than a version number nobody would remember to bump: the
    files are three, they are small, and a number maintained by hand is a number that drifts —
    this project has shipped that mistake five times in prose already.

    The paths are RELATIVE, not absolute. `request.build_absolute_uri()` reflects the `Host`
    header, and `ALLOWED_HOSTS` is `['*']`, so an absolute URL here is a URL the server does
    not actually control — and the APK downloads its UI from it and runs it in a WebView.
    Letting the APK join these against `BuildConfig.BUNKER_URL` is less code and the whole
    class disappears.
    """
    h = hashlib.sha256()
    urls = {}
    for nombre in sorted(MOVIL_ASSETS):
        ruta = settings.BASE_DIR / MOVIL_ASSETS[nombre]
        if not ruta.exists():
            return JsonResponse({"error": f"falta {nombre} en el servidor"}, status=500)
        h.update(ruta.read_bytes())
        # DERIVED from the same path that was just hashed, never rebuilt from the key.
        # Rebuilding it as f"/static/movil/{nombre}" was correct only while every asset sat
        # flat in that directory. The day `main.js` moved to `dist/`, that expression pointed
        # at `bunker_core/static/movil/main.js` — the UNBUNDLED entry point, which is also
        # served as a static file and answers **200**. The APK would have downloaded an ES
        # module with `import` statements, run it as a classic script, and shown a page that
        # renders and executes nothing. Measured 2026-08-21: both URLs answered 200 and only
        # the BODIES told them apart.
        urls[nombre] = ("/movil/asset/app.html" if nombre == "app.html"
                        else "/" + MOVIL_ASSETS[nombre].removeprefix("bunker_core/"))
    return JsonResponse({"version": h.hexdigest(), "files": urls})


def movil_sw(request):
    """The service worker.

    Served from /movil/ and not from /static/ on purpose: a service worker's scope is the
    directory it is delivered from, so one served under /static/ would never control
    /movil/ — and would fail silently, which is the worst thing it could do.
    """
    return render(request, 'movil/sw.js', content_type='application/javascript')


def movil_selftest(request):
    """The browser-run check for queue.js. Not linked from the app; open it by hand."""
    return render(request, 'movil/selftest.html')


def movil_manifest(request):
    return render(request, 'movil/manifest.json', content_type='application/manifest+json')


def movil_estado(request):
    """The minimum the Transmisor needs in order to capture correctly.

    This is NOT the dashboard. The dashboard costs 29 queries and aggregates five modules;
    the phone needs none of them. If this endpoint grows past a handful of queries it has
    become a second dashboard and the design has drifted.

    Spec: context/specs/transmisor-de-campo.md
    """
    # The book to offer first: the one most recently logged, not the one closest to being
    # finished. Those are different criteria — the briefing wants the latter, the capture
    # sheet wants whatever is physically on the table right now.
    # `book__is_read=False` because the session outlives the book's state: finishing a book
    # takes it out of `libros` but leaves the row that carries its last position, so without
    # this the phone keeps offering + PÁGINAS on a book you already closed.
    leyendo = None
    ultima = (ReadingSession.objects
              .filter(book__isnull=False, current_page__isnull=False, book__is_read=False)
              .select_related('book', 'book__author')
              .order_by('-date', '-id')
              .first())
    if ultima is not None:
        leyendo = {
            "book_id": ultima.book_id,
            "title": ultima.book.title,
            "author": ultima.book.author.name if ultima.book.author else "",
            "current_page": ultima.current_page,
            "page_count": ultima.book.page_count,
        }

    # `habitos_pendientes` and `aventureros` were here until the 2026-08-27 split. They fed the
    # phone's habit and session sheets, and both sheets left with them: La Posada is its own
    # repository and the Transmisor keeps only the nine inventory verbs.
    return JsonResponse({
        "leyendo": leyendo,
        "libros": list(Book.objects.filter(is_read=False).values("id", "title")[:500]),
        "peliculas": list(Movie.objects.filter(is_watched=False).values("id", "title")[:500]),
        "albums": list(Album.objects.filter(is_listened=False).values("id", "title")[:500]),
    })


@api_view(['GET'])
def briefing(_request):
    """Lo que el Búnker tiene que decirte al entrar. Solo lee.

    Que sea un GET sin efectos no es un detalle de estilo: `/posada/api/habits/` y
    `/api/dashboard/` liquidan eventos de calendario pasados en cada GET, y por eso
    el prestigio del gremio se movió 75 → 102 en una sesión que no pagó nada a mano.
    Este endpoint no llama a ninguno de los dos.
    """
    from bunker_core.briefing import construir_briefing
    return Response(construir_briefing())


@api_view(['GET'])
def stats_timeline(request):
    """Serie histórica por módulo. Solo lee.

    The response echoes the resolved query back because `serie()` clamps `window` to
    [1, 60] instead of rejecting it: without the echo, a client that sent 99999 has no
    way to tell it got 60, and a clamp nobody can see is a clamp nobody debugs.
    """
    from bunker_core.timeline import serie, WINDOW_DEFECTO
    modulo = request.GET.get('module', 'books')
    periodo = request.GET.get('period', 'monthly')
    ventana = request.GET.get('window', WINDOW_DEFECTO)
    try:
        datos = serie(modulo, periodo, ventana)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    return Response({"module": modulo, "period": periodo,
                     "window": len(datos), "series": datos})


# `panel_datos` and `/api/panel/` stood here until the 2026-08-27 split. All four of its blocks
# — prestige, habits, achievements and the session log — read only Posada's models, so nothing
# of it survived the amputation. `/panel/` itself stays: its second block reads
# `/api/stats/timeline/`, which is books, movies and music.


@api_view(['POST'])
def briefing_seen(request):
    """Marca la entrada como vista. Es POST porque escribe."""
    from bunker_core.briefing import marcar_visto
    marcar_visto(bool(request.data.get('con_revision', False)))
    return Response({"message": "Entrada registrada."})
