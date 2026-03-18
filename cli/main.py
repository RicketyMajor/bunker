import typer
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
import click
from click_repl import repl

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


@app.command(name="exit")
def exit_shell():
    """Sale del entorno inmersivo."""
    console.print(
        "[bold cyan]Cerrando la biblioteca... ¡Hasta pronto![/bold cyan]")
    raise EOFError  # <- Esta es la clave mágica para romper el bucle del REPL


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
