from django.http import JsonResponse
from django.db.models import Sum
from django.utils.timezone import localdate
from movies.models import Movie
from catalog.models import Book, ReadingSession, AnnualRecord


def global_dashboard_view(request):
    """BFF: Agrega datos de múltiples microservicios y devuelve un payload optimizado."""

    # 1. Agregaciones Cinematográficas
    movies = Movie.objects.all()
    total_movies = movies.count()
    watched_movies = movies.filter(is_watched=True).count()
    total_movie_minutes = sum((m.duration_minutes or 0) for m in movies)

    # 2. Agregaciones Literarias
    books = Book.objects.all()
    total_books = books.count()
    read_books = books.filter(is_read=True).count()
    total_pages = sum((b.page_count or 0) for b in books)

    # 3. Métricas Cruzadas (Horas de Entretenimiento)
    total_movie_hours = total_movie_minutes / 60
    # Estimación: 1.5 min por página
    total_book_hours = (total_pages * 1.5) / 60

    # 4. Generación del Feed de Actividad Curado (Hitos)
    feed_lines = []

    # Hito 1: Páginas leídas hoy (Consultando tu ReadingSession)
    today = localdate()
    pages_today = ReadingSession.objects.filter(date=today).aggregate(
        Sum('pages_read'))['pages_read__sum'] or 0
    if pages_today > 0:
        feed_lines.append(f"**Páginas leídas hoy:** {pages_today}")
    else:
        feed_lines.append(
            f"**Páginas leídas hoy:** 0 (¡Aún hay tiempo para leer!)")

    # Hito 2: Último ingreso al Videoclub
    last_movie = movies.order_by('-created_at').first()
    if last_movie:
        feed_lines.append(
            f"**Último ingreso al Videoclub:** {last_movie.title}")

    # Hito 3: Último ingreso a la Biblioteca
    last_book = books.order_by('-id').first()
    if last_book:
        feed_lines.append(
            f"**Último ingreso a Biblioteca:** {last_book.title}")

    # Hito 4: Última película vista
    # (Usa el ID inverso como aproximación cronológica)
    last_watched = movies.filter(is_watched=True).order_by('-id').first()
    if last_watched:
        feed_lines.append(f"**Última película vista:** {last_watched.title}")

    # Hito 5: Último libro terminado (Consulta el AnnualRecord)
    last_finished = AnnualRecord.objects.order_by(
        '-date_finished', '-id').first()
    if last_finished:
        feed_lines.append(
            f"**Último libro terminado:** {last_finished.title}")

    return JsonResponse({
        "movies": {"total": total_movies, "watched": watched_movies, "hours": round(total_movie_hours, 1)},
        "books": {"total": total_books, "read": read_books, "hours": round(total_book_hours, 1)},
        "feed": feed_lines
    })
