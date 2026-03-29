import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich import box
from rich.align import Align
from rich.prompt import Prompt, Confirm
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

console = Console()
dir_app = typer.Typer(
    help="Gestiona los directorios y colecciones maestras.", no_args_is_help=True)

API_DIR = "http://localhost:8000/api/books/directories/"
API_LIBRARY = "http://localhost:8000/api/books/library/"


@dir_app.command("create")
def create_dir():
    """Crea una nueva carpeta maestra con un color personalizado."""
    console.print("\n[bold cyan]📁 CREAR NUEVO DIRECTORIO[/bold cyan]")
    name = Prompt.ask("Nombre de la saga o colección (ej. Green Lantern)")

    console.print("\n[dim]Paleta de renderizado en terminal:[/dim]")
    colors = ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    for c in colors:
        console.print(f"  [{c}]■ {c.capitalize()}[/{c}]")

    color = Prompt.ask("\nElige un color para este universo",
                       choices=colors, default="cyan")

    try:
        resp = httpx.post(
            API_DIR, json={"name": name.strip(), "color_hex": color})
        if resp.status_code == 201:
            console.print(
                f"\n[bold green]Directorio '{name}' creado y montado exitosamente.[/bold green]\n")
        else:
            console.print(f"\n[bold red]Error: {resp.text}[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]Error de red: {e}[/bold red]")


@dir_app.command("list")
def list_dirs():
    """Muestra el sistema de archivos actual y su peso (cantidad de libros)."""
    try:
        resp = httpx.get(API_DIR)
        resp.raise_for_status()
        dirs = resp.json()

        # Hacem un fetch a la biblioteca para calcular el peso de cada directorio
        resp_books = httpx.get(API_LIBRARY)
        books = resp_books.json()

    except Exception as e:
        console.print(f"[bold red]❌ Error de red: {e}[/bold red]")
        return

    if not dirs:
        console.print(
            "\n[yellow]No hay directorios creados aún. Usa 'dir create' para empezar.[/yellow]\n")
        return

    table = Table(
        title="📁 [bold cyan]SISTEMA DE ARCHIVOS[/bold cyan] 📁", box=box.SIMPLE_HEAVY)
    table.add_column("ID Virtual", style="dim")
    table.add_column("Directorio")
    table.add_column("Volumen (Obras)", justify="center")

    for d in dirs:
        d_id = d.get('id')
        color = d.get('color_hex', 'cyan')
        name = d.get('name', 'Unknown')

        # Calcula cuántos libros apuntan a esta llave foránea
        count = sum(1 for b in books if b.get('directory') == d_id)

        table.add_row(
            f"[D-{d_id}]",
            f"[{color}]■ {name}[/{color}]",
            str(count)
        )

    console.print()
    console.print(Align.center(table))
    console.print()


@dir_app.command("add")
def add_to_dir(
    dir_id: int = typer.Argument(...,
                                 help="ID numérico del directorio (ej. 1)"),
    book_ids: str = typer.Argument(...,
                                   help="IDs de los libros separados por coma (ej. 14,15,16)")
):
    """Inyección Masiva: Mueve múltiples libros dentro de un directorio de golpe."""
    console.print(
        f"\n[dim]Iniciando transferencia al directorio D-{dir_id}...[/dim]")

    ids = [i.strip() for i in book_ids.split(",") if i.strip().isdigit()]
    if not ids:
        console.print(
            "[bold red]No se proporcionaron IDs numéricos válidos.[/bold red]")
        return

    success_count = 0
    for b_id in ids:
        try:
            # Usa PATCH para actualizar únicamente la llave foránea 'directory'
            resp = httpx.patch(f"{API_LIBRARY}{b_id}/",
                               json={"directory": dir_id})
            if resp.status_code == 200:
                success_count += 1
                console.print(
                    f"  [green]✔ Tomo #{b_id} transferido exitosamente.[/green]")
            else:
                console.print(
                    f"  [red]Falló el tomo #{b_id}: {resp.text}[/red]")
        except Exception as e:
            console.print(
                f"  [red]Error de red con el tomo #{b_id}: {e}[/red]")

    console.print(
        f"\n[bold magenta]Operación finalizada. {success_count} tomos anidados.[/bold magenta]\n")


@dir_app.command("delete")
def delete_dir(dir_id: int = typer.Argument(..., help="ID numérico del directorio a borrar")):
    """Elimina un directorio. Los libros en su interior NO se borrarán (quedarán huérfanos)."""
    if not Confirm.ask(f"¿Eliminar el directorio D-{dir_id}? (Sus libros quedarán intactos en la raíz)"):
        console.print("\n[yellow]Operación cancelada.[/yellow]\n")
        return

    try:
        resp = httpx.delete(f"{API_DIR}{dir_id}/")
        if resp.status_code == 204:
            console.print(
                f"\n[bold green]Directorio D-{dir_id} desintegrado exitosamente.[/bold green]\n")
        else:
            console.print(
                f"\n[bold red]Error al eliminar. ¿Existe el ID {dir_id}?[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]Error de red: {e}[/bold red]")


