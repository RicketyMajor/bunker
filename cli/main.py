from cli.loans import loan_app
from cli.books import book_app
import os
import django
import typer

# 1. Configuración de Django (Debe ir estrictamente al principio)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_manager.settings')
django.setup()

# 2. Importaciones Locales (Solo se importan después de configurar Django)
# Al ejecutar desde la raíz, Python reconoce la carpeta 'cli' como un paquete

# 3. Inicializar Typer principal
app = typer.Typer(
    help="CLI tool to manage my personal library.", no_args_is_help=True)

# 4. Conectar los submódulos
app.add_typer(book_app, name="book")
app.add_typer(loan_app, name="loan")

# 5. Ejecución
if __name__ == "__main__":
    app()
