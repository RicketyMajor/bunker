import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()
book_app = typer.Typer(
    help="Manage your library books, comics, and mangas.", no_args_is_help=True)

API_LIBRARY = "http://localhost:8000/api/books/library/"
API_SCAN = "http://localhost:8000/api/books/scan/"


@book_app.command(name="list")
def list_books():
    """Muestra todos los libros de tu biblioteca consumiendo la API REST."""
    try:
        response = httpx.get(API_LIBRARY)
        response.raise_for_status()
        books = response.json()
    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")
        return

    if not books:
        console.print("[yellow]Tu biblioteca está vacía.[/yellow]")
        return

    table = Table(
        title="📚 [bold blue]Mi Biblioteca[/bold blue]", box=box.ROUNDED)
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Título", style="magenta")
    table.add_column("Autor", style="green")
    table.add_column("Formato", style="yellow")
    table.add_column("Leído", justify="center")

    for book in books:
        status = "✅" if book.get('is_read') else "❌"
        table.add_row(
            str(book.get('id')),
            book.get('title', 'Sin título'),
            book.get('author_name', 'Desconocido'),
            book.get('format_type', '-'),
            status
        )

    console.print(table)


@book_app.command(name="add")
def add_book(isbn: str):
    """Añade un libro usando el ISBN consumiendo la API remota."""
    console.print(f"Buscando y procesando el ISBN {isbn} en el servidor...")
    try:
        response = httpx.post(API_SCAN, json={"isbn": isbn})
        data = response.json()

        if response.status_code == 201:
            console.print(
                f"[bold green]{data.get('message', 'Añadido')}[/bold green] (ID: {data['book']['id']})")
        elif response.status_code == 200:
            console.print(
                f"[yellow]{data.get('message', 'Ya existe')}[/yellow]")
        else:
            console.print(
                f"[bold red]❌ Error: {data.get('error', 'Desconocido')}[/bold red]")
    except Exception as e:
        console.print(
            f"[bold red]❌ Error de conexión al servidor: {e}[/bold red]")


@book_app.command(name="delete")
def delete_book(book_id: int):
    """Elimina un libro de la biblioteca mediante la API."""
    try:
        response = httpx.delete(f"{API_LIBRARY}{book_id}/")
        if response.status_code == 204:
            console.print(
                f"[bold green]✅ Libro #{book_id} eliminado correctamente del servidor.[/bold green]")
        else:
            console.print(
                f"[bold red]❌ No se pudo eliminar. ¿Existe el ID {book_id}?[/bold red]")
    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")
