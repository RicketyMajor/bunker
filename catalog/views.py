from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Book, Author, Genre, Watcher, WishlistItem
from django.shortcuts import render

# Importamos la herramienta que creamos para el CLI
from cli.api import fetch_book_by_isbn


@api_view(['POST'])
def scan_book(request):
    """
    Recibe un ISBN mediante POST, busca en OpenLibrary y lo guarda en la base de datos.
    """
    # 1. Extraemos el ISBN del JSON que envíe el teléfono
    isbn = request.data.get('isbn')

    if not isbn:
        return Response(
            {"error": "Please provide an 'isbn' in the request body."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2. Usamos nuestra función mágica de la Fase 6
    book_data = fetch_book_by_isbn(isbn)

    if not book_data:
        return Response(
            {"error": f"Book with ISBN {isbn} not found on OpenLibrary."},
            status=status.HTTP_404_NOT_FOUND
        )

    # 3. Guardamos los datos en la base de datos
    author, _ = Author.objects.get_or_create(name=book_data['author'].strip())

    # Prevenimos duplicados por si escaneas el mismo libro dos veces
    if Book.objects.filter(title=book_data['title'].strip(), author=author).exists():
        return Response(
            {"message": f"'{book_data['title']}' is already in your library!"},
            status=status.HTTP_200_OK
        )

    book = Book.objects.create(
        title=book_data['title'].strip(),
        subtitle=book_data['subtitle'],
        author=author,
        publisher=book_data['publisher'],
        format_type='NOVEL',  # Valor por defecto al escanear, luego lo puedes editar en el CLI
        is_read=False,       # Valor por defecto
        page_count=book_data['page_count'] or None,
        publish_date=book_data['publish_date'],
        cover_url=book_data['cover_url'],
        description=book_data['description']
    )

    for category in book_data['categories']:
        clean_category = category.split('/')[-1].strip()
        genre, _ = Genre.objects.get_or_create(name=clean_category)
        book.genres.add(genre)

    # 4. Respondemos con éxito al teléfono
    return Response({
        "message": "✅ Book successfully added to library!",
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

# Arriba del todo, asegúrate de añadir Watcher y WishlistItem a tu importación de models:
# from .models import Book, Author, Genre, Watcher, WishlistItem


@api_view(['GET'])
def get_active_watchers(_request):
    """
    Endpoint para que Node.js pregunte: "¿Qué palabras clave debo vigilar hoy?"
    """
    watchers = Watcher.objects.filter(is_active=True)
    # Extraemos solo los textos en una lista simple
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

    # Evitamos que el scraper llene la base de datos con el mismo libro todos los días
    if WishlistItem.objects.filter(title=title, buy_url=buy_url).exists():
        return Response({"message": "El libro ya estaba en el tablón de deseos."}, status=status.HTTP_200_OK)

    # Creamos el nuevo registro en el tablón
    item = WishlistItem.objects.create(
        title=title,
        author_string=request.data.get('author_string', ''),
        publisher=request.data.get('publisher', ''),
        price=request.data.get('price', ''),
        buy_url=buy_url,
        cover_url=request.data.get('cover_url', '')
    )

    return Response({
        "message": "✅ Nuevo lanzamiento añadido al tablón de deseos.",
        "id": item.id
    }, status=status.HTTP_201_CREATED)
