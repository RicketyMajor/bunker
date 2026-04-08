import httpx
from textual.app import ComposeResult
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Label, TabbedContent, TabPane, Tree
from textual.containers import VerticalScroll, Vertical, Grid
from textual.binding import Binding
from textual import work
from .constants import API_MOVIES, API_MOVIE_INBOX, API_MOVIE_PROCESS, API_MOVIE_DIRS, API_MOVIE_TRACKER, API_MOVIE_TRACKER_ANNUAL, API_MOVIE_TRACKER_MINUTES, API_MOVIE_TRACKER_FINISH
from .modals import AddMovieMenuModal, MovieScannerModal, LendModal, ConfirmModal, ManualMovieAddModal, DirModal, MoveToDirModal, DeleteDirModal, LogMinutesModal, FinishMovieModal


class MovieInventoryTab(TabPane):
    BINDINGS = [
        ("a", "screen.add_movie", "Añadir Película"),
        ("d", "screen.show_details", "Ver Detalles"),
        ("l", "screen.lend_movie", "Prestar a Amigo"),
        ("m", "screen.move_movie", "Mover a Carpeta"),
        ("c", "screen.create_dir", "Crear Carpeta"),
        ("x", "screen.delete_movie", "Eliminar Ficha"),
        ("shift+x", "screen.delete_dir", "Borrar Carpeta"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="movies_table")


class MovieInboxTab(TabPane):
    BINDINGS = [
        Binding("enter", "screen.process_barcode",
                "Procesar Escaneo UPC", show=True, priority=True),
        ("x", "screen.delete_inbox", "Descartar"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="movie_inbox_table")


class MovieLoansTab(TabPane):
    BINDINGS = [
        ("r", "screen.return_movie", "Devolver a Bóveda"),
    ]

    def compose(self) -> ComposeResult:
        yield DataTable(id="movie_loans_table")


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


class MovieTrackerTab(TabPane):
    BINDINGS = [
        ("m", "screen.log_minutes", "Anotar Minutos"),
        ("f", "screen.finish_movie", "Registrar Cinta Vista"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("Cargando métricas cinematográficas...", id="movie_tracker_content")
            yield DataTable(id="movie_annual_table")


class MovieMainScreen(Screen):
    all_movies = []
    all_dirs = []

    BINDINGS = [
        ("escape", "go_back", "Volver al Launcher"),
        ("q", "quit", "Salir"),
        ("ctrl+b", "toggle_sidebar", "Explorador"),
        ("shift+x", "action_delete_dir", "Borrar Carpeta"),
        Binding("1", "switch_tab('tab_cartelera')", "1-4 Pestañas", show=True),
        Binding("2", "switch_tab('tab_inbox')", "Inbox", show=False),
        Binding("3", "switch_tab('tab_prestamos')", "Préstamos", show=False),
        Binding("4", "switch_tab('tab_tracker')",
                "Hábitos", show=False),
    ]

    CSS = """
    Screen { background: $surface-darken-1; }
    DataTable { height: 1fr; margin: 1 2; }
    #sidebar {
        dock: left; 
        width: 35; 
        max-width: 50%;
        height: 100%;
        background: $surface-darken-2; 
        border-right: vkey $background;
        display: none;
        overflow-x: auto; 
    }
    #sidebar.-visible { display: block; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tree("📁 Raíz del Videoclub", id="sidebar")  # El Árbol Lateral
        with TabbedContent(initial="tab_cartelera", id="movie_tabs"):
            yield MovieInventoryTab("▤ Inventario", id="tab_cartelera")
            yield MovieInboxTab("◈ Inbox", id="tab_inbox")
            yield MovieLoansTab("⇋ Préstamos", id="tab_prestamos")
            yield MovieTrackerTab("∑ Hábitos", id="tab_tracker")
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

        t_loans = self.query_one("#movie_loans_table", DataTable)
        t_loans.cursor_type = "row"
        t_loans.zebra_stripes = True
        t_loans.add_columns("ID", "Título", "Amigo", "Estado")

        t_annual = self.query_one("#movie_annual_table", DataTable)
        t_annual.cursor_type = "row"
        t_annual.zebra_stripes = True
        t_annual.add_columns("ID", "Título", "Director",
                             "Propiedad", "Visto El")

        self.title = "BUNKER"
        self.sub_title = "Módulo de Videoclub"
        self.load_movies()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    @work(thread=True)
    def load_movies(self) -> None:
        try:
            movies_resp = httpx.get(API_MOVIES, timeout=5.0)
            dirs_resp = httpx.get(API_MOVIE_DIRS, timeout=5.0)

            if movies_resp.status_code == 200:
                self.all_movies = movies_resp.json()
                dirs = dirs_resp.json() if dirs_resp.status_code == 200 else []

                # Filtra para mostrar solo la raíz por defecto
                orphan = [m for m in self.all_movies if m.get(
                    'directory') is None]
                self.app.call_from_thread(self.populate_movies, orphan)
                self.app.call_from_thread(self.populate_tree, dirs)
        except Exception:
            pass

        # Cargar Inbox Físico
        try:
            resp_inbox = httpx.get(API_MOVIE_INBOX, timeout=5.0)
            if resp_inbox.status_code == 200:
                self.app.call_from_thread(
                    self.populate_inbox, resp_inbox.json())
        except Exception:
            pass

        # Cargar Hábitos y Registro Anual de Películas
        try:
            tracker = httpx.get(API_MOVIE_TRACKER, timeout=5.0).json()
            annual = httpx.get(API_MOVIE_TRACKER_ANNUAL, timeout=5.0).json()
            if isinstance(tracker, dict):
                self.app.call_from_thread(
                    self.populate_tracker, tracker, annual)
        except Exception:
            pass

    def populate_movies(self, movies: list) -> None:
        table_inv = self.query_one("#movies_table", DataTable)
        table_loans = self.query_one("#movie_loans_table", DataTable)
        table_inv.clear()
        table_loans.clear()

        for m in movies:
            # Llenar Inventario
            if not m.get('is_loaned'):
                status = "✔" if m.get('is_watched') else "✘"
                table_inv.add_row(str(m.get('id')), m.get('title', '').upper(), m.get(
                    'director', '-'), str(m.get('release_year', '-')), status, key=str(m.get('id')))
            # Llenar Préstamos
            else:
                amigo = m.get('friend_name') or 'Desconocido'  # <- CAMBIO AQUÍ
                table_loans.add_row(str(m.get('id')), m.get('title', '').upper(),
                                    amigo, "⇋ Prestada", key=str(m.get('id')))

    def populate_inbox(self, items: list) -> None:
        table = self.query_one("#movie_inbox_table", DataTable)
        table.clear()
        for item in items:
            table.add_row(str(item.get('id')), item.get(
                'barcode', '-'), item.get('date_scanned', '')[:10], key=str(item.get('id')))

    def populate_tracker(self, stats: dict, annual: list) -> None:
        md = self.query_one("#movie_tracker_content", Markdown)
        cintas_anuales = len(annual)
        text = f"""**Mes de {stats.get('current_month', '')}:** Minutos de vuelo: `{stats.get('minutes_this_month', 0)}`  |  **Total Año:** `{cintas_anuales} cintas vistas`"""
        md.update(text)

        table = self.query_one("#movie_annual_table", DataTable)
        table.clear()
        for rec in annual:
            owned_str = "✔ Bóveda" if rec.get(
                'is_owned') else "⇋ Cine/Streaming"
            table.add_row(
                str(rec.get('id')),
                rec.get('title', '').upper(),
                rec.get('director', 'Desconocido'),
                owned_str,
                rec.get('date_watched', '')[:10],
                key=str(rec.get('id'))
            )

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#movie_tabs", TabbedContent).active = tab_id

    def on_screen_resume(self, event: ScreenResume) -> None:
        """
        Se dispara automáticamente cada vez que se cierra un modal. Efecto de actualización en tiempo real
        """
        self.load_movies()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Atrapa la tecla 'Enter' que el DataTable consume por defecto, y la redirige a nuestras funciones lógicas.
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
                self.app.push_screen(MovieScannerModal())
            elif choice == "name":
                def handle_title(title: str | None) -> None:
                    if title:
                        self.app.notify(
                            f"Consultando Oráculo para '{title}'...", title="TMDB")
                        self.process_movie_scan(title)
                self.app.push_screen(LendModal(), handle_title)
            elif choice == "full":
                # CONECTA EL FORMULARIO MANUAL AL BACKEND
                def handle_manual_save(payload: dict | None) -> None:
                    if payload:
                        self.process_manual_movie(payload)
                self.app.push_screen(ManualMovieAddModal(), handle_manual_save)

        self.app.push_screen(AddMovieMenuModal(), handle_menu_choice)

    @work(thread=True)
    def process_manual_movie(self, payload: dict) -> None:
        try:
            resp = httpx.post(f"{API_MOVIES}", json=payload, timeout=5.0)
            if resp.status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, "Película archivada manualmente.", title="Éxito")
                self.app.call_from_thread(self.load_movies)
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error guardando la cinta.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

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
                # Si Django escupe HTML gigante, lo interceptamos
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

    # --- SISTEMA DE BORRADO ---
    def action_delete_movie(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
            return
        table = self.query_one("#movies_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            title = table.get_row(row_key)[1]

            def handle_confirm(confirm: bool) -> None:
                if confirm:
                    self.execute_delete_movie(row_key)

            self.app.push_screen(ConfirmModal(
                f"¿Destruir los registros de '{title}'?"), handle_confirm)
        except Exception:
            self.app.notify("Selecciona una película.", severity="warning")

    @work(thread=True)
    def execute_delete_movie(self, movie_id: str) -> None:
        try:
            httpx.delete(f"{API_MOVIES}{movie_id}/", timeout=5.0)
            self.app.call_from_thread(
                self.app.notify, "Cinta incinerada.", title="Éxito")
            self.app.call_from_thread(self.load_movies)
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Error al eliminar.", severity="error")

    # --- SISTEMA DE PRÉSTAMOS ---
    def action_lend_movie(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
            return
        table = self.query_one("#movies_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value

            def handle_lend(friend_name: str | None) -> None:
                if friend_name:
                    # envia el nombre del amigo al backend
                    self.update_movie_status(
                        row_key, {"is_loaned": True, "friend_name": friend_name})

            self.app.push_screen(LendModal(), handle_lend)
        except Exception:
            self.app.notify("Selecciona una película.", severity="warning")

    def action_return_movie(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_prestamos":
            return
        table = self.query_one("#movie_loans_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value

            # Limpia el nombre del amigo al devolverla
            self.update_movie_status(
                row_key, {"is_loaned": False, "friend_name": ""})

        except Exception:
            self.app.notify("Selecciona una película prestada.",
                            severity="warning")

    @work(thread=True)
    def update_movie_status(self, movie_id: str, payload: dict) -> None:
        try:
            resp = httpx.patch(f"{API_MOVIES}{movie_id}/",
                               json=payload, timeout=5.0)
            if resp.status_code == 200:
                msg = "Película devuelta a la bóveda." if not payload.get(
                    "is_loaned") else "Película marcada como prestada."
                self.app.call_from_thread(self.app.notify, msg, title="Éxito")
                self.app.call_from_thread(self.load_movies)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    # --- EXPLORADOR DE ARCHIVOS (SIDEBAR) ---
    def populate_tree(self, dirs: list) -> None:
        tree = self.query_one("#sidebar", Tree)
        tree.root.expand()
        tree.root.data = "root"
        tree.clear()

        self.all_dirs = dirs

        for d in dirs:
            dir_movies = [m for m in self.all_movies if m.get(
                'directory') == d['id']]
            count = len(dir_movies)
            node_label = f"[{d.get('color_hex', 'cyan')}]■ {d['name']}[/] [dim]({count})[/dim]"

            dir_node = tree.root.add(node_label, data=d['id'])
            for m in dir_movies:
                status = "✔" if m.get('is_watched') else "✘"
                dir_node.add_leaf(
                    f"[dim]{m['id']}[/dim] {m['title']} [{status}]", data=f"movie_{m['id']}")

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Tree)
        sidebar.toggle_class("-visible")
        if sidebar.has_class("-visible"):
            sidebar.focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is None:
            return
        data_val = str(event.node.data)
        if data_val.startswith("movie_"):
            return

        if data_val == "root":
            filtered = [m for m in self.all_movies if m.get(
                'directory') is None]
        else:
            filtered = [m for m in self.all_movies if str(
                m.get('directory')) == data_val]

        self.populate_movies(filtered)
        self.action_switch_tab("tab_cartelera")

    # --- ACCIONES DE DIRECTORIOS ---
    def action_create_dir(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
            return

        def do_create(payload: dict | None) -> None:
            if payload:
                self.process_create_dir(payload)
        self.app.push_screen(DirModal(), do_create)

    @work(thread=True)
    def process_create_dir(self, payload: dict) -> None:
        try:
            if httpx.post(API_MOVIE_DIRS, json=payload, timeout=5.0).status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, f"Directorio '{payload['name']}' creado", title="Éxito")
                self.app.call_from_thread(self.load_movies)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def action_move_movie(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
            return
        table = self.query_one("#movies_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                def do_move(dest_val: str) -> None:
                    if dest_val != "cancel":
                        target_id = None if dest_val == "root" else int(
                            dest_val)
                        self.process_move_movie(row_key, target_id)
                self.app.push_screen(MoveToDirModal(
                    getattr(self, 'all_dirs', [])), do_move)
        except Exception:
            self.app.notify("Selecciona una cinta de la tabla.",
                            severity="warning")

    @work(thread=True)
    def process_move_movie(self, movie_id: str, dest_dir: int | None) -> None:
        try:
            resp = httpx.patch(f"{API_MOVIES}{movie_id}/",
                               json={"directory": dest_dir}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "¡Cinta transferida de carpeta!", title="Éxito")
                self.app.call_from_thread(self.load_movies)
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al transferir.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    def action_delete_dir(self) -> None:
        sidebar = self.query_one("#sidebar", Tree)

        # Navegación por Ctrl+B
        if sidebar.has_focus:
            selected_node = sidebar.cursor_node
            if not selected_node or selected_node.data is None:
                return

            data_val = str(selected_node.data)

            if data_val == "root":
                self.app.notify(
                    "Eso no se puede hacer. La raíz es inamovible.", severity="error")
                return
            if data_val.startswith("movie_"):
                self.app.notify(
                    "Debes seleccionar una carpeta, no un archivo.", severity="warning")
                return

            dir_id = data_val
            dir_name = next((d['name'] for d in getattr(
                self, 'all_dirs', []) if str(d['id']) == dir_id), "Directorio")

            def do_confirm_tree(confirm: bool) -> None:
                if confirm:
                    self.process_delete_dir(dir_id)

            self.app.push_screen(ConfirmModal(
                f"¿Seguro que deseas destruir la carpeta '{dir_name}'?"), do_confirm_tree)

        # En la pestaña de Inventario
        else:
            if self.query_one("#movie_tabs", TabbedContent).active != "tab_cartelera":
                return

            def do_select(dir_id: str) -> None:
                if dir_id != "cancel" and dir_id is not None:
                    dir_name = next((d['name'] for d in getattr(
                        self, 'all_dirs', []) if str(d['id']) == dir_id), "Directorio")

                    def do_confirm_table(confirm: bool) -> None:
                        if confirm:
                            self.process_delete_dir(dir_id)

                    self.app.push_screen(ConfirmModal(
                        f"¿Seguro que deseas destruir '{dir_name}'?"), do_confirm_table)

            self.app.push_screen(DeleteDirModal(
                getattr(self, 'all_dirs', [])), do_select)

    @work(thread=True)
    def process_delete_dir(self, dir_id: str) -> None:
        try:
            if httpx.delete(f"{API_MOVIE_DIRS}{dir_id}/", timeout=5.0).status_code == 204:
                self.app.call_from_thread(
                    self.app.notify, "Carpeta destruida. Las cintas volvieron a la raíz.", title="Éxito")
                self.app.call_from_thread(self.load_movies)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    # ================= TRACKER CINEMATOGRÁFICO =================
    def action_log_minutes(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_tracker":
            return

        def do_log(minutes: int | None) -> None:
            if minutes:
                self.process_log_minutes(minutes)
        self.app.push_screen(LogMinutesModal(), do_log)

    @work(thread=True)
    def process_log_minutes(self, minutes: int) -> None:
        try:
            if httpx.post(API_MOVIE_TRACKER_MINUTES, json={"minutes": minutes}, timeout=5.0).status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, f"{minutes} minutos anotados a la bitácora.", title="Éxito")
                self.app.call_from_thread(self.load_movies)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def action_finish_movie(self) -> None:
        if self.query_one("#movie_tabs", TabbedContent).active != "tab_tracker":
            return

        def do_finish(payload: dict | None) -> None:
            if payload and payload.get('title'):
                self.process_finish_movie(payload)
        self.app.push_screen(FinishMovieModal(), do_finish)

    @work(thread=True)
    def process_finish_movie(self, payload: dict) -> None:
        try:
            # Registra en el Muro de la Fama
            resp = httpx.post(API_MOVIE_TRACKER_FINISH,
                              json=payload, timeout=5.0)
            if resp.status_code == 201:
                # Auto-marcar como visto en el Inventario si existe
                lib_resp = httpx.get(API_MOVIES, params={
                                     "title": payload['title']}, timeout=5.0)
                if lib_resp.status_code == 200 and lib_resp.json():
                    movie_id = lib_resp.json()[0]['id']
                    httpx.patch(f"{API_MOVIES}{movie_id}/",
                                json={"is_watched": True}, timeout=5.0)

                self.app.call_from_thread(
                    self.app.notify, "¡Cinta registrada en el Muro de la Fama!", title="Éxito")
                self.app.call_from_thread(self.load_movies)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")
