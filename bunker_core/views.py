import json
import logging
import os
import secrets
from django.core.management import call_command
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils.timezone import localdate
from datetime import timedelta
from catalog.models import Book, ReadingSession, AnnualRecord as BookAnnualRecord
from movies.models import Movie, MovieAnnualRecord
from disquera.models import Album, MusicAnnualRecord
from posada.models import GuildProfile, Adventurer, DeepWorkSession, DailyHabit, KanbanTask, CalendarEvent, JournalEntry
from chess_study.models import ChessRoom, ChessVariation, SolvedPuzzle
from posada.achievements import evaluate_achievements

logger = logging.getLogger(__name__)

# Las 5 apps que entran en la capsula del tiempo.
BACKUP_APPS = ('catalog', 'movies', 'disquera', 'posada', 'chess_study')
# Donde escribe el cron nocturno (volumen bunker_backups_data).
BACKUP_DIR = '/app/backups'
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
    """BFF: Agrega datos de TODOS los módulos de forma hiper-robusta y granular."""
    today = localdate()

    data = {
        "posada": {}, "books": {}, "movies": {}, "music": {}, "chess": {}, "feed": []
    }
    feed = []

    # 1. SECTOR LITERARIO
    try:
        books = Book.objects.all()
        data["books"]["total"] = books.count()
        data["books"]["read"] = books.filter(is_read=True).count()
        total_pages = books.aggregate(Sum('page_count'))['page_count__sum'] or 0
        data["books"]["hours"] = round((total_pages * 1.5) / 60, 1)
        
        # Calculate reading streak
        from catalog.models import ReadingSession
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
        data["movies"]["hours"] = data["movies"]["watched"] * 2
        
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
        data["music"]["hours"] = round(data["music"]["listened"] * 0.75, 1)

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

    # 4. AJEDREZ
    try:
        data["chess"]["rooms"] = ChessRoom.objects.count()
        data["chess"]["variations"] = ChessVariation.objects.count()
        data["chess"]["puzzles"] = SolvedPuzzle.objects.count()
    except Exception:
        logger.warning("Fallo el bloque Ajedrez del dashboard", exc_info=True)

    # 5. POSADA (MÉTRICAS BLINDADAS)
    posada_data = {}
    
    try:
        guild, _ = GuildProfile.objects.get_or_create(id=1)
        posada_data["guild"] = {
            "prestige_level": guild.prestige_level,
            "prestige": guild.prestige,
            "prestige_meta": guild.prestige_meta,
            "net_worth": getattr(guild, 'net_worth_in_talents', getattr(guild, 'talento', 0))
        }
    except Exception as e:
        feed.append(f"[red]Error Gremio:[/] {str(e)[:30]}")
        
    try:
        # Una sola consulta agrupada por dia cubre el sparkline de 7 dias y el total de hoy;
        # antes eran 8 agregaciones, una por iteracion del bucle.
        semana = (DeepWorkSession.objects
                  .filter(completed=True, start_time__date__gte=today - timedelta(days=6))
                  .annotate(dia=TruncDate('start_time'))
                  .values('dia')
                  .annotate(total=Sum('duration_minutes')))
        minutos_por_dia = {row['dia']: row['total'] or 0 for row in semana}

        posada_data["dw_minutes_today"] = minutos_por_dia.get(today, 0)
        posada_data["dw_history"] = [
            minutos_por_dia.get(today - timedelta(days=6 - i), 0) for i in range(7)]
        # Historico completo, no solo la semana: es lo que mide el logro "Mente de Acero".
        posada_data["dw_sessions_total"] = DeepWorkSession.objects.filter(completed=True).count()

    except Exception as e:
        logger.warning("Fallo el bloque Deep Work del dashboard", exc_info=True)
        feed.append(f"[red]Error DW:[/] {str(e)[:30]}")

    try:
        advs = Adventurer.objects.all()
        posada_data["active_adventurers"] = list(advs.values_list('id', flat=True))
        top_adv = advs.order_by('-level', '-experience').first()
        posada_data["top_adventurer"] = {"name": top_adv.name, "level": top_adv.level} if top_adv else None
    except Exception as e:
        logger.warning("Fallo el bloque Aventureros del dashboard", exc_info=True)
        feed.append(f"[red]Error Aventureros:[/] {str(e)[:30]}")

    try:
        habits = DailyHabit.objects.all()
        posada_data["habits_total"] = habits.count()
        # last_completed_date es lo que marca complete_habit, y es el mismo criterio que usa
        # list_habits ("completed_today"). El bucle anterior probaba un metodo inexistente
        # (is_completed_today) y caia en last_evaluated_date, que el cierre diario deja en
        # AYER: el contador daba 0 aunque el usuario hubiera completado todo.
        posada_data["habits_completed"] = habits.filter(last_completed_date=today).count()
        top_habit = habits.order_by('-current_streak').first()
        posada_data["top_streak"] = {"name": top_habit.name, "streak": top_habit.current_streak} if top_habit else None
    except Exception as e:
        logger.warning("Fallo el bloque Habitos del dashboard", exc_info=True)
        feed.append(f"[red]Error Hábitos:[/] {str(e)[:30]}")

    try:
        posada_data["pending_tasks"] = KanbanTask.objects.exclude(column__title__icontains='hecho').exclude(column__title__icontains='done').count()
    except Exception as e:
        feed.append(f"[red]Error Kanban:[/] {str(e)[:30]}")

    try:
        # CalendarEvent.date es un DateField: el intento previo con start_date__date lanzaba
        # FieldError en cada carga del dashboard y caia a este mismo query por el except.
        posada_data["today_events"] = CalendarEvent.objects.filter(date=today).count()
    except Exception as e:
        logger.warning("Fallo el bloque Calendar del dashboard", exc_info=True)
        feed.append(f"[red]Error Calendar:[/] {str(e)[:30]}")

    data["posada"] = posada_data

    # 6. LOGROS
    # Reaprovecha contadores que los bloques de arriba ya calcularon; solo aporta la consulta
    # al catalogo y, cuando de verdad se desbloquea algo, la escritura. Una metrica ausente
    # (su modulo fallo) se omite: sin dato no se desbloquea nada.
    try:
        top_streak = posada_data.get("top_streak") or {}
        contadores = {
            "books_read": data["books"].get("read"),
            # El logro cuenta lo VISTO/ESCUCHADO, que vive en el registro anual, no en el
            # inventario: se ve mucho de lo que no se posee. data["movies"]["watched"] sigue
            # siendo la metrica de inventario que pinta el TUI, y es correcta para eso.
            "movies_watched": MovieAnnualRecord.objects.count(),
            "albums_listened": MusicAnnualRecord.objects.count(),
            "deep_work_sessions": posada_data.get("dw_sessions_total"),
            "puzzles_solved": data["chess"].get("puzzles"),
            "habit_streak": top_streak.get("streak"),
        }
        contadores = {k: v for k, v in contadores.items() if v is not None}

        # El Renacentista pide >= 1 en los cinco modulos, que es justo el minimo de los cinco
        # contadores. Expresarlo como una metrica mas evita que necesite su propia rama.
        cinco = ("books_read", "movies_watched", "albums_listened",
                 "deep_work_sessions", "puzzles_solved")
        if all(m in contadores for m in cinco):
            contadores["renacentista"] = min(contadores[m] for m in cinco)

        data["achievements"] = evaluate_achievements(contadores)
    except Exception:
        logger.warning("Fallo la evaluacion de logros", exc_info=True)
        data["achievements"] = []

    # 7. TRÁFICO DE RED (FEED GLOBAL SEGURO)
    try:
        for dw in DeepWorkSession.objects.filter(completed=True).order_by('-start_time')[:3]:
            feed.append(f"[cyan]⏱️  DW:[/] {dw.category} ({dw.duration_minutes}m)")
    except Exception:
        logger.warning("Fallo el feed de Deep Work", exc_info=True)

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
    """Genera una cápsula de tiempo (JSON) de la base de datos de los 5 módulos."""
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
def list_backups(request):
    """Lista las cápsulas automáticas del volumen, de la más reciente a la más antigua."""
    rejected = _reject_if_bad_token(request)
    if rejected:
        return rejected

    try:
        names = sorted(
            (n for n in os.listdir(BACKUP_DIR) if n.endswith('.json')), reverse=True)
        archivos = [{
            "filename": n,
            "size_bytes": os.path.getsize(os.path.join(BACKUP_DIR, n)),
        } for n in names]
    except FileNotFoundError:
        archivos = []

    return JsonResponse({
        "automaticos": archivos,
        "manual": os.path.basename(ROOT_BACKUP) if os.path.exists(ROOT_BACKUP) else None,
    }, status=200)


