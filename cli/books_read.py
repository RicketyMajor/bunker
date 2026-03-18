import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()
app = typer.Typer(help="Read operations for your library.",
                  no_args_is_help=True)

# La URL de tu servidor en Docker
API_URL = "http://localhost:8000/api/books/library/"


@app.command(name="list")
def list_books():
    """Muestra todos los libros de tu biblioteca consumiendo la API REST."""
    try:
        # Hacemos la petición GET al servidor
        response = httpx.get(API_URL)
        response.raise_for_status()  # Lanza un error si el servidor no responde 200 OK
        books = response.json()     # Convertimos el JSON a una lista de diccionarios de Python
    except httpx.ConnectError:
        console.print(
            "[bold red]❌ Error de conexión: ¿Está encendido el servidor Docker?[/bold red]")
        return
    except Exception as e:
        console.print(f"[bold red]❌ Error inesperado: {e}[/bold red]")
        return

    if not books:
        console.print("[yellow]Tu biblioteca está vacía.[/yellow]")
        return

    table = Table(
        title="📚 [bold blue]Mi Biblioteca (Modo Cliente API)[/bold blue]", box=box.ROUNDED)
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Título", style="magenta")
    table.add_column("Autor", style="green")
    table.add_column("Formato", style="yellow")
    table.add_column("Leído", justify="center")

    # Ahora iteramos sobre diccionarios, no sobre objetos de Django
    for book in books:
        status = "✅" if book['is_read'] else "❌"
        # Usamos .get() por seguridad en caso de que algún campo venga nulo
        table.add_row(
            str(book.get('id')),
            book.get('title', 'Sin título'),
            book.get('author_name', 'Desconocido'),
            book.get('format_type', '-'),
            status
        )

    console.print(table)
