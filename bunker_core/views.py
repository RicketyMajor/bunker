import os
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum
from django.utils.timezone import localdate
from datetime import timedelta
from catalog.models import Book, AnnualRecord as BookAnnualRecord
from movies.models import Movie, MovieAnnualRecord
from disquera.models import Album, MusicAnnualRecord
from posada.models import GuildProfile, Adventurer, DeepWorkSession, DailyHabit, KanbanTask, CalendarEvent, JournalEntry
from chess_study.models import ChessRoom, ChessVariation

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
        total_pages = sum((b.page_count or 0) for b in books)
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

        # Minutes listened this week
        from disquera.models import ListeningEntry
        start_of_week = today - timedelta(days=today.weekday())
        entries = ListeningEntry.objects.filter(date__gte=start_of_week)
        minutes_this_week = entries.aggregate(Sum('minutes_listened'))['minutes_listened__sum'] or 0
        data["music"]["minutes_week"] = minutes_this_week
        
        top_album = albums.filter(personal_rating__isnull=False).order_by('-personal_rating').first()
        if top_album:
            data["music"]["top_rated"] = {"title": top_album.title, "rating": float(top_album.personal_rating)}
            
    except Exception as e:
        feed.append(f"[red]Error Disquera:[/] {str(e)[:40]}")

    # 4. AJEDREZ
    try:
        data["chess"]["rooms"] = ChessRoom.objects.count()
        data["chess"]["variations"] = ChessVariation.objects.count()
    except Exception as e:
        pass

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
        # Extraer DW de hoy
        dw = DeepWorkSession.objects.filter(start_time__date=today, completed=True)
        posada_data["dw_minutes_today"] = dw.aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
        
        # --- NUEVO: Historial de 7 días para el Sparkline ---
        dw_history = []
        for i in range(7):
            d = today - timedelta(days=6 - i)
            mins = DeepWorkSession.objects.filter(start_time__date=d, completed=True).aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
            dw_history.append(mins)
        posada_data["dw_history"] = dw_history

    except Exception as e:
        feed.append(f"[red]Error DW:[/] {str(e)[:30]}")

    try:
        advs = Adventurer.objects.all()
        posada_data["active_adventurers"] = [a.id for a in advs]
        top_adv = advs.order_by('-level', '-experience').first()
        posada_data["top_adventurer"] = {"name": top_adv.name, "level": top_adv.level} if top_adv else None
    except Exception as e:
        feed.append(f"[red]Error Aventureros:[/] {str(e)[:30]}")

    try:
        habits = DailyHabit.objects.all()
        posada_data["habits_total"] = habits.count()
        habits_completed = 0
        for h in habits:
            try:
                if hasattr(h, 'is_completed_today') and h.is_completed_today():
                    habits_completed += 1
                elif getattr(h, 'last_evaluated_date', None) == today: 
                    habits_completed += 1
            except: pass
        posada_data["habits_completed"] = habits_completed
        top_habit = habits.order_by('-current_streak').first()
        posada_data["top_streak"] = {"name": top_habit.name, "streak": top_habit.current_streak} if top_habit else None
    except Exception as e:
        feed.append(f"[red]Error Hábitos:[/] {str(e)[:30]}")

    try:
        posada_data["pending_tasks"] = KanbanTask.objects.exclude(column__title__icontains='hecho').exclude(column__title__icontains='done').count()
    except Exception as e:
        feed.append(f"[red]Error Kanban:[/] {str(e)[:30]}")

    try:
        try:
            today_events = CalendarEvent.objects.filter(start_date__date=today).count()
        except:
            today_events = CalendarEvent.objects.filter(date=today).count()
        posada_data["today_events"] = today_events
    except Exception as e:
        feed.append(f"[red]Error Calendar:[/] {str(e)[:30]}")

    data["posada"] = posada_data

    # 6. TRÁFICO DE RED (FEED GLOBAL SEGURO)
    try:
        for dw in DeepWorkSession.objects.filter(completed=True).order_by('-start_time')[:3]:
            feed.append(f"[cyan]⏱️  DW:[/] {dw.category} ({dw.duration_minutes}m)")
    except: pass
        
    try:
        for rb in BookAnnualRecord.objects.order_by('-date_finished')[:3]:
            title = getattr(rb.book, 'title', 'Libro') if hasattr(rb, 'book') else 'Libro'
            feed.append(f"[green]📚 Leído:[/] {str(title)[:25]}")
    except: pass
        
    try:
        for rm in MovieAnnualRecord.objects.order_by('-date_finished')[:2]:
            title = getattr(rm.movie, 'title', 'Pelicula') if hasattr(rm, 'movie') else 'Pelicula'
            feed.append(f"[yellow]🎬 Visto:[/] {str(title)[:25]}")
    except: pass

    data["feed"] = feed
    return JsonResponse(data, status=200)


@csrf_exempt
def backup_database(request):
    """Genera una cápsula de tiempo (JSON) de la base de datos de los 4 módulos."""
    if request.method == 'POST':
        # 🛡️ Seguridad: Validar Token Secreto
        token = request.headers.get("X-Bunker-Token")
        expected_token = os.environ.get("BUNKER_BACKUP_TOKEN", "bunker_local_secure_99")
        if token != expected_token:
            return JsonResponse({"error": "Acceso denegado: Token de seguridad inválido o ausente."}, status=403)

        try:
            # Apunta a la raíz del proyecto (donde está el docker-compose)
            backup_path = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), 'bunker_backup.json')

            with open(backup_path, 'w', encoding='utf-8') as f:
                # vuelca específicamente las 5 aplicaciones
                call_command('dumpdata', 'catalog', 'movies', 'disquera',
                             'posada', 'chess_study', format='json', indent=4, stdout=f)

            return JsonResponse({"message": "Cápsula de seguridad generada con éxito.", "path": backup_path}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def restore_database(request):
    """Restaura todo el Búnker a partir de la cápsula de tiempo."""
    if request.method == 'POST':
        # 🛡️ Seguridad: Validar Token Secreto
        token = request.headers.get("X-Bunker-Token")
        expected_token = os.environ.get("BUNKER_BACKUP_TOKEN", "bunker_local_secure_99")
        if token != expected_token:
            return JsonResponse({"error": "Acceso denegado: Token de seguridad inválido o ausente."}, status=403)

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
