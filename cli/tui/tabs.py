from textual.app import ComposeResult
from textual.widgets import TabPane, DataTable, Markdown
from textual.containers import Vertical
from textual.binding import Binding


class InventoryTab(TabPane):
    BINDINGS = [
        ("a", "screen.add_book", "Añadir (ISBN)"),
        ("e", "screen.edit_book", "Editar Ficha"),
        ("m", "screen.move_book", "Mover a Carpeta"),
        ("d", "screen.show_details", "Ver Detalles"),
        ("l", "screen.lend_book", "Prestar a Amigo"),
        ("c", "screen.create_dir", "Crear Carpeta"),
        ("x", "screen.delete_book", "Eliminar Ficha"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="books_table")


class InboxTab(TabPane):
    BINDINGS = [
        # Fuerza a Textual a mostrar el Enter en el Footer
        Binding("enter", "screen.process_inbox",
                "Procesar Escaneo", show=True),
        ("x", "screen.delete_inbox", "Descartar Escaneo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="inbox_table")


class LoansTab(TabPane):
    BINDINGS = [
        ("r", "screen.return_book", "Devolver a Estantería"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="loans_table")


class TrackerTab(TabPane):
    """Pestaña 4: Hábitos y lectura."""
    BINDINGS = [
        ("p", "screen.log_pages", "Anotar Páginas"),
        ("f", "screen.finish_book", "Registrar Terminado"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("Cargando métricas del sistema...", id="tracker_content")
            yield DataTable(id="annual_table")


class WishlistTab(TabPane):
    """Pestaña 5: El radar del Scraper."""
    BINDINGS = [
        ("s", "screen.sync_scraper", "Sincronizar Scraper"),
        ("w", "screen.add_watcher", "Vigilar Autor"),
        ("v", "screen.view_watchers", "Ver/Borrar Vigilados"),
        ("d", "screen.wishlist_details", "Ver Enlace"),
        ("x", "screen.delete_wishlist", "Ocultar Lanzamiento"),
        ("c", "screen.clear_wishlist", "Limpiar Todo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="wishlist_table")
