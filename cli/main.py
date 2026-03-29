import re
import subprocess
import typer
import click
import subprocess
import time
import httpx
import sys
import pyfiglet
import socket
import sys
import platform
import qrcode
from prompt_toolkit.formatted_text import HTML
from click_repl import repl
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
from rich.prompt import Prompt
from rich.table import Table
from rich import box
from cli.books import book_app
from cli.loans import loan_app
from cli.wishlist import wishlist_app
from cli.tracker import tracker_app
from cli.directories import dir_app


console = Console()
app = typer.Typer(
    help="CLI tool to manage my personal library.", no_args_is_help=True)

app.add_typer(book_app, name="book")
app.add_typer(loan_app, name="loan")
app.add_typer(wishlist_app, name="wishlist")
app.add_typer(tracker_app, name="tracker")
app.add_typer(dir_app, name="dir")

# Esta variable recordará si ya revisó la red
_infrastructure_checked = False


def ensure_infrastructure_up():
    """El Orquestador Invisible: Verifica la red y levanta Docker si está caído."""
    global _infrastructure_checked

    # Si ya comprobó que todo está en orden en esta sesión, salta esta función de inmediato
    if _infrastructure_checked:
        return

    try:
        # Sube el timeout a 2.0s para evitar "falsos positivos" de caída
        httpx.get("http://localhost:8000/api/books/library/", timeout=2.0)
        _infrastructure_checked = True  # Sellamos la verificación exitosa

    except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
        console.print(
            "\n[bold yellow]Infraestructura dormida o inestable. Encendiendo servidores...[/bold yellow]")
        project_dir = Path(__file__).resolve().parent.parent
        try:
            subprocess.run(["docker-compose", "up", "-d"], cwd=project_dir,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            console.print(
                "[bold red]Comando 'docker-compose' no encontrado en el sistema.[/bold red]")
            return

        console.print(
            "[cyan]Sincronizando bases de datos distribuidas[/cyan]", end="")
        for _ in range(20):
            try:
                httpx.get(
                    "http://localhost:8000/api/books/library/", timeout=2.0)
                console.print(
                    "\n[bold green]¡Sistemas en línea![/bold green]\n")
                _infrastructure_checked = True  # Sellamos la verificación tras encender
                return

            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
                console.print(".", end="", style="cyan")
                sys.stdout.flush()
                time.sleep(1)

        console.print(
            "\n[bold red]El servidor tardó demasiado en responder.[/bold red]")

        _infrastructure_checked = True


@app.callback()
def main_callback():
    """Hook automático para asegurar la infraestructura."""
    ensure_infrastructure_up()


@app.command(name="exit")
def exit_shell():
    """Sale del entorno inmersivo."""
    console.print(
        "\n[bold magenta]Cerrando la biblioteca... ¡Hasta tu próxima lectura![/bold magenta]\n")
    raise EOFError


def get_local_ip():
    """Descubre la IPv4 local, con soporte especial para atravesar el NAT de WSL2."""

    # 1. Detectar si estamos atrapados dentro de WSL
    release_info = platform.uname().release.lower()
    in_wsl = "microsoft" in release_info or "wsl" in release_info

    if in_wsl:
        try:
            # Ejecuta PowerShell desde Linux para extraer la IPv4 del adaptador Wi-Fi o Ethernet del host Windows
            cmd = 'powershell.exe -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match \'Wi-Fi|Ethernet\' } | Select-Object -First 1).IPAddress"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=2)
            ip = result.stdout.strip()
            if ip:
                return ip
        except Exception:
            pass  # Si falla, cae silenciosamente al método estándar

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_dashboard_stats():
    """Consulta la API para obtener métricas rápidas de la biblioteca."""
    stats = {"books": 0, "loans": 0, "wishlist": 0}
    try:
        books_resp = httpx.get(
            "http://localhost:8000/api/books/library/", timeout=1.0)
        if books_resp.status_code == 200:
            stats["books"] = len(books_resp.json())

        loans_resp = httpx.get(
            "http://localhost:8000/api/books/loans/", timeout=1.0)
        if loans_resp.status_code == 200:
            stats["loans"] = len(loans_resp.json())

        wish_resp = httpx.get(
            "http://localhost:8000/api/books/wishlist-crud/", timeout=1.0)
        if wish_resp.status_code == 200:
            stats["wishlist"] = len(wish_resp.json())

        tracker_resp = httpx.get(
            "http://localhost:8000/api/books/tracker/stats/", timeout=1.0)
        if tracker_resp.status_code == 200:
            stats["tracker"] = tracker_resp.json()
    except Exception:
        pass
    return stats


def show_welcome_screen():
    """Genera la cabecera visual y el dashboard dinámico de la aplicación."""

    ascii_art = pyfiglet.figlet_format("LIBRARY", font="slant")
    ascii_text = Text(ascii_art, style="bold cyan")

    # Obtiene los datos dinámicos
    stats = get_dashboard_stats()

    tracker = stats.get("tracker", {})
    pages_month = tracker.get("pages_this_month", 0)
    books_month = tracker.get("books_this_month", 0)
    month_name = tracker.get("current_month", "Mes actual")

    # Panel de Inventario
    inv_text = f"""[cyan]▤[/cyan] Colección: [bold green]{stats.get('books', 0)}[/bold green] tomos
[yellow]⇋[/yellow] Préstamos: [bold yellow]{stats.get('loans', 0)}[/bold yellow] activos
[magenta]◈[/magenta] Wishlist:  [bold magenta]{stats.get('wishlist', 0)}[/bold magenta] en radar
[green]★[/green] Bandeja: [bold cyan]book inbox[/bold cyan]"""

    # Panel de Tracker
    track_text = f"""[cyan]∑[/cyan] Páginas leídas: [bold cyan]{pages_month}[/bold cyan]
[yellow]★[/yellow] Obras terminadas: [bold yellow]{books_month}[/bold yellow]
[dim]Progreso de {month_name}[/dim]"""

    # Panel de Comandos Rápidos
    cmd_text = """[cyan]⌘[/cyan] Escanear QR: [bold cyan]scanner[/bold cyan]
[green]▤[/green] Explorar Raíz: [bold cyan]ls[/bold cyan]
[green]✎[/green] Anotar páginas: [bold cyan]tracker log <num>[/bold cyan]
[magenta]✔[/magenta] Registrar obra: [bold cyan]tracker finish[/bold cyan]"""

    # Panel de Módulos (Con atajos extra)
    mod_text = """[green]▪[/green] [bold]book[/bold]    (list, add, details...)
[green]▪[/green] [bold]dir[/bold]     (create, list, add)
[green]▪[/green] [bold]loan[/bold]    (list, lend, return)
[green]▪[/green] [bold]tracker[/bold] (log, finish, annual)"""

    # Ensambla los 4 paneles reduciendo drásticamente el padding vertical
    p_inv = Panel(
        inv_text, title="[bold cyan]Sensores[/bold cyan]", border_style="cyan", padding=(0, 2))
    p_trk = Panel(
        track_text, title="[bold green]Hábitos[/bold green]", border_style="green", padding=(0, 2))
    p_cmd = Panel(cmd_text, title="[bold yellow]Atajos Rápidos[/bold yellow]",
                  border_style="yellow", padding=(0, 2))
    p_mod = Panel(mod_text, title="[bold magenta]Módulos[/bold magenta]",
                  border_style="magenta", padding=(0, 2))

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)  # Columna Izquierda
    grid.add_column(ratio=1)  # Columna Derecha

    # Apila en formato 2x2
    grid.add_row(p_inv, p_trk)
    grid.add_row(p_cmd, p_mod)

    console.print(Align.center(ascii_text))
    console.print(grid)
    console.print(
        "[dim]Atajos: \\[Tab] Autocompletar | \\[exit] Cerrar sesión[/dim]", justify="center")
    console.print()


