from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Book, Author, Genre, Watcher, WishlistItem, Friend, Loan, ReadingSession, AnnualRecord, Directory, ScanInbox
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from rest_framework import viewsets
from .serializers import BookSerializer, WatcherSerializer, WishlistItemSerializer, FriendSerializer, LoanSerializer, AnnualRecordSerializer, DirectorySerializer
from cli.api import fetch_book_by_isbn
import django_filters
from .serializers import ScanInboxSerializer


@api_view(['POST'])
def scan_book(request):
    """
    Recibe un ISBN y opcionalmente la metadata seleccionada, y lo guarda en la BD.
    """
    # Extrae el ISBN y el book_data (si el CLI ya hizo la elección)
    isbn = request.data.get('isbn')
    book_data = request.data.get('book_data')

    if not isbn:
        return Response(
            {"error": "Falta proveer el 'isbn' en el cuerpo de la petición."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Si viene del escáner web (que aún no tiene menú), usa la lista y toma el primero
    if not book_data:
        results = fetch_book_by_isbn(isbn)
        if not results:
            return Response(
                {"error": f"ISBN {isbn} no encontrado en los oráculos."},
                status=status.HTTP_404_NOT_FOUND
            )
        book_data = results[0]

    # Guarda los datos en la base de datos
    author_name = book_data.get('author') or "Desconocido"
    author, _ = Author.objects.get_or_create(name=author_name.strip())

    if Book.objects.filter(isbn=isbn).exists():
        return Response(
            {"message": f"¡El tomo con ISBN {isbn} ya está registrado en tu biblioteca!"},
            status=status.HTTP_200_OK
        )

    # Detección Automática Multi-Formato
    detected_format = 'NOVEL'  # Valor por defecto
    categories_str = " ".join(book_data.get('categories', [])).lower()
    title_str = book_data.get('title', '').lower()
    desc_str = book_data.get('description', '').lower()

    # Sistema de triage heurístico
    if 'manga' in categories_str or 'manga' in title_str:
        detected_format = 'MANGA'
    elif any(kw in categories_str for kw in ['comic', 'graphic novel', 'superhero']):
        detected_format = 'COMIC'
    elif any(kw in categories_str + desc_str for kw in ['anthology', 'short stories', 'cuentos', 'antología']):
        detected_format = 'ANTHOLOGY'

    book = Book.objects.create(
        isbn=isbn,
        title=book_data.get('title', 'Sin título').strip(),
        subtitle=book_data.get('subtitle', ''),
        author=author,
        publisher=book_data.get('publisher', ''),
        format_type=detected_format,
        is_read=False,
        page_count=book_data.get('page_count') or None,
        publish_date=book_data.get('publish_date', ''),
        cover_url=book_data.get('cover_url', ''),
        description=book_data.get('description', '')
    )

    for category in book_data.get('categories', []):
        clean_category = category.split('/')[-1].strip()
        genre, _ = Genre.objects.get_or_create(name=clean_category)
        book.genres.add(genre)

    # Responde con éxito
    return Response({
        "message": f"{detected_format} agregado a la biblioteca.",
        "book": {
            "id": book.id,
            "title": book.title,
            "author": book.author.name
        }
    }, status=status.HTTP_201_CREATED)


def scanner_view(request):
    """
    Renderiza la interfaz web del escáner para dispositivos móviles.
    """
    return render(request, 'catalog/scanner.html')


@api_view(['GET'])
def get_active_watchers(_request):
    """
    Endpoint para que Node.js pregunte: "¿Qué palabras clave debo vigilar hoy?"
    """
    watchers = Watcher.objects.filter(is_active=True)
    # Extrae solo los textos en una lista simple
    keywords = [w.keyword for w in watchers]

    return Response({"keywords": keywords}, status=status.HTTP_200_OK)


@api_view(['POST'])
def add_wishlist_item(request):
    """
    Endpoint para que Node.js envíe un libro recién encontrado al tablón.
    """
    title = request.data.get('title')
    buy_url = request.data.get('buy_url')

    if not title:
        return Response({"error": "El título es obligatorio"}, status=status.HTTP_400_BAD_REQUEST)

    # Evita que el scraper llene la base de datos con el mismo libro todos los días
    if WishlistItem.objects.filter(title=title, buy_url=buy_url).exists():
        return Response({"message": "El libro ya estaba en el tablón de deseos."}, status=status.HTTP_200_OK)

    # Crea el nuevo registro en el tablón
    item = WishlistItem.objects.create(
        title=title,
        author_string=request.data.get('author_string', ''),
        publisher=request.data.get('publisher', ''),
        price=request.data.get('price', ''),
        buy_url=buy_url,
        cover_url=request.data.get('cover_url', '')
    )

    return Response({
        "message": "Nuevo lanzamiento añadido al tablón de deseos.",
        "id": item.id
    }, status=status.HTTP_201_CREATED)

# --- ENDPOINTS PARA EL CLI EMANCIPADO ---


class BookFilter(django_filters.FilterSet):
    # lookup_expr='icontains' significa: ignorar mayúsculas y buscar si "contiene" el texto
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(
        field_name='author__name', lookup_expr='icontains')
    genre = django_filters.CharFilter(
        field_name='genres__name', lookup_expr='icontains')

    class Meta:
        model = Book
        fields = ['title', 'author', 'genre', 'format_type', 'is_read']


class BookViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD automáticas para los libros de la biblioteca."""
    queryset = Book.objects.all().order_by('-id')
    serializer_class = BookSerializer
    filterset_class = BookFilter


class WatcherViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD para las palabras clave vigiladas."""
    queryset = Watcher.objects.all().order_by('-created_at')
    serializer_class = WatcherSerializer


class WishlistItemViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD para el tablón de deseos."""
    queryset = WishlistItem.objects.filter(
        is_rejected=False).order_by('-date_found')
    serializer_class = WishlistItemSerializer


class FriendViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD para los amigos."""
    queryset = Friend.objects.all()
    serializer_class = FriendSerializer


class LoanViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD para los préstamos."""
    queryset = Loan.objects.all().order_by('-loan_date')
    serializer_class = LoanSerializer


@api_view(['POST'])
def log_pages(request):
    """Registra páginas leídas en el libro mayor (Ledger)"""
    pages = request.data.get('pages', 0)
    try:
        pages = int(pages)
        if pages <= 0:
            return Response({"error": "La cantidad de páginas debe ser mayor a 0"}, status=400)

        # Simplemente añade un evento al registro
        ReadingSession.objects.create(pages_read=pages)
        return Response({"message": f"{pages} páginas registradas exitosamente para hoy."}, status=201)
    except ValueError:
        return Response({"error": "Valor numérico inválido"}, status=400)


@api_view(['POST'])
def finish_book(request):
    """Registra un libro terminado y actualiza la estantería si es propio"""
    title = request.data.get('title')
    author_name = request.data.get('author_name', 'Desconocido')
    book_id = request.data.get('book_id')  # Puede venir vacío si es externo
    is_owned = request.data.get('is_owned', False)

    if not title:
        return Response({"error": "El título es obligatorio"}, status=400)

    # Crea el registro histórico
    AnnualRecord.objects.create(
        title=title,
        author_name=author_name,
        book_id=book_id,
        is_owned=is_owned
    )

    # Si el libro es mio, lo marca como leído en la base de datos central
    if book_id and is_owned:
        try:
            book = Book.objects.get(id=book_id)
            if not book.is_read:
                book.is_read = True
                book.save()
        except Book.DoesNotExist:
            pass

    return Response({"message": f"¡Felicidades! '{title}' añadido al registro anual."}, status=201)


@api_view(['GET'])
def tracker_stats(request):
    """Calcula las métricas dinámicas del mes actual para el Centro de Mando"""
    now = timezone.now()

    # Suma las páginas, filtrando solo por el año y mes actuales
    mes_actual_sessions = ReadingSession.objects.filter(
        date__year=now.year, date__month=now.month)
    paginas_mes = mes_actual_sessions.aggregate(
        Sum('pages_read'))['pages_read__sum'] or 0

    # Cuenta los libros terminados este mes
    libros_mes = AnnualRecord.objects.filter(
        date_finished__year=now.year, date_finished__month=now.month).count()

    return Response({
        "pages_this_month": paginas_mes,
        "books_this_month": libros_mes,
        "current_month": now.strftime("%B").capitalize(),  # Ej: "Marzo"
        "current_year": now.year
    }, status=200)


class AnnualRecordViewSet(viewsets.ModelViewSet):
    """Devuelve la lista de libros leídos (filtrada siempre por el año actual)"""
    serializer_class = AnnualRecordSerializer

    def get_queryset(self):
        now = timezone.now()
        # El reset anual solo devuelve los registros de este año
        return AnnualRecord.objects.filter(date_finished__year=now.year).order_by('-date_finished')


class DirectoryViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD para los directorios del Sistema de Archivos."""
    queryset = Directory.objects.all().order_by('name')
    serializer_class = DirectorySerializer

# Asegúrate de importar ScanInbox y ScanInboxSerializer


class ScanInboxViewSet(viewsets.ModelViewSet):
    """Provee operaciones CRUD para la bandeja de entrada del escáner móvil."""
    queryset = ScanInbox.objects.all().order_by('date_scanned')
    serializer_class = ScanInboxSerializer
