from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Book, Author, Genre

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