@app.command(name="scanner")
def show_scanner_qr():
    """Genera un Código QR y un túnel HTTPS efímero para el escáner móvil."""
    console.print("\n[bold cyan]INICIANDO ESCÁNER MÓVIL SEGURO[/bold cyan]")
    console.print(
        "[cyan]Negociando túnel cifrado (SSH Reverse Tunnel)...[/cyan]")

    tunnel_process = None
    url = ""

    try:
        # Se define la ruta exacta de nuestra llave dedicada
        key_path = str(Path.home() / ".ssh" / "library_cli_key")

        tunnel_process = subprocess.Popen(
            # Heartbeat cada 60 segundos para evitar que el túnel muera por inactividad
            ["ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no", "-o",
                "ServerAliveInterval=60", "-R", "80:localhost:8000", "nokey@localhost.run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True
        )

        output_log = []
        for _ in range(50):
            line = tunnel_process.stdout.readline()
            if line:
                output_log.append(line.strip())

            match = re.search(r"(https://[a-zA-Z0-9-]+\.lhr\.life)", line)
            if match:
                url = match.group(1) + "/scanner/"
                break

        if not url:
            console.print(
                "[bold red]❌ No se pudo establecer el túnel. Leyendo la 'Caja Negra' de SSH:[/bold red]")
            for log_line in output_log:
                if log_line:
                    console.print(f"[dim]  > {log_line}[/dim]")

            if tunnel_process:
                tunnel_process.terminate()
            return

    except Exception as e:
        console.print(
            f"[bold red]Error iniciando el túnel SSH: {e}[/bold red]")
        return

    console.print(
        f"\n[bold green]Escanea este código QR con la cámara de tu celular:[/bold green]")
    console.print(f"[blue underline]{url}[/blue underline]\n")

    qr = qrcode.QRCode(version=1, box_size=1, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_tty()

    console.print("\n[dim]El servidor ya está escuchando...[/dim]")
    Prompt.ask(
        "[bold yellow]Presiona ENTER cuando termines de escanear para cerrar la conexión[/bold yellow]")

    if tunnel_process:
        console.print("[dim]Destruyendo túnel efímero...[/dim]")
        tunnel_process.terminate()


@app.command(name="ls")
def list_structure():
    """Muestra la estructura unificada de la raíz (Directorios + Libros Huérfanos)."""
    try:
        books_resp = httpx.get("http://localhost:8000/api/books/library/")
        dirs_resp = httpx.get("http://localhost:8000/api/books/directories/")
        books_resp.raise_for_status()
        dirs_resp.raise_for_status()

        all_books = books_resp.json()
        all_dirs = dirs_resp.json()
    except Exception as e:
        console.print(f"[bold red]Error de red: {e}[/bold red]")
        return

    # Filtra solo los libros que están en la raíz (sin directorio)
    orphan_books = [b for b in all_books if b.get('directory') is None]

    # ORDENAMIENTO ALFABÉTICO
    def natural_sort_key(book_dict):
        title = book_dict.get('title', '').lower()
        return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', title)]

    all_dirs.sort(key=lambda d: d.get('name', '').lower())
    orphan_books.sort(key=natural_sort_key)

    if not all_dirs and not orphan_books:
        console.print(
            "\n[yellow]Tu biblioteca está completamente vacía.[/yellow]\n")
        return

    table = Table(title="[bold cyan]SISTEMA DE ARCHIVOS (RAÍZ)[/bold cyan]",
                  box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("ID", justify="right", style="dim", no_wrap=True)
    table.add_column("Nombre / Título", style="bold white")
    table.add_column("Autor / Detalles", style="yellow")
    table.add_column("Formato", style="magenta", justify="center")
    table.add_column("Estado", justify="center")

    # ImprimE primero las carpetas (Directorios)
    for d in all_dirs:
        d_id = d['id']
        color = d.get('color_hex', 'cyan')
        name = d.get('name', 'Unknown')
        count = sum(1 for b in all_books if b.get('directory') == d_id)

        table.add_row(
            f"[D-{d_id}]",
            f"[{color}]📁 {name.upper()}[/{color}]",
            f"[dim]Contiene {count} obras anidadas[/dim]",
            f"[{color}]DIRECTORIO[/{color}]",
            "-"
        )

    # Imprime luego los archivos sueltos (Libros)
    for b in orphan_books:
        status = "[green]✔ Leído[/green]" if b.get(
            'is_read') else "[red]✘ Pendiente[/red]"
        table.add_row(
            str(b.get('id')),
            b.get('title', 'Sin título'),
            b.get('author_name', 'Desconocido'),
            b.get('format_type', '-'),
            status
        )

    console.print()
    console.print(Align.center(table))
    console.print()


@app.command(name="tree")
def show_tree():
    """Explorador visual del Sistema de Archivos (Directorios y Libros)."""
    console.print("\n[bold cyan]ÁRBOL DE DIRECTORIOS[/bold cyan]\n")
    try:
        books = httpx.get("http://localhost:8000/api/books/library/").json()
        dirs = httpx.get("http://localhost:8000/api/books/directories/").json()
    except Exception as e:
        console.print(f"[bold red]Error de red: {e}[/bold red]")
        return

    from rich.tree import Tree

    # Crea la raíz del árbol
    root = Tree("[bold white]Mi Biblioteca[/bold white]", guide_style="cyan")

    # Agrupa libros por directorio
    books_by_dir = {}
    orphans = []
    for b in books:
        d_id = b.get('directory')
        if d_id:
            if d_id not in books_by_dir:
                books_by_dir[d_id] = []
            books_by_dir[d_id].append(b)
        else:
            orphans.append(b)

    # Dibuja los Directorios y sus libros anidados
    for d in dirs:
        d_id = d['id']
        color = d.get('color_hex', 'cyan')
        d_name = d.get('name', 'Unknown')

        # Rama del directorio (Carpeta)
        branch = root.add(f"[{color}]📁 {d_name}[/{color}]")

        # Hojas (libros pertenecientes a esta carpeta)
        dir_books = books_by_dir.get(d_id, [])
        for b in dir_books:
            status = "[green]✔[/green]" if b.get('is_read') else "[red]✘[/red]"
            branch.add(f"[dim]ID:{b['id']}[/dim] {b['title']} {status}")

    # 4. Dibujar los libros sueltos en la raíz
    if orphans:
        orphans_branch = root.add("[bold dim]Obras sin agrupar[/bold dim]")
        for b in orphans:
            status = "[green]✔[/green]" if b.get('is_read') else "[red]✘[/red]"
            orphans_branch.add(
                f"[dim]ID:{b['id']}[/dim] {b['title']} {status}")

    console.print(root)
    console.print()


@app.command(name="sync")
def run_scraper():
    """Despierta a los sabuesos (Scraper Node.js) para buscar novedades en la web."""
    console.print(
        "\n[bold cyan]INICIANDO RASTREO WEB (SCRAPER)[/bold cyan]")
    console.print("[dim]Conectando con el microservicio Node.js...[/dim]")

    project_dir = Path(__file__).resolve().parent.parent

    try:
        # docker-compose run crea un contenedor efímero, ejecuta el script y lo destruye al terminar
        process = subprocess.Popen(
            ["docker-compose", "run", "--rm", "scraper"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Lee los logs en tiempo real para que veas qué está haciendo el scraper
        for line in process.stdout:
            console.print(f"[dim green]>[/dim green] {line.strip()}")

        process.wait()

        if process.returncode == 0:
            console.print(
                "\n[bold green]Rastreo web finalizado con éxito.[/bold green]\n")
        else:
            console.print(
                "\n[bold red]El rastreo finalizó con errores (Revisa los logs arriba).[/bold red]\n")

    except FileNotFoundError:
        console.print(
            "[bold red]Comando 'docker-compose' no encontrado en el sistema.[/bold red]")
    except Exception as e:
        console.print(
            f"[bold red]Error al ejecutar el scraper: {e}[/bold red]")


@app.command(name="shell")
def interactive_shell():
    """Inicia el entorno inmersivo de la Biblioteca."""

    click.clear()

    show_welcome_screen()

    ctx = click.get_current_context()

    prompt_style = HTML(
        "<ansicyan><b>library</b></ansicyan> <ansimagenta>❯</ansimagenta> ")
    repl(ctx, prompt_kwargs={"message": prompt_style})


if __name__ == "__main__":
    app()
