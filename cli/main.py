import re
import subprocess
import typer
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
import click
from click_repl import repl
from prompt_toolkit.formatted_text import HTML
import subprocess
import time
import httpx
from pathlib import Path
import sys
import pyfiglet
import socket
import sys
import platform
import qrcode
from rich.prompt import Prompt


# Importaciones limpias
from cli.books import book_app
from cli.loans import loan_app
from cli.wishlist import wishlist_app

console = Console()
app = typer.Typer(
    help="CLI tool to manage my personal library.", no_args_is_help=True)

app.add_typer(book_app, name="book")
app.add_typer(loan_app, name="loan")
app.add_typer(wishlist_app, name="wishlist")


def ensure_infrastructure_up():
    """El Orquestador Invisible: Verifica la red y levanta Docker si está caído."""
    try:
        httpx.get("http://localhost:8000/api/books/library/", timeout=0.5)
    except httpx.ConnectError:
        console.print(
            "\n[bold yellow]🚀 Infraestructura dormida. Encendiendo servidores...[/bold yellow]")
        project_dir = Path(__file__).resolve().parent.parent
        try:
            subprocess.run(["docker-compose", "up", "-d"], cwd=project_dir,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            console.print(
                "[bold red]❌ Comando 'docker-compose' no encontrado en el sistema.[/bold red]")
            return

        console.print(
            "[cyan]⏳ Sincronizando bases de datos distribuidas[/cyan]", end="")
        for _ in range(20):
            try:
                httpx.get(
                    "http://localhost:8000/api/books/library/", timeout=1.0)
                console.print(
                    "\n[bold green]✅ ¡Sistemas en línea![/bold green]\n")
                return
            except httpx.ConnectError:
                console.print(".", end="", style="cyan")
                sys.stdout.flush()
                time.sleep(1)

        console.print(
            "\n[bold red]❌ El servidor tardó demasiado en responder.[/bold red]")


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
            # Magia de interoperabilidad: Ejecutamos PowerShell desde Linux
            # para extraer la IPv4 del adaptador Wi-Fi o Ethernet del host Windows
            cmd = 'powershell.exe -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match \'Wi-Fi|Ethernet\' } | Select-Object -First 1).IPAddress"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=2)
            ip = result.stdout.strip()
            if ip:
                return ip
        except Exception:
            pass  # Si falla, caemos silenciosamente al método estándar

    # 2. Método estándar para sistemas Linux puros (tu futuro PC Ubuntu)
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
    except Exception:
        pass
    return stats


def show_welcome_screen():
    """Genera la cabecera visual y el dashboard dinámico de la aplicación."""
    ascii_art = pyfiglet.figlet_format("LIBRARY", font="slant")
    ascii_text = Text(ascii_art, style="bold cyan")

    # Obtenemos los datos dinámicos
    local_ip = get_local_ip()
    stats = get_dashboard_stats()

    # 🚀 Panel Izquierdo: Sensores
    left_text = f"""[bold white]► ESTADO DEL INVENTARIO ◄[/bold white]
  ❖ Libros en colección: [bold green]{stats['books']}[/bold green]
  ⇋ Préstamos activos: [bold yellow]{stats['loans']}[/bold yellow]
  ★ Novedades en radar: [bold magenta]{stats['wishlist']}[/bold magenta]

[bold white]► ESCÁNER MÓVIL ◄[/bold white]
  ⌖ Ejecuta: [bold cyan]scanner[/bold cyan]"""

    # 🚀 Panel Derecho: Comandos
    right_text = """[bold yellow]► MÓDULOS ACTIVOS ◄[/bold yellow]
[green]▪[/green] [bold]book[/bold] (list, add, details, edit, delete)
[green]▪[/green] [bold]loan[/bold] (list, lend, return)
[green]▪[/green] [bold]wishlist[/bold] (list, watch, watchers, clear)

[dim]Atajos del Sistema:[/dim]
[dim]  Tab  = Autocompletar[/dim]
[dim]  exit = Cerrar sesión[/dim]"""

    # Compresión vertical: padding de 0 arriba y abajo
    left_panel = Panel(
        left_text, title="[bold cyan]Métricas y Sensores[/bold cyan]", border_style="cyan", padding=(0, 2))
    right_panel = Panel(
        right_text, title="[bold magenta]Subsistemas[/bold magenta]", border_style="magenta", padding=(0, 2))

    # Ensamblamos los paneles uno al lado del otro
    dashboard = Columns([left_panel, right_panel], equal=True, expand=False)

    console.print(Align.center(ascii_text))
    # Imprimimos el dashboard ensamblado sin saltos de línea extra
    console.print(Align.center(dashboard))


@app.command(name="scanner")
def show_scanner_qr():
    """Genera un Código QR y un túnel HTTPS efímero para el escáner móvil."""
    console.print("\n[bold cyan]📱 INICIANDO ESCÁNER MÓVIL SEGURO[/bold cyan]")
    console.print(
        "[cyan]⏳ Negociando túnel cifrado (SSH Reverse Tunnel)...[/cyan]")

    tunnel_process = None
    url = ""

    try:
        tunnel_process = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-R",
                "80:localhost:8000", "nokey@localhost.run"],
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
            f"[bold red]❌ Error iniciando el túnel SSH: {e}[/bold red]")
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


@app.command(name="shell")
def interactive_shell():
    """Inicia el entorno inmersivo de la Biblioteca."""

    # 🧹 Usamos el clear nativo de click, que es 100% compatible con todos los sistemas operativos
    click.clear()

    show_welcome_screen()

    ctx = click.get_current_context()

    # El nuevo Prompt Personalizado y Dinámico
    prompt_style = HTML(
        "<ansicyan><b>library</b></ansicyan> <ansimagenta>❯</ansimagenta> ")
    repl(ctx, prompt_kwargs={"message": prompt_style})


if __name__ == "__main__":
    app()
