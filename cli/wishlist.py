import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box
from rich.panel import Panel

console = Console()
wishlist_app = typer.Typer(
    help="Manage your Wishlist and Scraper Watchers.", no_args_is_help=True)


@wishlist_app.command(name="list")
def list_wishlist():
    """Muestra los lanzamientos atrapados por el scraper."""
    from catalog.models import WishlistItem

    items = WishlistItem.objects.all().order_by('-date_found')

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
    table.add_column("Encontrado el", style="cyan")

    for item in items:
        date_str = item.date_found.strftime("%Y-%m-%d")
        table.add_row(str(item.id), item.title,
                      item.publisher or "-", item.price or "-", date_str)

    console.print(table)
    console.print(
        "\n[dim]Usa 'python -m cli.main wishlist details <ID>' para ver el link de compra.[/dim]\n")


@wishlist_app.command(name="watch")
def add_watcher():
    """Añade un autor, manga o palabra clave para que el scraper lo vigile."""
    from catalog.models import Watcher

    console.print(
        "\n[bold cyan]👁️  Añadir a la Lista de Vigilancia[/bold cyan]")
    console.print(
        "[dim]El scraper buscará estas palabras clave todos los días en las editoriales.[/dim]\n")

    keyword = Prompt.ask(
        "Palabra clave a vigilar (ej. 'Tatsuki Fujimoto' o 'Chainsaw Man')")

    if not keyword.strip():
        console.print("[red]❌ La palabra clave no puede estar vacía.[/red]")
        return

    watcher, created = Watcher.objects.get_or_create(keyword=keyword.strip())

    if created:
        console.print(
            f"\n[bold green]✅ ¡Ojos abiertos! El scraper ahora vigilará: '{watcher.keyword}'[/bold green]\n")
    else:
        # Si ya existía pero estaba desactivado, lo reactivamos
        if not watcher.is_active:
            watcher.is_active = True
            watcher.save()
            console.print(
                f"\n[bold green]✅ Vigilancia reactivada para: '{watcher.keyword}'[/bold green]\n")
        else:
            console.print(
                f"\n[yellow]⚠️ Ya estabas vigilando '{watcher.keyword}'.[/yellow]\n")


@wishlist_app.command(name="delete")
def delete_wishlist_item(item_id: int = typer.Argument(..., help="ID del lanzamiento a eliminar")):
    """Elimina un libro del tablón de deseos (si ya lo compraste o no te interesa)."""
    from catalog.models import WishlistItem

    try:
        item = WishlistItem.objects.get(id=item_id)
    except WishlistItem.DoesNotExist:
        console.print(
            "[bold red]❌ Libro no encontrado en el tablón.[/bold red]")
        return

    if Confirm.ask(f"¿Estás seguro de eliminar '{item.title}' de tu tablón?"):
        item.delete()
        console.print(
            "\n[bold green]✅ Eliminado correctamente del tablón.[/bold green]\n")
    else:
        console.print("\n[yellow]Operación cancelada.[/yellow]\n")
