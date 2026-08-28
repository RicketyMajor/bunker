from textual.app import ComposeResult
from textual.widgets import TabPane, DataTable, Markdown
from textual.containers import Vertical
from textual.binding import Binding
from textual_plotext import PlotextPlot


def pintar_serie(plot: PlotextPlot, serie: list, titulo: str) -> None:
    """Paints one module's historical series as period bars.

    ONE measure per panel, always `count`. `amount` is on a different scale — pages against
    books finished — and a second y-axis is the chart mistake that misreads by construction:
    the reader compares two heights drawn to two rulers. If the amount ever needs a picture
    it gets its own panel, not a twin axis.

    Gaps are already zeros when they arrive here: `serie()` builds its periods from the
    calendar, not from the data, so an empty month is a bar of height 0 and not a hole.
    """
    plot.plt.clear_figure()
    if not serie:
        # Never an empty frame: an unpainted plot is indistinguishable from a broken one.
        plot.plt.title(f"{titulo} — sin datos")
        plot.plt.text("sin respuesta del Búnker", 0.5, 0.5)
        plot.plt.xticks([])          # ejes sin marcas: no hay escala que leer
        plot.plt.yticks([])
        plot.refresh()
        return
    # "2026-03" → "26-03", "2026-W31" → "26-W31". A 12-bar axis has no room for the century
    # and the same slice works for both periods.
    etiquetas = [p['period'][2:] for p in serie]
    valores = [p['count'] for p in serie]
    plot.plt.bar(etiquetas, valores)
    plot.plt.title(titulo)
    plot.plt.ylim(lower=0)
    # Integer ticks: the axis counts books, films and albums, and plotext's default split
    # offers "4.17 obras" — a value the data cannot take. At most six marks so a 12-bar
    # panel keeps its axis readable.
    alto = max(valores) or 1
    plot.plt.yticks(list(range(0, alto + 1, max(1, alto // 5))))
    plot.refresh()


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
    """Pestaña 4: el Registro Anual de lectura.

    Se llamó "Hábitos" hasta el 2026-08-27. Nunca contuvo hábitos de la Posada: lee
    `ReadingSession` y `AnnualRecord`. Los métodos `action_delete_habit`/`process_delete_habit`
    conservan su nombre a propósito.
    ponytail: renombrarlos toca cadenas de BINDINGS en tres ficheros para cero cambio de
    comportamiento; hazlo el día que se toque uno de esos BINDINGS por otro motivo.
    """
    BINDINGS = [
        ("p", "screen.log_pages", "Anotar Páginas"),
        ("f", "screen.finish_book", "Registrar Terminado"),
        ("x", "screen.delete_habit", "Revertir Registro"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("Cargando métricas del sistema...", id="tracker_content")
            yield PlotextPlot(id="tracker_plot")
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
    """Pestaña de Registro para el Videoclub."""
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
            yield PlotextPlot(id="music_tracker_plot")
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


def cargar_serie(pantalla, selector, modulo, titulo):
    """Fetches one module's series and paints its panel. NEVER raises.

    It runs inside a worker that has other things to load after it — the wishlist, in two of
    the three screens — and an exception escaping here drops all of them silently: the tab
    just stays empty and nothing is reported. That includes the FAILURE path, which is the
    one likely to run while the user is popping the screen: `query_one` raises `NoMatches` on
    a screen that is gone, and `call_from_thread` raises while the app is shutting down.
    """
    import httpx
    from .constants import API_TIMELINE
    try:
        datos = httpx.get(API_TIMELINE,
                          params={"module": modulo, "period": "monthly", "window": 12},
                          timeout=5.0).json().get('series', [])
    except Exception:
        # Lista vacía, no marco vacío: `pintar_serie` lo dice. Un marco sin nada afirma
        # "no hiciste nada este año", y eso es una afirmación falsa.
        datos = []
    try:
        pantalla.app.call_from_thread(_pintar_en, pantalla, selector, datos, titulo)
    except Exception:
        pass


def _pintar_en(pantalla, selector, datos, titulo):
    """Runs on the UI thread. Guarded because the screen may be gone by now."""
    try:
        pintar_serie(pantalla.query_one(selector, PlotextPlot), datos, titulo)
    except Exception:
        pass