@dir_app.command("edit")
def edit_dir(dir_id: int = typer.Argument(..., help="ID numérico del directorio")):
    """Modifica el nombre o color de un directorio existente."""
    try:
        resp = httpx.get(f"{API_DIR}{dir_id}/")
        if resp.status_code == 404:
            console.print(
                f"[bold red]Directorio D-{dir_id} no encontrado.[/bold red]")
            return

        directory = resp.json()
        console.print(
            f"\n[bold cyan]Editando Directorio: {directory['name']}[/bold cyan]")

        new_name = Prompt.ask("Nuevo nombre", default=directory['name'])

        colors = ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]
        color_completer = WordCompleter(colors, ignore_case=True)
        console.print(
            "[dim]Colores: red, green, yellow, blue, magenta, cyan, white[/dim]")
        new_color = prompt("Nuevo color (TAB para opciones): ",
                           completer=color_completer).strip().lower()

        if new_color not in colors:
            new_color = directory.get('color_hex', 'cyan')

        payload = {"name": new_name, "color_hex": new_color}
        update_resp = httpx.patch(f"{API_DIR}{dir_id}/", json=payload)

        if update_resp.status_code == 200:
            console.print(
                "\n[bold green]Directorio actualizado magistralmente.[/bold green]\n")
        else:
            console.print(
                f"\n[bold red]Error al actualizar: {update_resp.text}[/bold red]\n")

    except Exception as e:
        console.print(f"[bold red]Error de red: {e}[/bold red]")


@dir_app.command("view")
def view_dir(dir_id: int = typer.Argument(..., help="ID numérico del directorio a explorar")):
    """Abre el directorio y muestra los libros anidados en su interior."""
    try:
        # Obtiene la metadata del directorio
        d_resp = httpx.get(f"{API_DIR}{dir_id}/")
        if d_resp.status_code == 404:
            console.print(
                f"[bold red]Directorio D-{dir_id} no encontrado.[/bold red]")
            return
        directory = d_resp.json()

        # Obtiene todos los libros y filtramos localmente
        b_resp = httpx.get(API_LIBRARY)
        b_resp.raise_for_status()
        all_books = b_resp.json()

        dir_books = [b for b in all_books if b.get('directory') == dir_id]

    except Exception as e:
        console.print(f"[bold red]❌ Error de red: {e}[/bold red]")
        return

    color = directory.get('color_hex', 'cyan')
    name = directory['name']

    if not dir_books:
        console.print(
            f"\n[{color}]■ Directorio '{name}' está vacío.[/_{color}]\n")
        return

   # Renderiza la tabla con todas las columnas estándar
    table = Table(title=f"[{color}]■ CONTENIDO DE: {name.upper()}[/{color}]",
                  box=box.SIMPLE_HEAVY, header_style=f"bold {color}", border_style=color)
    table.add_column("ID", justify="right", style="dim", no_wrap=True)
    table.add_column("Título", style="bold white")
    table.add_column("Autor", style="yellow")
    table.add_column("Formato", style="magenta")
    table.add_column("Editorial", style="green")
    table.add_column("Leído", justify="center")
    table.add_column("Ubicación", justify="center")

    for book in dir_books:
        status = "[green]✔[/green]" if book.get('is_read') else "[red]✘[/red]"
        ubicacion = "[bold red]⇋ Prestado[/bold red]" if book.get(
            'is_loaned') else "[bold green]❖ Estantería[/bold green]"

        title_display = book.get('title', 'Sin título').upper()
        details = book.get('details', {})
        fmt = book.get('format_type', 'NOVEL')

        if fmt in ["MANGA", "COMIC"] and details:
            tomos_raw = details.get('tomos_obtenidos', '')
            if tomos_raw:
                cantidad = len(
                    [t for t in str(tomos_raw).split(',') if t.strip()])
                title_display += f"\n  [dim]↳ {cantidad} tomos en colección[/dim]"
        elif fmt == "ANTHOLOGY" and details:
            cuentos = details.get('lista_cuentos', [])
            if cuentos:
                title_display += f"\n  [dim]↳ {len(cuentos)} cuentos incluidos[/dim]"

        table.add_row(
            str(book.get('id')),
            title_display,
            book.get('author_name', 'Desconocido'),
            fmt,
            book.get('publisher') or '-',
            status,
            ubicacion
        )

    console.print()
    console.print(Align.center(table))
    console.print()
