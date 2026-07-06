import re
import os
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rich.markup import render
from .models import Movie, MovieDirectory, MovieWatcher, MovieWishlist, MovieInbox, MovieViewingSession, MovieAnnualRecord
from .serializers import MovieSerializer, MovieDirectorySerializer, MovieWatcherSerializer, MovieWishlistSerializer, MovieInboxSerializer
from .tmdb_oracle import search_movie_tmdb
from .omdb_oracle import search_movie_omdb
from django.shortcuts import render
from django.db.models import Sum
from django.utils import timezone

BARCODE_LOOKUP_KEY = os.getenv("BARCODE_LOOKUP_KEY", "")


class MovieDirectoryViewSet(viewsets.ModelViewSet):
    queryset = MovieDirectory.objects.all()
    serializer_class = MovieDirectorySerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all().order_by('-created_at')
    serializer_class = MovieSerializer


class MovieWatcherViewSet(viewsets.ModelViewSet):
    queryset = MovieWatcher.objects.all().order_by('-created_at')
    serializer_class = MovieWatcherSerializer


class MovieWishlistViewSet(viewsets.ModelViewSet):
    # El queryset por defecto asegura que el GET solo muestre los no rechazados
    queryset = MovieWishlist.objects.filter(
        is_rejected=False).order_by('-date_found')
    serializer_class = MovieWishlistSerializer

    def create(self, request, *args, **kwargs):
        """Sobreescritura del método POST para garantizar la idempotencia."""
        title = request.data.get('title')

        if title:
            # Us .objects sin el filtro de is_rejected y __iexact para ignorar mayúsculas
            # Así revisa si existe en el Tablón activo O en la lista negra.
            exists = MovieWishlist.objects.filter(title__iexact=title).exists()
            if exists:
                # Devolvuelve un 200 OK pero no guarda nada.
                # Al devolver 200, el scraper de Node.js no lanza error y sigue trabajando,
                # pero la base de datos se mantiene sin de duplicados y zombis.
                return Response(
                    {"message": f"'{title}' ya está en el radar o fue rechazada. Ignorando."},
                    status=status.HTTP_200_OK
                )

        # Si es genuinamente nueva, deja     que Django haga el flujo de guardado normal
        return super().create(request, *args, **kwargs)


@api_view(['POST'])
def scan_movie(request):
    """Busca una película en TMDB y la inyecta al Videoclub."""
    title = request.data.get('title')
    if not title:
        return Response({"error": "Se requiere el título de la cinta."}, status=status.HTTP_400_BAD_REQUEST)

    # Evita duplicados
    if Movie.objects.filter(title__icontains=title).exists():
        return Response({"message": "La cinta ya está en las bóvedas del Videoclub."}, status=status.HTTP_200_OK)

    # Invoca al Oráculo
    movie_data = search_movie_tmdb(title)

    if not movie_data:
        return Response({"error": "La cinta no fue encontrada en los registros de TMDB."}, status=status.HTTP_404_NOT_FOUND)

    # Guarda la película
    movie = Movie.objects.create(
        title=movie_data['title'],
        original_title=movie_data.get('original_title', ''),
        director=movie_data.get('director', 'Desconocido'),
        writers=movie_data.get(
            'writers', 'Desconocido'),
        production_company=movie_data.get(
            'production_company', ''),
        cast=movie_data.get('cast', ''),
        release_year=movie_data.get('release_year'),
        duration_minutes=movie_data.get('duration_minutes', 0),
        genres=movie_data.get('genres', []),
        synopsis=movie_data.get('synopsis', ''),
        poster_url=movie_data.get('poster_url', '')
    )

    return Response({
        "message": f"¡Cinta '{movie.title}' procesada y archivada!",
        "id": movie.id
    }, status=status.HTTP_201_CREATED)


class MovieInboxViewSet(viewsets.ModelViewSet):
    queryset = MovieInbox.objects.all().order_by('-date_scanned')
    serializer_class = MovieInboxSerializer


# --- HELPERS COMERCIALES EXHAUSTIVOS ---

def clean_movie_title(raw_title):
    if not raw_title:
        return None
    # Elimina ruidos comerciales y etiquetas de edición
    clean = re.sub(r'(?i)(blu-ray|bluray|dvd|4k|uhd|steelbook|edición|edition|import|combo|pack|mint|rare|sealed|new|widescreen|fullscreen|region \d)', '', raw_title)
    clean = re.split(r'[-(\[|:]', clean)[0].strip()
    clean = re.sub(r'^\d+\s+', '', clean)
    return clean.strip()


