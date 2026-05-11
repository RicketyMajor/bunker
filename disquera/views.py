from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Album, AlbumDirectory, MusicWatcher, MusicWishlist, MusicInbox, MusicAnnualRecord
from .serializers import AlbumSerializer, AlbumDirectorySerializer, MusicWatcherSerializer, MusicWishlistSerializer, MusicInboxSerializer
from .discogs_oracle import search_album_discogs


class AlbumDirectoryViewSet(viewsets.ModelViewSet):
    queryset = AlbumDirectory.objects.all()
    serializer_class = AlbumDirectorySerializer


class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all().order_by('-created_at')
    serializer_class = AlbumSerializer


class MusicWatcherViewSet(viewsets.ModelViewSet):
    queryset = MusicWatcher.objects.all().order_by('-created_at')
    serializer_class = MusicWatcherSerializer


class MusicWishlistViewSet(viewsets.ModelViewSet):
    queryset = MusicWishlist.objects.filter(
        is_rejected=False).order_by('-date_found')
    serializer_class = MusicWishlistSerializer


class MusicInboxViewSet(viewsets.ModelViewSet):
    queryset = MusicInbox.objects.all().order_by('-date_scanned')
    serializer_class = MusicInboxSerializer

# --- ENDPOINTS DEL ORÁCULO DISCOGS ---


@api_view(['POST'])
def process_barcode(request):
    """Recibe un código de barras del escáner móvil y lo busca en Discogs."""
    barcode = request.data.get('barcode')
    if not barcode:
        return Response({"error": "No se proporcionó código de barras."}, status=status.HTTP_400_BAD_REQUEST)

    album_data = search_album_discogs(barcode, search_type="barcode")

    if album_data:
        # Lo encontramos! Lo guardamos en el inventario oficial
        Album.objects.create(
            title=album_data['title'],
            artist=album_data['artist'],
            label=album_data['label'],
            release_year=album_data['release_year'],
            format_type=album_data['format_type'],
            genres=album_data['genres'],
            cover_url=album_data['cover_url']
        )
        return Response({"message": "Álbum procesado y guardado en la Disquera."}, status=status.HTTP_201_CREATED)
    else:
        # Si no lo encuentra, lo guarda en el Inbox para ingreso manual posterior
        MusicInbox.objects.get_or_create(barcode=barcode)
        return Response({"error": "Código no hallado en Discogs. Archivado en el Inbox."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def scan_album(request):
    """Busca un álbum por título/artista y lo añade al inventario (Ingreso semi-automático)."""
    title = request.data.get('title')
    if not title:
        return Response({"error": "Falta el título para la búsqueda."}, status=status.HTTP_400_BAD_REQUEST)

    album_data = search_album_discogs(title, search_type="title")

    if album_data:
        Album.objects.create(
            title=album_data['title'],
            artist=album_data['artist'],
            label=album_data['label'],
            release_year=album_data['release_year'],
            format_type=album_data['format_type'],
            genres=album_data['genres'],
            cover_url=album_data['cover_url']
        )
        return Response({"message": f"Álbum '{album_data['title']}' archivado."}, status=status.HTTP_201_CREATED)

    return Response({"error": "No se encontraron resultados en los archivos de Discogs."}, status=status.HTTP_404_NOT_FOUND)

# --- TRACKER MUSICAL ---


# disquera/views.py

@api_view(['GET'])
def tracker_stats(request):
    """Devuelve estadísticas del mes en curso para la música con nombres en español."""
    today = timezone.localdate()
    start_of_month = today.replace(day=1)

    # Conteo mensual (Solo lo que se registró desde el día 1 de este mes)
    albums_this_month = MusicAnnualRecord.objects.filter(
        date_listened__gte=start_of_month,
        date_listened__lte=today
    ).count()

    # Mapeo para asegurar el idioma
    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    return Response({
        "current_month": meses_es.get(today.month),
        "albums_this_month": albums_this_month
    })


@api_view(['GET'])
def tracker_annual(request):
    """Devuelve los discos escuchados en el año actual."""
    now = timezone.localdate()
    start_of_year = now.replace(month=1, day=1)
    records = MusicAnnualRecord.objects.filter(
        date_listened__gte=start_of_year).order_by('-date_listened', '-id')

    data = [
        {
            "id": r.id,
            "title": r.title,
            "artist": r.artist or "Desconocido",
            "is_owned": r.is_owned,
            "date_listened": r.date_listened.strftime("%Y-%m-%d")
        } for r in records
    ]
    return Response(data)


@api_view(['POST'])
def finish_album(request):
    """Registra una sesión de escucha en el muro de la fama."""
    title = request.data.get('title')
    artist = request.data.get('artist', 'Desconocido')
    is_owned = request.data.get('is_owned', True)

    if not title:
        return Response({"error": "Falta el título del álbum."}, status=status.HTTP_400_BAD_REQUEST)

    MusicAnnualRecord.objects.create(
        title=title,
        artist=artist,
        is_owned=is_owned
    )
    return Response({"message": f"'{title}' registrado como escuchado."}, status=status.HTTP_201_CREATED)
