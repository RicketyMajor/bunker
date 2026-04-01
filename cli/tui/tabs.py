from textual.app import ComposeResult
from textual.widgets import TabPane, DataTable, Markdown
from textual.containers import Vertical


class InventoryTab(TabPane):
    """Pestaña 1: El Inventario Principal."""
    BINDINGS = [
        ("a", "app.add_book", "Añadir (ISBN)"),
        ("e", "app.edit_book", "Editar Ficha"),
        ("m", "app.move_book", "Mover a Carpeta"),
        ("d", "app.show_details", "Ver Detalles"),
        ("l", "app.lend_book", "Prestar a Amigo"),
        ("c", "app.create_dir", "Crear Carpeta"),
        ("x", "app.delete_book", "Eliminar Ficha"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="books_table")


class InboxTab(TabPane):
    """Pestaña 2: El Purgatorio."""
    BINDINGS = [
        ("enter", "app.process_inbox", "Procesar Escaneo"),
        ("x", "app.delete_inbox", "Descartar Escaneo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="inbox_table")


class LoansTab(TabPane):
    BINDINGS = [
        ("r", "app.return_book", "Devolver a Estantería"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="loans_table")


class TrackerTab(TabPane):
    """Pestaña 4: Hábitos y lectura."""
    BINDINGS = [
        ("p", "app.log_pages", "Anotar Páginas"),
        ("f", "app.finish_book", "Registrar Terminado"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("Cargando métricas del sistema...", id="tracker_content")
            yield DataTable(id="annual_table")


class WishlistTab(TabPane):
    """Pestaña 5: El radar del Scraper."""
    BINDINGS = [
        ("s", "app.sync_scraper", "Sincronizar Scraper"),
        ("w", "app.add_watcher", "Vigilar Autor"),
        ("v", "app.view_watchers", "Ver/Borrar Vigilados"),
        ("d", "app.wishlist_details", "Ver Enlace"),
        ("x", "app.delete_wishlist", "Ocultar Lanzamiento"),
        ("c", "app.clear_wishlist", "Limpiar Todo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="wishlist_table")
