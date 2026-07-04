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
        ("D", "screen.delete_dir", "Borrar Carpeta"),
        ("x", "screen.delete_book", "Eliminar Ficha"),
        ("g", "screen.show_genre_stats", "Estadísticas Géneros"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="books_table")


class InboxTab(TabPane):
    BINDINGS = [
        Binding("enter", "screen.process_inbox",
                "Procesar Escaneo", show=True, priority=True),
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
        ("x", "screen.delete_habit", "Revertir Registro"),
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


class MovieTrackerTab(TabPane):
    """Pestaña de Hábitos para el Videoclub."""
    BINDINGS = [
        ("f", "screen.finish_movie", "Registrar Película Vista"),
        ("x", "screen.delete_habit", "Revertir Registro"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("Cargando métricas cinematográficas...", id="movie_tracker_content")
            yield DataTable(id="movie_annual_table")


class MovieWishlistTab(TabPane):
    """Pestaña 5: El radar del Scraper para el Videoclub."""
    BINDINGS = [
        ("s", "screen.sync_scraper", "Sincronizar Scraper"),
        ("w", "screen.add_watcher", "Vigilar Director/Saga"),
        ("v", "screen.view_watchers", "Ver/Borrar Vigilados"),
        ("x", "screen.delete_wishlist", "Ocultar Lanzamiento"),
        ("c", "screen.clear_wishlist", "Limpiar Todo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="movie_wishlist_table")


class MusicInventoryTab(TabPane):
    BINDINGS = [
        ("a", "screen.add_album", "Añadir Disco"),
        ("e", "screen.edit_album", "Editar Ficha"),
        ("d", "screen.show_details", "Ver Detalles"),
        ("l", "screen.lend_album", "Prestar a Amigo"),
        ("m", "screen.move_album", "Mover a Carpeta"),
        ("c", "screen.create_dir", "Crear Carpeta"),
        ("D", "screen.delete_dir", "Borrar Carpeta"),
        ("x", "screen.delete_album", "Eliminar Ficha"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="music_table")


class MusicInboxTab(TabPane):
    BINDINGS = [
        Binding("enter", "screen.process_barcode",
                "Procesar Escaneo", show=True, priority=True),
        ("x", "screen.delete_inbox", "Descartar"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="music_inbox_table")


class MusicLoansTab(TabPane):
    BINDINGS = [("r", "screen.return_album", "Devolver a Estantería")]

    def compose(self) -> ComposeResult:
        yield DataTable(id="music_loans_table")


class MusicTrackerTab(TabPane):
    BINDINGS = [("f", "screen.finish_album", "Registrar Escucha"),
                ("x", "screen.delete_habit", "Revertir Registro")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("Cargando métricas musicales...", id="music_tracker_content")
            yield DataTable(id="music_annual_table")


class MusicWishlistTab(TabPane):
    BINDINGS = [
        ("s", "screen.sync_scraper", "Sincronizar Scraper"),
        ("w", "screen.add_watcher", "Vigilar Artista/Sello"),
        ("v", "screen.view_watchers", "Ver/Borrar Vigilados"),
        ("x", "screen.delete_wishlist", "Ocultar Lanzamiento"),
        ("c", "screen.clear_wishlist", "Limpiar Todo"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="music_wishlist_table")
