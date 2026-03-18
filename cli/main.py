from cli.wishlist import wishlist_app  # <-- Importamos el nuevo módulo
from cli.loans import loan_app
from cli.books_write import app as write_app
from cli.books_read import app as read_app
import os
import django
import typer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_manager.settings')
django.setup()


app = typer.Typer(
    help="CLI tool to manage my personal library.", no_args_is_help=True)

book_app = typer.Typer(
    help="Manage your books, comics, and mangas.", no_args_is_help=True)
book_app.add_typer(read_app, name="")
book_app.add_typer(write_app, name="")

app.add_typer(book_app, name="book")
app.add_typer(loan_app, name="loan")
# <-- Conectamos el módulo de wishlist
app.add_typer(wishlist_app, name="wishlist")

if __name__ == "__main__":
    app()
