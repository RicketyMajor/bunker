import os
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum
from django.utils.timezone import localdate
from movies.models import Movie
from catalog.models import Book, ReadingSession, AnnualRecord
from disquera.models import Album, MusicAnnualRecord


def global_dashboard_view(request):
    """BFF: Agrega datos de TODOS los módulos del Bunker para el Launcher en vivo."""

    today = localdate()

    # ═══════════════════════════════════════════
    # SECTOR LITERARIO
    # ═══════════════════════════════════════════
    books = Book.objects.all()
    total_books = books.count()
    read_books = books.filter(is_read=True).count()
    total_pages = sum((b.page_count or 0) for b in books)
    total_book_hours = round((total_pages * 1.5) / 60, 1)

    pages_today = ReadingSession.objects.filter(date=today).aggregate(
        Sum('pages_read'))['pages_read__sum'] or 0

    from catalog.models import Loan, ScanInbox, AnnualRecord
    active_loans = Loan.objects.filter(returned=False).count()
    inbox_count = ScanInbox.objects.count()
    books_this_year = AnnualRecord.objects.filter(date_finished__year=today.year).count()
    books_this_month = AnnualRecord.objects.filter(date_finished__year=today.year, date_finished__month=today.month).count()

    # ═══════════════════════════════════════════
    # SECTOR CINEMATOGRÁFICO
    # ═══════════════════════════════════════════
    from movies.models import MovieAnnualRecord
    movies = Movie.objects.all()
    total_movies = movies.count()
    watched_movies = movies.filter(is_watched=True).count()
    total_movie_minutes = sum((m.duration_minutes or 0) for m in movies)
    total_movie_hours = round(total_movie_minutes / 60, 1)
    movies_this_year = MovieAnnualRecord.objects.filter(date_watched__year=today.year).count()
    movies_this_month = MovieAnnualRecord.objects.filter(date_watched__year=today.year, date_watched__month=today.month).count()

    # ═══════════════════════════════════════════
    # SECTOR MUSICAL
    # ═══════════════════════════════════════════
    from disquera.models import MusicAnnualRecord
    albums = Album.objects.all()
    total_albums = albums.count()
    listened_albums = albums.filter(is_listened=True).count()
    total_tracks = sum((a.track_count or 0) for a in albums)
    total_music_hours = round((total_tracks * 4) / 60, 1)
    music_this_year = MusicAnnualRecord.objects.filter(date_listened__year=today.year).count()
    music_this_month = MusicAnnualRecord.objects.filter(date_listened__year=today.year, date_listened__month=today.month).count()

    # ═══════════════════════════════════════════
    # SECTOR POSADA (RPG)
    # ═══════════════════════════════════════════
    from posada.models import (
        GuildProfile, Adventurer, DeepWorkSession, DailyHabit,
        KanbanTask, CalendarEvent, JournalEntry
    )

    guild = GuildProfile.objects.first()
    guild_data = {}
    if guild:
        guild_data = {
            "prestige_level": guild.prestige_level,
            "prestige": guild.prestige,
            "prestige_meta": guild.prestige_meta,
            "net_worth": guild.net_worth_in_talents,
        }

    adventurers = Adventurer.objects.all()
    active_adventurers = adventurers.filter(is_active=True)
    top_adventurer = adventurers.order_by('-level').first()

    dw_sessions_today = DeepWorkSession.objects.filter(
        start_time__date=today, completed=True)
    dw_minutes_today = sum(s.duration_minutes for s in dw_sessions_today)

    habits = DailyHabit.objects.all()
    total_habits = habits.count()
    completed_habits = habits.filter(last_completed_date=today).count()
    top_streak = habits.order_by('-current_streak').first()

    pending_tasks = KanbanTask.objects.filter(completed_at=None).count()
    today_events = CalendarEvent.objects.filter(status='TODAY').count()

    posada_data = {
        "guild": guild_data,
        "active_adventurers": [
            {"name": a.name, "level": a.level, "class": a.get_adv_class_display()}
            for a in active_adventurers[:5]
        ],
        "top_adventurer": {
            "name": top_adventurer.name,
            "level": top_adventurer.level
        } if top_adventurer else None,
        "dw_minutes_today": dw_minutes_today,
        "dw_sessions_today": dw_sessions_today.count(),
        "habits_completed": completed_habits,
        "habits_total": total_habits,
        "top_streak": {
            "name": top_streak.name,
            "streak": top_streak.current_streak
        } if top_streak and top_streak.current_streak > 0 else None,
        "pending_tasks": pending_tasks,
        "today_events": today_events,
    }

    # ═══════════════════════════════════════════
    # SECTOR AJEDREZ
    # ═══════════════════════════════════════════
    from chess_study.models import ChessRoom, ChessVariation, ChessNote
    chess_data = {
        "rooms": ChessRoom.objects.count(),
        "variations": ChessVariation.objects.count(),
        "notes": ChessNote.objects.count(),
    }

    # ═══════════════════════════════════════════
    # FEED DE ACTIVIDAD CRUZADO
    # ═══════════════════════════════════════════
    feed_lines = []

    if pages_today > 0:
        feed_lines.append(f"📖 Leíste {pages_today} páginas hoy.")

    if dw_minutes_today > 0:
        feed_lines.append(f"⚔️ Deep Work hoy: {dw_minutes_today} minutos.")

    if completed_habits > 0:
        feed_lines.append(f"✅ Hábitos completados: {completed_habits}/{total_habits}.")

    if today_events > 0:
        feed_lines.append(f"📅 Tienes {today_events} evento(s) programado(s) para HOY.")

    if active_loans > 0:
        feed_lines.append(f"📕 {active_loans} libro(s) prestado(s) activo(s).")

    if inbox_count > 0:
        feed_lines.append(f"📬 {inbox_count} ISBN(s) esperando en el Purgatorio.")

    last_movie = movies.order_by('-created_at').first()
    if last_movie:
        feed_lines.append(f"🎬 Último ingreso: {last_movie.title}")

    last_book = books.order_by('-id').first()
    if last_book:
        feed_lines.append(f"📚 Último libro: {last_book.title}")

    last_album = albums.order_by('-created_at').first()
    if last_album:
        feed_lines.append(f"🎵 Último disco: {last_album.title}")

    last_journal = JournalEntry.objects.order_by('-created_at').first()
    if last_journal:
        snippet = last_journal.content[:60] + "..." if len(last_journal.content) > 60 else last_journal.content
        feed_lines.append(f"📝 Diario: \"{snippet}\"")

    return JsonResponse({
        "books": {
            "total": total_books,
            "read": read_books,
            "hours": total_book_hours,
            "pages_today": pages_today,
            "loans": active_loans,
            "inbox": inbox_count,
            "finished_this_year": books_this_year,
            "finished_this_month": books_this_month,
        },
        "movies": {
            "total": total_movies,
            "watched": watched_movies,
            "hours": total_movie_hours,
            "watched_this_year": movies_this_year,
            "watched_this_month": movies_this_month,
        },
        "music": {
            "total": total_albums,
            "listened": listened_albums,
            "hours": total_music_hours,
            "listened_this_year": music_this_year,
            "listened_this_month": music_this_month,
        },
        "posada": posada_data,
        "chess": chess_data,
        "feed": feed_lines[:10],
    })


@csrf_exempt
def backup_database(request):
    """Genera una cápsula de tiempo (JSON) de la base de datos de los 4 módulos."""
    if request.method == 'POST':
        try:
            # Apunta a la raíz del proyecto (donde está el docker-compose)
            backup_path = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), 'bunker_backup.json')

            with open(backup_path, 'w', encoding='utf-8') as f:
                # vuelca específicamente las 4 aplicaciones
                call_command('dumpdata', 'catalog', 'movies', 'disquera',
                             'posada', format='json', indent=4, stdout=f)

            return JsonResponse({"message": "Cápsula de seguridad generada con éxito.", "path": backup_path}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def restore_database(request):
    """Restaura todo el Búnker a partir de la cápsula de tiempo."""
    if request.method == 'POST':
        try:
            backup_path = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), 'bunker_backup.json')

            if not os.path.exists(backup_path):
                return JsonResponse({"error": "No se encontró el archivo bunker_backup.json en la raíz."}, status=404)

            call_command('loaddata', backup_path)

            return JsonResponse({"message": "Búnker restaurado a su estado original."}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método no permitido."}, status=405)