@csrf_exempt
def restore_database(request):
    """Restaura el Búnker desde una cápsula.

    Sin `filename` usa el backup manual de la raíz (comportamiento histórico). Con `filename`
    restaura una de las cápsulas automáticas del volumen, que hasta ahora eran inalcanzables.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido."}, status=405)

    rejected = _reject_if_bad_token(request)
    if rejected:
        return rejected

    filename = request.POST.get('filename') or ''
    if not filename and request.body:
        try:
            filename = json.loads(request.body).get('filename') or ''
        except (ValueError, AttributeError):
            filename = ''
    filename = filename.strip()
    if filename:
        # basename() corta cualquier "../": el nombre viene de fuera y solo puede
        # referirse a un archivo dentro del directorio de backups.
        safe_name = os.path.basename(filename)
        backup_path = os.path.join(BACKUP_DIR, safe_name)
    else:
        backup_path = ROOT_BACKUP

    if not os.path.exists(backup_path):
        return JsonResponse({"error": f"No se encontró la cápsula '{os.path.basename(backup_path)}'."}, status=404)

    try:
        call_command('loaddata', backup_path)
        return JsonResponse(
            {"message": "Búnker restaurado a su estado original.", "restored_from": backup_path}, status=200)
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
    """The PWA. One template, inline CSS, no build step and no CDN."""
    return render(request, 'movil/app.html')


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
    hoy = localdate()

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

    # Only habits that are actually due today. `valid_days` is a comma-separated list of
    # weekday numbers, and it is what the penalty engine reads (legacy.py:481) — offering a
    # Monday-only habit on a Sunday would pay prestige for a day the engine never scored.
    # ponytail: substring match, correct because weekdays are single digits 0-6; if the
    # field ever holds anything wider, this needs a real membership test.
    habitos = list(
        DailyHabit.objects
        .filter(valid_days__contains=str(hoy.weekday()))
        .exclude(last_completed_date=hoy)
        .values("id", "name", "difficulty", "is_bad_habit")
    )

    return JsonResponse({
        "leyendo": leyendo,
        "habitos_pendientes": habitos,
        "libros": list(Book.objects.filter(is_read=False).values("id", "title")[:500]),
        "peliculas": list(Movie.objects.filter(is_watched=False).values("id", "title")[:500]),
        "albums": list(Album.objects.filter(is_listened=False).values("id", "title")[:500]),
    })
