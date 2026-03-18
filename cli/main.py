import typer
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
import click
from click_repl import repl
import subprocess
import time
import httpx
from pathlib import Path
import sys

# Importaciones limpias
from cli.books import book_app
from cli.loans import loan_app
from cli.wishlist import wishlist_app

console = Console()
app = typer.Typer(
    help="CLI tool to manage my personal library.", no_args_is_help=True)

# Conectamos los subcomandos de forma directa
app.add_typer(book_app, name="book")
app.add_typer(loan_app, name="loan")
app.add_typer(wishlist_app, name="wishlist")


def ensure_infrastructure_up():
    """El Orquestador Invisible: Verifica la red y levanta Docker si está caído."""
    try:
        # Hacemos un 'ping' ultrarrápido (0.5 segundos) a la API
        httpx.get("http://localhost:8000/api/books/library/", timeout=0.5)
    except httpx.ConnectError:
        console.print(
            "\n[bold yellow]🚀 Infraestructura dormida. Encendiendo contenedores Docker...[/bold yellow]")

        # Magia de rutas: Obtenemos la carpeta raíz del proyecto de forma absoluta
        # (Sube dos niveles desde cli/main.py -> cli/ -> library_manager/)
        project_dir = Path(__file__).resolve().parent.parent

        try:
            # Ejecutamos docker-compose silenciosamente en segundo plano
            subprocess.run(["docker-compose", "up", "-d"], cwd=project_dir,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            console.print(
                "[bold red]❌ Comando 'docker-compose' no encontrado en el sistema.[/bold red]")
            return

        console.print(
            "[cyan]⏳ Esperando sincronización de bases de datos[/cyan]", end="")

        # Bucle de espera inteligente (Ping por segundo)
        for _ in range(20):
            try:
                httpx.get(
                    "http://localhost:8000/api/books/library/", timeout=1.0)
                console.print(
                    "\n[bold green]✅ ¡Servidor en línea! Entrando a la Matrix...[/bold green]\n")
                return
            except httpx.ConnectError:
                console.print(".", end="", style="cyan")
                sys.stdout.flush()  # Forzamos a que el puntito se imprima en pantalla
                time.sleep(1)

        console.print(
            "\n[bold red]❌ El servidor tardó demasiado en responder.[/bold red]")


@app.callback()
def main_callback():
    """Este hook se ejecuta automáticamente antes de cualquier subcomando (shell, book list, etc.)"""
    ensure_infrastructure_up()


@app.command(name="exit")
def exit_shell():
    """Sale del entorno inmersivo."""
    console.print(
        "[bold cyan]Cerrando la biblioteca... ¡Hasta pronto![/bold cyan]")
    raise EOFError


@app.command(name="shell")
def interactive_shell():
    """Inicia el entorno inmersivo de la Biblioteca."""
    welcome_text = """
[bold cyan]📚 BIENVENIDO A TU BIBLIOTECA DISTRIBUIDA 📚[/bold cyan]

[dim]Escribe un comando para empezar (ej. 'book list' o 'wishlist list').
Presiona [bold]Tab[/bold] para autocompletar. Escribe [bold]exit[/bold] para salir.[/dim]
    """
    console.print(Align.center(
        Panel(welcome_text, expand=False, border_style="cyan")))

    ctx = click.get_current_context()
    repl(ctx, prompt_kwargs={"message": "library-cli > "})


if __name__ == "__main__":
    app()
