from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import Album, AlbumDirectory, MusicWatcher, MusicWishlist, MusicInbox, MusicAnnualRecord
from bunker_core.capture import InvalidOccurredOn, parse_occurred_on
from bunker_core.insights import feedback_terminado
from bunker_core.dedup import ya_conocido, es_vigilado, desglosar
from .serializers import AlbumSerializer, AlbumDirectorySerializer, MusicWatcherSerializer, MusicWishlistSerializer, MusicInboxSerializer
from .discogs_oracle import search_album_discogs
from .lastfm_oracle import enrich_album_data


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

    def create(self, request, *args, **kwargs):
        """Sobreescritura del POST para garantizar la idempotencia.

        Mismo contrato que MovieWishlistViewSet: un título repetido responde 200 sin
        guardar, de modo que el radar de Node no ve un error y sigue barriendo, y la
        lista negra (is_rejected=True) también cuenta como 'ya conocido'.
        """
        title = request.data.get('title')

        if title:
            exists = ya_conocido(MusicWishlist.objects.all(), title)
            if exists:
                return Response(
                    {"message": f"'{title}' ya está en el radar o fue rechazado. Ignorando."},
                    status=status.HTTP_200_OK
                )

        # La misma sede unica de relevancia que libros (bunker_core/dedup.py:es_vigilado). Casa
        # por titulo O por artist, y el segundo no es un extra: los vigilados de musica son
        # una BANDA ('Daft Punk'), y un nombre asi no aparece dentro del titulo. Medido el
        # 2026-08-30 sobre las filas vivas: 7 de 10 NO mencionan a su vigilado en el titulo
        # ('Random Access Memories', 'Discovery' y 'Homework' son las tres de Daft Punk), asi
        # que un filtro que solo mirase ahi borraria practicamente el tablon.
        vigilados, exclusiones = desglosar(
            MusicWatcher.objects.filter(is_active=True).values_list('keyword', 'exclusiones'))
        persona = request.data.get('artist')
        # La guardia juzga la manguera del scraper, que SIEMPRE etiqueta (0 de 519 filas
        # producidas sin campo de persona, libros incluidos via `enriquecer`). Un POST que
        # OMITE el campo es un alta a mano desde el movil (movil/app.js:571 postea solo
        # {title}) y no se juzga: rechazarla devuelve 200, la cola lo lee como transmitido y
        # la fila se pierde en silencio.
        if vigilados and persona is not None and not es_vigilado(title, persona, vigilados,
                                                                 exclusiones):
            return Response(
                {"message": "No menciona a ningún vigilado."},
                status=status.HTTP_200_OK
            )
        return super().create(request, *args, **kwargs)


class MusicInboxViewSet(viewsets.ModelViewSet):
    queryset = MusicInbox.objects.all().order_by('-date_scanned')
    serializer_class = MusicInboxSerializer

    def create(self, request, *args, **kwargs):
        """Sobreescritura del POST para garantizar la idempotencia.

        `barcode` es unique: sin esto un código repetido devuelve el error de campo de DRF y
        la captura se queda atascada en la cola del Transmisor, que solo borra con un 2xx.
        """
        barcode = request.data.get('barcode')

        if barcode and MusicInbox.objects.filter(barcode=barcode).exists():
            return Response(
                {"message": f"'{barcode}' ya estaba en el Purgatorio. Ignorando."},
                status=status.HTTP_200_OK
            )

        return super().create(request, *args, **kwargs)


# --- ENDPOINTS DEL ORÁCULO DISCOGS ---


@api_view(['POST'])
def process_barcode(request):
    """Recibe un código de barras del escáner móvil y lo busca en Discogs."""
    barcode = request.data.get('barcode')
    if not barcode:
        return Response({"error": "No se proporcionó código de barras."}, status=status.HTTP_400_BAD_REQUEST)

    album_data = search_album_discogs(barcode, search_type="barcode")

    if album_data:
        # Enriquecer con Last.fm
        lastfm_data = enrich_album_data(album_data['artist'], album_data['title'])
        duration = None
        tracklist = []
        if lastfm_data:
            duration = lastfm_data.get('duration_minutes')
            tracklist = lastfm_data.get('tracklist', [])
            if lastfm_data.get('cover_url'):
                album_data['cover_url'] = lastfm_data.get('cover_url')

        # Lo encontramos! Lo guardamos en el inventario oficial
        Album.objects.create(
            title=album_data['title'],
            artist=album_data['artist'],
            label=album_data['label'],
            release_year=album_data['release_year'],
            format_type=album_data['format_type'],
            genres=album_data['genres'],
            cover_url=album_data['cover_url'],
            duration_minutes=duration,
            tracklist=tracklist
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
        # Enriquecer con Last.fm
        lastfm_data = enrich_album_data(album_data['artist'], album_data['title'])
        duration = None
        tracklist = []
        if lastfm_data:
            duration = lastfm_data.get('duration_minutes')
            tracklist = lastfm_data.get('tracklist', [])
            if lastfm_data.get('cover_url'):
                album_data['cover_url'] = lastfm_data.get('cover_url')
                
        Album.objects.create(
            title=album_data['title'],
            artist=album_data['artist'],
            label=album_data['label'],
            release_year=album_data['release_year'],
            format_type=album_data['format_type'],
            genres=album_data['genres'],
            cover_url=album_data['cover_url'],
            duration_minutes=duration,
            tracklist=tracklist
        )
        return Response({"message": f"Álbum '{album_data['title']}' archivado."}, status=status.HTTP_201_CREATED)

    return Response({"error": "No se encontraron resultados en los archivos de Discogs."}, status=status.HTTP_404_NOT_FOUND)

# --- TRACKER MUSICAL ---


# music/views.py

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
    album_id = request.data.get('album_id')

    if not title:
        return Response({"error": "Falta el título del álbum."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        occurred_on = parse_occurred_on(request.data.get('occurred_on'))
    except InvalidOccurredOn as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    album = None
    if album_id:
        album = Album.objects.filter(id=album_id).first()
        if album is None:
            return Response({"error": "El álbum no existe."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        MusicAnnualRecord.objects.create(
            title=title,
            artist=artist,
            is_owned=is_owned,
            album=album,
            date_listened=occurred_on,
        )
        if album is not None and not album.is_listened:
            album.is_listened = True
            album.save(update_fields=['is_listened'])

    return Response({
        "message": f"'{title}' registrado como escuchado.",
        "feedback": feedback_terminado('discos', title, occurred_on),
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
def delete_annual_record(request, pk):
    """Borra un registro del muro de la fama y revierte el estado del álbum."""
    try:
        record = MusicAnnualRecord.objects.get(pk=pk)

        # Revertir el estado en el inventario si existe la relación
        if record.album:
            record.album.is_listened = False
            record.album.save()

        # Eliminar el registro histórico
        record.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    except MusicAnnualRecord.DoesNotExist:
        return Response({"error": "Registro no encontrado"}, status=status.HTTP_404_NOT_FOUND)
