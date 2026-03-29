import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm
from datetime import datetime
from rich.align import Align

console = Console()
loan_app = typer.Typer(
    help="Gestiona los préstamos de tus libros a amigos.", no_args_is_help=True)

API_LIBRARY = "http://localhost:8000/api/books/library/"
API_FRIENDS = "http://localhost:8000/api/books/friends/"
API_LOANS = "http://localhost:8000/api/books/loans/"


@loan_app.command(name="lend")
def lend_book():
    """Presta un libro de tu biblioteca a un amigo."""
    try:
        # Obtener todos los libros y filtrar solo los que están en casa
        response = httpx.get(API_LIBRARY)
        books = response.json()
        available_books = [b for b in books if not b.get('is_loaned')]

        if not available_books:
            console.print(
                "[yellow]No tienes libros disponibles para prestar en este momento.[/yellow]")
            return

        # Mostrar opciones
        console.print()
        table = Table(title="[bold cyan]INVENTARIO DISPONIBLE[/bold cyan]",
                      box=box.SIMPLE_HEAVY, header_style="bold cyan", border_style="cyan")
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Título", style="bold white")
        table.add_column("Autor", style="green")

        for b in available_books:
            table.add_row(str(b['id']), b['title'].upper(),
                          b.get('author_name', ''))

        console.print(Align.center(table))
        console.print()

        # Recopilar datos
        book_id = Prompt.ask(
            "\n[bold yellow]Ingresa el ID del libro que vas a prestar[/bold yellow]")
        friend_name = Prompt.ask(
            "[bold yellow]¿A quién se lo vas a prestar?[/bold yellow]")

        if not Confirm.ask(f"\n¿Confirmas que entregarás este libro a {friend_name}?"):
            console.print(
                "\n[yellow]Préstamo cancelado. El libro sigue en tu estantería.[/yellow]\n")
            return

        # Lógica de Amigos
        friends_resp = httpx.get(API_FRIENDS)
        friend_id = None
        for f in friends_resp.json():
            if f.get('name', '').lower() == friend_name.lower():
                friend_id = f['id']
                break

        if not friend_id:
            f_post = httpx.post(API_FRIENDS, json={
                                "name": friend_name.strip()})
            if f_post.status_code == 201:
                friend_id = f_post.json()['id']
            else:
                console.print(
                    f"[red]Error registrando al amigo: {f_post.text}[/red]")
                return

        # Registrar el Préstamo
        loan_payload = {
            "book": int(book_id),
            "friend": friend_id,
            "loan_date": datetime.now().strftime("%Y-%m-%d")
        }
        loan_post = httpx.post(API_LOANS, json=loan_payload)

        if loan_post.status_code == 201:
            # 6. Actualizar el estado del libro (Transacción distribuida simulada)
            httpx.patch(f"{API_LIBRARY}{book_id}/", json={"is_loaned": True})
            console.print(
                f"\n[bold green]El libro se ha registrado como prestado a {friend_name} correctamente.[/bold green]\n")
        else:
            console.print(
                f"[red]Error creando préstamo: {loan_post.text}[/red]")

    except Exception as e:
        console.print(f"[bold red]Error de conexión: {e}[/bold red]")


@loan_app.command(name="list")
def list_loans():
    """Muestra la lista de libros que tienes prestados actualmente."""
    try:
        resp = httpx.get(API_LOANS)
        loans = resp.json()

        if not loans:
            console.print(
                "\n[yellow]No tienes ningún libro prestado actualmente. Tienes todos tus libros en casa.[/yellow]\n")
            return

        console.print()
        table = Table(
            title="⇋ [bold magenta]REGISTRO DE PRÉSTAMOS[/bold magenta] ⇋",
            box=box.SIMPLE_HEAVY,
            header_style="bold magenta",
            border_style="magenta"
        )
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Libro", style="bold white")
        table.add_column("Amigo", style="bold green")
        table.add_column("Fecha Préstamo", style="yellow")

        for l in loans:
            table.add_row(
                str(l['id']),
                l.get('book_title', f"Libro #{l['book']}").upper(),
                l.get('friend_name', f"Amigo #{l['friend']}"),
                l.get('loan_date', '')
            )
        console.print(Align.center(table))
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error de conexión: {e}[/bold red]")


@loan_app.command(name="return")
def return_book(loan_id: int = typer.Argument(..., help="ID del préstamo a devolver")):
    """Devuelve un libro prestado a tu biblioteca física."""

    if not Confirm.ask(f"¿Confirmas que el préstamo #{loan_id} ya está físicamente de vuelta en tu estantería?"):
        console.print("\n[yellow]Devolución cancelada.[/yellow]\n")
        return

    try:
        # Obtiene el préstamo para saber qué libro se debe devolver
        resp = httpx.get(f"{API_LOANS}{loan_id}/")
        if resp.status_code == 404:
            console.print(
                f"[bold red]Préstamo #{loan_id} no encontrado.[/bold red]")
            return

        loan = resp.json()
        book_id = loan['book']

        # Elimina el registro del préstamo (Devolución)
        delete_resp = httpx.delete(f"{API_LOANS}{loan_id}/")

        if delete_resp.status_code == 204:
            # Actualiza el libro a "En Biblioteca"
            httpx.patch(f"{API_LIBRARY}{book_id}/", json={"is_loaned": False})
            console.print(
                f"\n[bold green]¡Libro devuelto! Vuelve a estar disponible en tu estantería física.[/bold green]\n")
        else:
            console.print(f"[red]Error procesando la devolución.[/red]")

    except Exception as e:
        console.print(f"[bold red]Error de conexión: {e}[/bold red]")
