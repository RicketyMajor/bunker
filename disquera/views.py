from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Album, AlbumDirectory, MusicWatcher, MusicWishlist, MusicInbox, MusicAnnualRecord
from .serializers import AlbumSerializer, AlbumDirectorySerializer, MusicWatcherSerializer, MusicWishlistSerializer, MusicInboxSerializer


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

# --- ENDPOINTS FANTASMA (FASE 2) ---


@api_view(['POST'])
def process_barcode(request):
    return Response({"error": "Oráculo de Discogs inactivo. (Requiere Fase 2)"}, status=501)


@api_view(['POST'])
def scan_album(request):
    return Response({"error": "Búsqueda manual inactiva. (Requiere Fase 2)"}, status=501)

# --- TRACKER MUSICAL ---


@api_view(['GET'])
def tracker_stats(request):
    """Devuelve estadísticas del mes en curso para la música."""
    today = timezone.localdate()
    start_of_month = today.replace(day=1)

    albums_this_month = MusicAnnualRecord.objects.filter(
        date_listened__gte=start_of_month, date_listened__lte=today).count()

    return Response({
        "current_month": today.strftime("%B").capitalize(),
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
