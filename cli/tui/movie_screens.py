import httpx
from textual.app import ComposeResult
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Label, TabbedContent, TabPane
from textual.containers import VerticalScroll, Vertical, Grid
from textual.binding import Binding
from textual import work
from .constants import API_MOVIES, API_MOVIE_INBOX, API_MOVIE_PROCESS
from .modals import AddMovieMenuModal, MovieScannerModal, LendModal


class MovieInventoryTab(TabPane):
    BINDINGS = [
        ("a", "screen.add_movie", "Añadir (Manual)"),
        ("d", "screen.show_details", "Ver Detalles"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="movies_table")


class MovieInboxTab(TabPane):
    BINDINGS = [
        ("enter", "screen.process_barcode", "Procesar Escaneo UPC"),
        ("x", "screen.delete_inbox", "Descartar"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="movie_inbox_table")


class MovieDetailsScreen(Screen):
    BINDINGS = [
        ("escape, b, left", "go_back", "Volver a la Cartelera"),
    ]

    CSS = """
    #movie_root { padding: 1 2; }
    #movie_header {
        border: heavy $warning; background: $surface; margin-bottom: 1; padding: 1 2;
        align: center middle; content-align: center middle;
    }
    #movie_title { text-style: bold; color: $text; }
    #movie_subtitle { color: $text-muted; margin-top: 1; }
    #movie_grid { grid-size: 3; grid-columns: 1fr 2fr 2fr; grid-gutter: 2; }
    .movie_panel { border: heavy $accent; padding: 0 1; background: $surface; height: auto; }
    #poster_panel { border: double $success; text-align: center; color: $text; height: 100%; content-align: center middle; }
    """

    def __init__(self, movie_id: str, **kwargs):
        super().__init__(**kwargs)
        self.movie_id = movie_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="movie_root"):
            with Vertical(id="movie_header"):
                yield Label("Cargando...", id="movie_title")
                yield Label("", id="movie_subtitle")
            with Grid(id="movie_grid"):
                with Vertical(classes="movie_panel", id="poster_panel"):
                    yield Label("Póster")
                with Vertical(classes="movie_panel"):
                    yield Markdown("### Ficha Técnica", id="movie_tech")
                with Vertical(classes="movie_panel"):
                    yield Markdown("### Sinopsis", id="movie_synopsis")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_details()

    @work(thread=True)
    def fetch_details(self) -> None:
        try:
            resp = httpx.get(f"{API_MOVIES}{self.movie_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_details, resp.json())
        except Exception:
            pass

    def render_details(self, movie: dict) -> None:
        self.query_one("#movie_title", Label).update(
            f"[bold]{movie.get('title', '').upper()}[/bold]")
        self.query_one("#movie_subtitle", Label).update(
            f"Dirigida por: {movie.get('director', 'Desconocido')}")

        tech = f"**Año:** {movie.get('release_year', '-')}\n**Duración:** {movie.get('duration_minutes', '-')} min\n**Géneros:** {', '.join(movie.get('genres', []))}"
        self.query_one("#movie_tech", Markdown).update(tech)
        self.query_one("#movie_synopsis", Markdown).update(
            movie.get('synopsis', 'Sin descripción.'))

    def action_go_back(self) -> None:
        self.app.pop_screen()


class MovieMainScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Volver al Bunker"),
        Binding("1", "switch_tab('tab_cartelera')", "1-2 Pestañas", show=True),
        Binding("2", "switch_tab('tab_inbox')", "Inbox", show=False),
    ]

    CSS = """
    Screen { background: $surface-darken-1; }
    DataTable { height: 1fr; margin: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="tab_cartelera", id="movie_tabs"):
            yield MovieInventoryTab("Inventario", id="tab_cartelera")
            yield MovieInboxTab("◈ Inbox Físico", id="tab_inbox")
        yield Footer()

    def on_mount(self) -> None:
        t_movies = self.query_one("#movies_table", DataTable)
        t_movies.cursor_type = "row"
        t_movies.zebra_stripes = True
        t_movies.add_columns("ID", "Título", "Director", "Año", "Visto")

        t_inbox = self.query_one("#movie_inbox_table", DataTable)
        t_inbox.cursor_type = "row"
        t_inbox.zebra_stripes = True
        t_inbox.add_columns("ID", "Código EAN/UPC", "Fecha de Escaneo")

        self.load_movies()

    @work(thread=True)
    def load_movies(self) -> None:
        # Cargar Cartelera
        try:
            resp = httpx.get(API_MOVIES, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.populate_movies, resp.json())
        except Exception:
            pass

        # Cargar Inbox de Películas
        try:
            resp_inbox = httpx.get(API_MOVIE_INBOX, timeout=5.0)
            if resp_inbox.status_code == 200:
                self.app.call_from_thread(
                    self.populate_inbox, resp_inbox.json())
        except Exception:
            pass

    def populate_movies(self, movies: list) -> None:
        table = self.query_one("#movies_table", DataTable)
        table.clear()
        for m in movies:
            status = "✔" if m.get('is_watched') else "✘"
            table.add_row(str(m.get('id')), m.get('title', '').upper(), m.get(
                'director', '-'), str(m.get('release_year', '-')), status, key=str(m.get('id')))

    def populate_inbox(self, items: list) -> None:
        table = self.query_one("#movie_inbox_table", DataTable)
        table.clear()
        for item in items:
            table.add_row(str(item.get('id')), item.get(
                'barcode', '-'), item.get('date_scanned', '')[:10], key=str(item.get('id')))

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#movie_tabs", TabbedContent).active = tab_id

    def on_screen_resume(self, event: ScreenResume) -> None:
        """
        [EVENTO NATIVO] 
        Se dispara automáticamente cada vez que se cierra un modal (como el del escáner).
        ¡Esto crea el efecto de actualización en tiempo real!
        """
        self.load_movies()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        [EVENTO NATIVO]
        Atrapa la tecla 'Enter' que el DataTable consume por defecto, 
        y la redirige a nuestras funciones lógicas.
        """
        if event.control.id == "movie_inbox_table":
            self.action_process_barcode()
        elif event.control.id == "movies_table":
            self.action_show_details()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        for widget in event.pane.query("*"):
            if isinstance(widget, DataTable):
                widget.focus()
                break

    # --- ACCIONES DE LA CARTELERA ---
    def action_show_details(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
            return
        table = self.query_one("#movies_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.app.push_screen(MovieDetailsScreen(movie_id=row_key))
        except Exception:
            self.app.notify("Selecciona una película.", severity="warning")

    def action_add_movie(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
            return

        def handle_menu_choice(choice: str) -> None:
            if choice == "scan":
                # Levantamos el túnel exclusivo de películas
                self.app.push_screen(MovieScannerModal())
            elif choice == "name":
                def handle_title(title: str | None) -> None:
                    if title:
                        self.app.notify(
                            f"Consultando Oráculo para '{title}'...", title="TMDB")
                        self.process_movie_scan(title)
                self.app.push_screen(LendModal(), handle_title)
            elif choice == "full":
                self.app.notify(
                    "Modo 100% Manual en construcción...", severity="warning")

        self.app.push_screen(AddMovieMenuModal(), handle_menu_choice)

    @work(thread=True)
    def process_movie_scan(self, title: str) -> None:
        try:
            resp = httpx.post(
                "http://localhost:8000/api/movies/scan/", json={"title": title}, timeout=10.0)
            if resp.status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, "¡Cinta archivada exitosamente!", title="Éxito")
                self.app.call_from_thread(self.load_movies)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error: {resp.json().get('error')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    # --- ACCIONES DEL INBOX FÍSICO ---
    def action_process_barcode(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_inbox":
            return
        table = self.query_one("#movie_inbox_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                barcode = table.get_row(row_key)[1]
                self.app.notify(
                    f"Consultando API Comercial para EAN: {barcode}...", title="Traductor")
                self.process_barcode_api(row_key, barcode)
        except Exception:
            self.app.notify(
                "Selecciona un escaneo de la tabla.", severity="warning")

    @work(thread=True)
    def process_barcode_api(self, inbox_id: str, barcode: str) -> None:
        try:
            resp = httpx.post(API_MOVIE_PROCESS, json={
                              "barcode": barcode}, timeout=15.0)
            if resp.status_code == 201:
                httpx.delete(f"{API_MOVIE_INBOX}{inbox_id}/", timeout=5.0)
                self.app.call_from_thread(
                    self.app.notify, "¡Película procesada y guardada en el Videoclub!", title="Éxito")
                self.app.call_from_thread(self.load_movies)
            else:
                # BLINDAJE ANTI-CONGELAMIENTOS: Si Django escupe HTML gigante, lo interceptamos
                if resp.status_code >= 500:
                    error_msg = "Error 500: Fallo interno de Django. Revisa los logs de Docker."
                else:
                    error_msg = resp.json().get('error', 'Error desconocido') if resp.status_code in [
                        400, 404] else str(resp.text)[:100]
                self.app.call_from_thread(
                    self.app.notify, f"Error: {error_msg}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    def action_delete_inbox(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_inbox":
            return
        table = self.query_one("#movie_inbox_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.process_delete_inbox(row_key)
        except Exception:
            self.app.notify("Selecciona un escaneo.", severity="warning")

    @work(thread=True)
    def process_delete_inbox(self, inbox_id: str) -> None:
        try:
            if httpx.delete(f"{API_MOVIE_INBOX}{inbox_id}/", timeout=5.0).status_code == 204:
                self.app.call_from_thread(
                    self.app.notify, "Código descartado.", title="Éxito")
                self.app.call_from_thread(self.load_movies)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()