def search_barcode_lookup(barcode):
    """Nodo de Alta Prioridad: Barcode Lookup (Requiere API Key)"""
    if not BARCODE_LOOKUP_KEY:
        return None
    try:
        url = f"https://api.barcodelookup.com/v3/products?barcode={barcode}&formatted=y&key={BARCODE_LOOKUP_KEY}"
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            return data['products'][0]['title']
    except:
        pass
    return None


def search_upcitemdb(barcode):
    """Nodo 2: UPCitemdb (Nuestra base actual)"""
    try:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        resp = requests.get(url, timeout=4.0)
        if resp.status_code == 200 and resp.json().get('items'):
            return resp.json()['items'][0]['title']
    except:
        pass
    return None


def resolve_barcode_exhaustively(barcode):
    """Estrategia de búsqueda federada."""
    print(f"[SISTEMA] Iniciando búsqueda federada para: {barcode}")

    # 1. Intentar con el nodo premium (Barcode Lookup)
    title = search_barcode_lookup(barcode)
    if title:
        return clean_movie_title(title)

    # 2. Intentar con el nodo estándar (UPCitemdb)
    title = search_upcitemdb(barcode)
    if title:
        return clean_movie_title(title)

    # 3. Nodo de emergencia (Scraper de UPCIndex)
    try:
        resp = requests.get(
            f"https://www.upcindex.com/{barcode}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3.0)
        if resp.status_code == 200:
            match = re.search(r'<title>(.*?)</title>',
                              resp.text, re.IGNORECASE)
            if match:
                title = match.group(1).replace(
                    "UPC", "").replace(barcode, "").strip()
                if len(title) > 3 and "No found" not in title:
                    return clean_movie_title(title)
    except:
        pass

    return None

# --- RUTAS DE ESCANEO ---


@api_view(['POST'])
def receive_barcode(request):
    """DEPÓSITO ULTRARRÁPIDO: El celular solo lanza el código numérico y sigue su camino."""
    barcode = request.data.get('barcode')
    if not barcode:
        return Response({"error": "Falta el código de barras."}, status=status.HTTP_400_BAD_REQUEST)

    MovieInbox.objects.get_or_create(barcode=barcode, defaults={
        'title': "En Cuarentena..."})
    return Response({"message": f"Código {barcode} asegurado en el Inbox."}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def process_barcode(request):
    """PROCESAMIENTO PESADO: Detonado por la tecla ENTER en el TUI."""
    barcode = request.data.get('barcode')
    if not barcode:
        return Response({"error": "Falta el código de barras."}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Búsqueda Comercial Exhaustiva
    clean_title = resolve_barcode_exhaustively(barcode)
    if not clean_title:
        return Response({"error": f"Búsqueda agotada. El código {barcode} no figura en las bases comerciales."}, status=status.HTTP_404_NOT_FOUND)

    # 2. Validación de Duplicados
    if Movie.objects.filter(title__icontains=clean_title).exists():
        return Response({"error": f"'{clean_title}' ya está en tus bóvedas."}, status=status.HTTP_400_BAD_REQUEST)

    # 3. Invocación al Oráculo Principal (TMDB) con Búsqueda Iterativa
    movie_data = search_movie_tmdb(clean_title)
    words = clean_title.split()

    if not movie_data:
        # Intenta buscar solo las primeras 3 palabras
        if len(words) > 3:
            short_title = " ".join(words[:3])
            movie_data = search_movie_tmdb(short_title)

            # Intentamos con las primeras 2
            if not movie_data and len(words) > 2:
                shorter_title = " ".join(words[:2])
                movie_data = search_movie_tmdb(shorter_title)

    # 4. Invocación al Oráculo Secundario (OMDb)
    if not movie_data:
        print(
            f"[AVISO] TMDB falló con '{clean_title}'. Enrutando hacia OMDb...")
        movie_data = search_movie_omdb(clean_title)

        # Si OMDb también falla con el título largo, aplica las mismas reducciones
        if not movie_data and len(words) > 3:
            movie_data = search_movie_omdb(" ".join(words[:3]))

        if not movie_data and len(words) > 2:
            movie_data = search_movie_omdb(" ".join(words[:2]))

    # 5. Rendición Total (Todos los nodos fallaron)
    if not movie_data:
        return Response({"error": f"Comercio arrojó '{clean_title}', pero ni TMDB ni OMDb lo reconocen."}, status=status.HTTP_404_NOT_FOUND)

    # 6. Guardado Final en la Base de Datos
    Movie.objects.create(
        title=movie_data['title'],
        original_title=movie_data.get('original_title', ''),
        director=movie_data.get('director', 'Desconocido'),
        cast=movie_data.get('cast', ''),
        release_year=movie_data.get('release_year'),
        duration_minutes=movie_data.get('duration_minutes', 0),
        genres=movie_data.get('genres', []),
        synopsis=movie_data.get('synopsis', ''),
        poster_url=movie_data.get('poster_url', '')
    )

    return Response({"message": f"'{movie_data['title']}' extraída y archivada con éxito."}, status=status.HTTP_201_CREATED)


def movie_scanner_view(request):
    """Renderiza el escáner QR aislado exclusivamente para películas."""
    return render(request, 'movies/movie_scanner.html')

# ================= TRACKER Y HÁBITOS (VIDEOCLUB) =================


@api_view(['GET'])
def tracker_stats(request):
    """Devuelve las estadísticas del mes en curso basadas en las películas terminadas."""
    today = timezone.localdate()
    start_of_month = today.replace(day=1)

    # Cuenta cuántos registros se crearon en el mes
    movies_this_month = MovieAnnualRecord.objects.filter(
        date_watched__gte=start_of_month, date_watched__lte=today).count()

    return Response({
        "current_month": today.strftime("%B").capitalize(),
        "movies_this_month": movies_this_month
    })


@api_view(['GET'])
def tracker_annual(request):
    """Devuelve el historial inmutable de películas vistas este año."""
    today = timezone.localdate()
    start_of_year = today.replace(month=1, day=1)

    records = MovieAnnualRecord.objects.filter(
        date_watched__gte=start_of_year).order_by('-date_watched', '-id')

    data = [
        {
            "id": r.id,
            "title": r.title,
            "director": r.director or "Desconocido",
            "is_owned": r.is_owned,
            "date_watched": r.date_watched.strftime("%Y-%m-%d")
        } for r in records
    ]
    return Response(data)


@api_view(['GET'])
def tracker_heatmap(request):
    """Devuelve el conteo de películas vistas agrupadas por mes para el año en curso."""
    today = timezone.localdate()
    start_of_year = today.replace(month=1, day=1)

    records = MovieAnnualRecord.objects.filter(date_watched__gte=start_of_year)
    counts = [0] * 12
    for r in records:
        counts[r.date_watched.month - 1] += 1

    return Response({"counts": counts})


@api_view(['POST'])
def log_minutes(request):
    """Anota minutos vistos en el día actual."""
    minutes = request.data.get('minutes')
    if not minutes:
        return Response({"error": "Faltan los minutos."}, status=status.HTTP_400_BAD_REQUEST)

    MovieViewingSession.objects.create(minutes_watched=int(minutes))
    return Response({"message": f"Anotados {minutes} minutos de visionado."}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def finish_movie(request):
    """Registra una película como 'Vista' en el Muro de la Fama."""
    title = request.data.get('title')
    director = request.data.get('director', 'Desconocido')
    is_owned = request.data.get('is_owned', True)

    if not title:
        return Response({"error": "Falta el título."}, status=status.HTTP_400_BAD_REQUEST)

    # Guarda en el registro inmutable
    MovieAnnualRecord.objects.create(
        title=title,
        director=director,
        is_owned=is_owned
    )
    return Response({"message": "Película añadida al historial anual."}, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
def delete_annual_record(request, pk):
    """Borra un registro del muro de la fama y revierte el estado de la película."""
    try:
        record = MovieAnnualRecord.objects.get(pk=pk)

        # Revertir el estado en el inventario si existe la relación
        if record.movie:
            record.movie.is_watched = False
            record.movie.save()

        # Eliminar el registro histórico
        record.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    except MovieAnnualRecord.DoesNotExist:
        return Response({"error": "Registro no encontrado"}, status=status.HTTP_404_NOT_FOUND)
