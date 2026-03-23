import typer
import httpx
from rich.console import Console
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich.prompt import Prompt, Confirm

console = Console()
tracker_app = typer.Typer(
    help="Registra tu progreso de lectura diario y anual.", no_args_is_help=True)

# Asegúrate de que estas rutas coincidan con cómo configuraste tu urls.py
API_LIBRARY = "http://localhost:8000/api/books/library/"
API_TRACKER_PAGES = "http://localhost:8000/api/books/tracker/pages/"
API_TRACKER_FINISH = "http://localhost:8000/api/books/tracker/finish/"


@tracker_app.command(name="log")
def log_pages(pages: int = typer.Argument(..., help="Cantidad de páginas leídas hoy")):
    """Suma páginas a tu registro diario (Ledger)."""
    try:
        response = httpx.post(API_TRACKER_PAGES, json={"pages": pages})
        data = response.json()

        if response.status_code == 201:
            console.print(
                f"\n[bold green]{data.get('message')}[/bold green]\n")
        else:
            console.print(
                f"\n[bold red]❌ Error: {data.get('error', 'Desconocido')}[/bold red]\n")
    except Exception as e:
        console.print(
            f"[bold red]❌ Error de conexión al servidor: {e}[/bold red]")


@tracker_app.command(name="finish")
def finish_book():
    """Asistente inteligente para registrar un libro terminado en tu historial anual."""
    console.print(
        "\n[bold cyan]🏆 REGISTRO DE VICTORIA LITERARIA 🏆[/bold cyan]")

    # 1. Obtenemos la base de datos de libros actual para el autocompletado
    try:
        resp = httpx.get(API_LIBRARY, timeout=5.0)
        resp.raise_for_status()
        all_books = resp.json()
    except Exception as e:
        console.print(
            f"[bold red]❌ No se pudo conectar a la base de datos: {e}[/bold red]")
        return

    # Extraemos todos los títulos únicos para el autocompletador
    titles = list(set([b.get('title') for b in all_books if b.get('title')]))
    title_completer = WordCompleter(
        titles, ignore_case=True, match_middle=True)

    # 2. Prompt interactivo para el Título
    console.print(
        "[dim]Escribe el título (usa TAB para autocompletar si está en tu biblioteca):[/dim]")
    title_input = prompt("Título: ", completer=title_completer).strip()

    if not title_input:
        console.print("[yellow]⚠️ El título no puede estar vacío.[/yellow]")
        return

    # 3. Buscamos si el título ingresado coincide con nuestra base de datos
    matching_books = [b for b in all_books if b.get(
        'title', '').lower() == title_input.lower()]

    # Preparamos el autocompletador de autores dependiendo de si hubo match
    authors = []
    book_id = None
    is_owned = False

    if matching_books:
        # ¡Hubo Match! Extraemos los autores específicos de este libro
        authors = list(set([b.get('author_name')
                       for b in matching_books if b.get('author_name')]))
        console.print(
            "[dim green]✓ Libro detectado en tu inventario.[/dim green]")
        book_id = matching_books[0].get('id')
        is_owned = True  # Asumimos que es propio porque está en la DB
    else:
        # No hubo match, cargamos todos los autores de la DB por si acaso
        authors = list(set([b.get('author_name')
                       for b in all_books if b.get('author_name')]))
        console.print(
            "[dim yellow]ℹ️ Libro externo/nuevo detectado.[/dim yellow]")

    author_completer = WordCompleter(
        authors, ignore_case=True, match_middle=True)

    # 4. Prompt interactivo para el Autor
    console.print("[dim]Escribe el autor (usa TAB para autocompletar):[/dim]")
    author_input = prompt("Autor: ", completer=author_completer).strip()

    # Si es un libro externo, preguntamos explícitamente si se lo prestaron
    if not matching_books:
        is_owned = Confirm.ask(
            "¿Este libro es de tu propiedad? (Responde 'y' si es tuyo, 'n' si te lo prestaron)", default=False)

    # 5. Enviamos el evento al Backend
    payload = {
        "title": title_input,
        "author_name": author_input or "Desconocido",
        "book_id": book_id,
        "is_owned": is_owned
    }

    try:
        response = httpx.post(API_TRACKER_FINISH, json=payload)
        data = response.json()

        if response.status_code == 201:
            console.print(
                f"\n[bold magenta]✨ {data.get('message')}[/bold magenta]\n")
        else:
            console.print(
                f"\n[bold red]❌ Error: {data.get('error', 'Desconocido')}[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]❌ Error al registrar: {e}[/bold red]")
