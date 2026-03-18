import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()
wishlist_app = typer.Typer(
    help="Manage your Wishlist and Scraper Watchers.", no_args_is_help=True)

# Las URLs de nuestra nueva API automática
API_WISHLIST = "http://localhost:8000/api/books/wishlist-crud/"
API_WATCHERS = "http://localhost:8000/api/books/watchers-crud/"


@wishlist_app.command(name="list")
def list_wishlist():
    """Muestra los lanzamientos atrapados por el scraper consumiendo la API."""
    try:
        response = httpx.get(API_WISHLIST)
        response.raise_for_status()
        items = response.json()
    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")
        return

    if not items:
        console.print(
            "[bold yellow]📭 Tu tablón de deseos está vacío. ¡El scraper aún no ha encontrado nada![/bold yellow]")
        return

    table = Table(
        title="✨ [bold cyan]Tablón de Deseos & Lanzamientos[/bold cyan]",
        box=box.ROUNDED,
        header_style="bold magenta"
    )

    table.add_column("ID", justify="right", style="dim")
    table.add_column("Título", style="bold white")
    table.add_column("Editorial", style="yellow")
    table.add_column("Precio", style="green")
    table.add_column("Fecha", style="cyan")

    for item in items:
        # Acortamos la fecha que viene del JSON (ej. "2026-03-17T12:00:00Z" -> "2026-03-17")
        date_str = item.get('date_found', '')[:10]
        table.add_row(
            str(item.get('id')),
            item.get('title'),
            item.get('publisher') or "-",
            item.get('price') or "-",
            date_str
        )

    console.print(table)


@wishlist_app.command(name="watch")
def add_watcher():
    """Añade un autor, manga o palabra clave mediante un POST a la API."""
    console.print(
        "\n[bold cyan]👁️  Añadir a la Lista de Vigilancia[/bold cyan]")
    keyword = Prompt.ask("Palabra clave a vigilar (ej. 'Tatsuki Fujimoto')")

    if not keyword.strip():
        console.print("[red]❌ La palabra clave no puede estar vacía.[/red]")
        return

    try:
        # Enviamos un POST al servidor para crear la palabra clave
        response = httpx.post(API_WATCHERS, json={
                              "keyword": keyword.strip(), "is_active": True})

        if response.status_code == 201:
            console.print(
                f"\n[bold green]✅ ¡Ojos abiertos! El scraper ahora vigilará: '{keyword}'[/bold green]\n")
        elif response.status_code == 400:
            console.print(
                f"\n[yellow]⚠️ Esa palabra clave ya está en tu lista de vigilancia.[/yellow]\n")
        else:
            console.print(f"[red]❌ Error del servidor: {response.text}[/red]")

    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")


@wishlist_app.command(name="delete")
def delete_wishlist_item(item_id: int = typer.Argument(..., help="ID del lanzamiento a eliminar")):
    """Elimina un libro del tablón de deseos mediante un DELETE a la API."""
    if Confirm.ask(f"¿Estás seguro de eliminar el ítem #{item_id} de tu tablón?"):
        try:
            # Enviamos la petición DELETE a la URL específica del ítem (ej. .../wishlist-crud/5/)
            response = httpx.delete(f"{API_WISHLIST}{item_id}/")
            # 204 significa "No Content" (Borrado exitoso en DRF)
            if response.status_code == 204:
                console.print(
                    "\n[bold green]✅ Eliminado correctamente del tablón.[/bold green]\n")
            else:
                console.print(
                    f"[red]❌ No se pudo eliminar. ¿Estás seguro de que el ID {item_id} existe?[/red]")
        except Exception as e:
            console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")
    else:
        console.print("\n[yellow]Operación cancelada.[/yellow]\n")
