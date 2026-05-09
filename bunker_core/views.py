from django.http import JsonResponse
from django.db.models import Sum
from django.utils.timezone import localdate
from movies.models import Movie
from catalog.models import Book, ReadingSession, AnnualRecord
from disquera.models import Album, MusicAnnualRecord


def global_dashboard_view(request):
    """BFF: Agrega datos de múltiples microservicios y devuelve un payload optimizado."""

    # Agregaciones Cinematográficas
    movies = Movie.objects.all()
    total_movies = movies.count()
    watched_movies = movies.filter(is_watched=True).count()
    total_movie_minutes = sum((m.duration_minutes or 0) for m in movies)

    # Agregaciones Literarias
    books = Book.objects.all()
    total_books = books.count()
    read_books = books.filter(is_read=True).count()
    total_pages = sum((b.page_count or 0) for b in books)

    # Agregaciones Musicales
    albums = Album.objects.all()
    total_albums = albums.count()
    listened_albums = albums.filter(is_listened=True).count()
    total_tracks = sum((a.track_count or 0) for a in albums)

    # Métricas Cruzadas (Horas de Entretenimiento)
    total_movie_hours = total_movie_minutes / 60
    total_book_hours = (total_pages * 1.5) / 60
    # Asumiendo 4 mins promedio por canción
    total_music_hours = (total_tracks * 4) / 60

    # Generación del Feed de Actividad Curado
    feed_lines = []

    today = localdate()
    pages_today = ReadingSession.objects.filter(date=today).aggregate(
        Sum('pages_read'))['pages_read__sum'] or 0
    if pages_today > 0:
        feed_lines.append(f"**Páginas leídas hoy:** {pages_today}")

    last_movie = movies.order_by('-created_at').first()
    if last_movie:
        feed_lines.append(
            f"**Último ingreso al Videoclub:** {last_movie.title}")

    last_book = books.order_by('-id').first()
    if last_book:
        feed_lines.append(
            f"**Último ingreso a Biblioteca:** {last_book.title}")

    last_album = albums.order_by('-created_at').first()
    if last_album:
        feed_lines.append(
            f"**Último disco en la Disquera:** {last_album.title}")

    last_watched = movies.filter(is_watched=True).order_by('-id').first()
    if last_watched:
        feed_lines.append(f"**Última película vista:** {last_watched.title}")

    last_listened = MusicAnnualRecord.objects.order_by(
        '-date_listened', '-id').first()
    if last_listened:
        feed_lines.append(
            f"**Última sesión de escucha:** {last_listened.title}")

    return JsonResponse({
        "movies": {
            "total": total_movies,
            "watched": watched_movies,
            "hours": round(total_movie_hours, 1)
        },
        "books": {
            "total": total_books,
            "read": read_books,
            "hours": round(total_book_hours, 1)
        },
        "music": {
            "total": total_albums,
            "listened": listened_albums,
            "hours": round(total_music_hours, 1)
        },
        "feed": feed_lines[:6]
    })
