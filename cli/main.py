import typer
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
import click
from click_repl import repl
from prompt_toolkit.formatted_text import HTML
import subprocess
import time
import httpx
from pathlib import Path
import sys
import pyfiglet

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


def show_welcome_screen():
    """Genera la cabecera visual de la aplicación."""
    # Arte ASCII principal
    ascii_art = pyfiglet.figlet_format("LIBRARY", font="slant")
    ascii_text = Text(ascii_art, style="bold cyan")

    welcome_text = """
[dim]Tu ecosistema distribuido está en línea y operando.[/dim]

[bold yellow]Módulos Principales:[/bold yellow]
[green]▸[/green] [bold]book[/bold] (list, add, details, edit, delete)
[green]▸[/green] [bold]loan[/bold] (list, lend, return)
[green]▸[/green] [bold]wishlist[/bold] (list, watch, watchers, clear)

[dim]Presiona [bold]Tab[/bold] para autocompletar. Escribe [bold]exit[/bold] para salir.[/dim]
    """

    # Imprimimos el ASCII centrado
    console.print(Align.center(ascii_text))
    # Imprimimos el panel de comandos centrado debajo del ASCII
    console.print(Align.center(
        Panel(welcome_text, title="[bold magenta]Terminal UI v2.0[/bold magenta]",
              border_style="cyan", expand=False)
    ))
    console.print()  # Salto de línea extra para respirar


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
