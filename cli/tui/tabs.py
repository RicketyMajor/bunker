from textual.app import ComposeResult
from textual.widgets import TabPane, DataTable, Markdown
from textual.containers import Vertical


class InventoryTab(TabPane):
    """Pestaña 1: El Inventario Principal."""
    BINDINGS = [
        ("a", "app.add_book", "Añadir (ISBN)"),
        ("e", "app.edit_book", "Editar Ficha"),
        ("d", "app.show_details", "Ver Detalles"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="books_table")


class InboxTab(TabPane):
    """Pestaña 2: El Purgatorio."""
    BINDINGS = [
        ("enter", "app.process_inbox", "Procesar Escaneo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="inbox_table")


class LoansTab(TabPane):
    """Pestaña 3: Préstamos a amigos."""
    BINDINGS = [
        ("l", "app.lend_book", "Prestar Libro"),
        ("r", "app.return_book", "Devolver"),
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
        # 🚀 Anidamos el panel de stats y la tabla debajo
        with Vertical():
            yield Markdown("Cargando métricas del sistema...", id="tracker_content")
            yield DataTable(id="annual_table")


class WishlistTab(TabPane):
    """Pestaña 5: El radar del Scraper."""
    BINDINGS = [
        ("s", "app.sync_scraper", "Sincronizar Scraper"),
        ("w", "app.add_watcher", "Vigilar Autor"),
        ("d", "app.wishlist_details", "Ver Enlace"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="wishlist_table")
