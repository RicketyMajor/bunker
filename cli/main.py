from cli.loans import loan_app
from cli.books_write import app as write_app
from cli.books_read import app as read_app
import os
import django
import typer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_manager.settings')
django.setup()

# Importamos las "mini-apps" que creamos

# 1. Inicializar Typer principal
app = typer.Typer(
    help="CLI tool to manage my personal library.", no_args_is_help=True)

# 2. Unimos los módulos de libros en un solo comando unificado llamado "book"
book_app = typer.Typer(
    help="Manage your books, comics, and mangas.", no_args_is_help=True)
book_app.add_typer(read_app, name="")  # Funciones de lista y detalles
book_app.add_typer(write_app, name="")  # Funciones de agregar, editar, borrar

# 3. Conectamos los subcomandos al CLI principal
app.add_typer(book_app, name="book")
app.add_typer(loan_app, name="loan")

if __name__ == "__main__":
    app()
