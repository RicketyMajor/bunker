import re
import os
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rich.markup import render
from .models import Movie, MovieDirectory, MovieWatcher, MovieWishlist, MovieInbox
from .serializers import MovieSerializer, MovieDirectorySerializer, MovieWatcherSerializer, MovieWishlistSerializer, MovieInboxSerializer
from .tmdb_oracle import search_movie_tmdb
from .omdb_oracle import search_movie_omdb
from django.shortcuts import render

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
    queryset = MovieWishlist.objects.filter(
        is_rejected=False).order_by('-date_found')
    serializer_class = MovieWishlistSerializer


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
        original_title=movie_data['original_title'],
        director=movie_data['director'],
        cast=movie_data['cast'],
        release_year=movie_data['release_year'],
        duration_minutes=movie_data['duration_minutes'],
        genres=movie_data['genres'],
        synopsis=movie_data['synopsis'],
        poster_url=movie_data['poster_url']
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
