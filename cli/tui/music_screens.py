import httpx
from textual.app import ComposeResult
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Label, TabbedContent, Tree, Input
from textual.containers import VerticalScroll, Vertical, Grid
from textual.binding import Binding
from textual import work

# Importaciones locales
from .constants import (
    API_MUSIC, API_MUSIC_DIRS, API_MUSIC_INBOX, API_MUSIC_PROCESS, API_MUSIC_SCAN,
    API_MUSIC_TRACKER, API_MUSIC_TRACKER_ANNUAL, API_MUSIC_TRACKER_FINISH,
    API_MUSIC_WATCHERS, API_MUSIC_WISHLIST, API_MUSIC_TRACKER_LOG
)
from .modals import (
    AddMusicMenuModal, MusicScannerModal, MusicTitleModal, MusicFullEditModal,
    FinishMusicModal, LendModal, ConfirmModal, DirModal, MoveToDirModal,
    DeleteDirModal, SyncConsoleModal, WatcherModal, WatchersListModal,
    LogMinutesModal
)
from .tabs import (
    MusicInventoryTab, MusicInboxTab, MusicLoansTab, MusicTrackerTab, MusicWishlistTab
)


class MusicDetailsScreen(Screen):
    """Pantalla de detalles profundos para un Álbum."""
    BINDINGS = [
        ("escape, b, left", "go_back", "Volver a la Disquera"),
    ]

    CSS = """
    #music_root { padding: 1 2; }
    #music_header {
        border: heavy $success; background: $surface; margin-bottom: 1; padding: 0 1;
        align: center middle; content-align: center middle; height: auto;
    }
    #music_title { text-style: bold; color: $text; }
    #music_subtitle { color: $text-muted; margin-top: 1; }
    
    #music_grid { grid-size: 2; grid-columns: 1fr 2fr; grid-gutter: 2; }
    .music_panel { border: heavy $accent; padding: 0 1; background: $surface; height: 100%; }
    """

    def __init__(self, album_id: str, **kwargs):
        super().__init__(**kwargs)
        self.album_id = album_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="music_root"):
            with Vertical(id="music_header"):
                yield Label("Cargando aguja...", id="music_title")
                yield Label("", id="music_subtitle")
            with Grid(id="music_grid"):
                with Vertical(classes="music_panel"):
                    yield Markdown("### Ficha Técnica", id="music_tech")
                with VerticalScroll(classes="music_panel"):
                    yield Markdown("### Detalles de Edición\n*(Datos extraídos del Oráculo de Discogs)*", id="music_notes")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_details()

    @work(thread=True)
    def fetch_details(self) -> None:
        try:
            resp = httpx.get(f"{API_MUSIC}{self.album_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_details, resp.json())
        except Exception:
            pass

    def render_details(self, album: dict) -> None:
        self.query_one("#music_title", Label).update(
            f"[bold]{album.get('title', '').upper()}[/bold]")
        self.query_one("#music_subtitle", Label).update(
            f"Artista: {album.get('artist', 'Desconocido')}")

        tech = f"**Artista:** {album.get('artist', '-')}\n"
        tech += f"**Sello (Label):** {album.get('label', '-')}\n"
        tech += f"**Formato:** {album.get('format_type', 'VINYL')}\n"
        tech += f"**Año:** {str(album.get('release_year') or '-')}\n"
        tech += f"**Géneros/Estilos:** {', '.join(album.get('genres', []))}"

        self.query_one("#music_tech", Markdown).update(tech)

    def action_go_back(self) -> None:
        self.app.pop_screen()


class MusicMainScreen(Screen):
    """Controlador central de la Disquera (Búnker Musical)."""

    all_albums = []
    all_dirs = []

    BINDINGS = [
        ("escape", "go_back", "Volver al Launcher"),
        ("q", "quit", "Salir"),
        ("ctrl+b", "toggle_sidebar", "Explorador"),
        ("a", "action_add_album", "Añadir Disco"),
        ("M", "action_move_album", "Mover a Carpeta"),
        ("/", "focus_search", "Buscador Global"),
        Binding("1", "switch_tab('tab_disquera')", "1-5 Pestañas", show=True),
        Binding("2", "switch_tab('tab_inbox')", "Inbox", show=False),
        Binding("3", "switch_tab('tab_prestamos')", "Préstamos", show=False),
        Binding("4", "switch_tab('tab_tracker')", "Hábitos", show=False),
        Binding("5", "switch_tab('tab_wishlist')", "Tablón", show=False),
    ]

    CSS = """
    Screen { background: $surface-darken-1; }
    DataTable { height: 1fr; margin: 1 2; }
    #music_tracker_content { height: auto; margin: 1 2 0 2; padding: 1; border: solid $success; background: $surface; }
    
    #sidebar {
        dock: left; 
        width: 45; 
        max-width: 60%;
        height: 100%;
        background: $surface-darken-2; 
        border-right: vkey $background;
        display: none;
        overflow-x: auto; 
    }
    #sidebar.-visible { display: block; }
    Tree { overflow-x: auto; } 

    /* Buscador Global (Fuzzy) */
    #search_bar {
        display: none;
        dock: bottom;
        margin-bottom: 1;
        border-top: solid $success;
        background: $surface-darken-1;
    }
    #search_bar.-visible { display: block; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Tree("📁 Estantería de Discos", id="sidebar")
        with TabbedContent(initial="tab_disquera", id="music_tabs"):
            yield MusicInventoryTab("▤ Colección", id="tab_disquera")
            yield MusicInboxTab("◈ Inbox", id="tab_inbox")
            yield MusicLoansTab("⇋ Préstamos", id="tab_prestamos")
            yield MusicTrackerTab("∑ Hábitos", id="tab_tracker")
            yield MusicWishlistTab("★ Tablón", id="tab_wishlist")

        yield Input(id="search_bar", placeholder="Búsqueda instantánea (Título o Artista)...")
        yield Footer()

    def on_mount(self) -> None:
        self.current_dir = "root"

        # Init Tablas
        t_inv = self.query_one("#music_table", DataTable)
        t_inv.cursor_type = "row"
        t_inv.zebra_stripes = True
        t_inv.add_columns("ID", "Álbum", "Artista", "Año",
                          "Sello", "Formato", "Duración", "Escuchado")

        t_inbox = self.query_one("#music_inbox_table", DataTable)
        t_inbox.cursor_type = "row"
        t_inbox.zebra_stripes = True
        t_inbox.add_columns("ID", "Código EAN/UPC", "Fecha de Escaneo")

        t_loans = self.query_one("#music_loans_table", DataTable)
        t_loans.cursor_type = "row"
        t_loans.zebra_stripes = True
        t_loans.add_columns("ID", "Álbum", "Amigo", "Estado")

        t_annual = self.query_one("#music_annual_table", DataTable)
        t_annual.cursor_type = "row"
        t_annual.zebra_stripes = True
        t_annual.add_columns("ID", "Álbum", "Artista",
                             "Propiedad", "Escuchado El")

        t_wishlist = self.query_one("#music_wishlist_table", DataTable)
        t_wishlist.cursor_type = "row"
        t_wishlist.zebra_stripes = True
        t_wishlist.add_columns("ID", "Lanzamiento / Edición",
                               "Artista/Sello", "Año", "Detectado")

        self.title = "BUNKER"
        self.sub_title = "Módulo de Disquera"
        self.load_data()

    # --- RUTINAS DE CARGA Y REFRESCO ---
    @work(thread=True)
    def load_data(self) -> None:
        try:
            albums_resp = httpx.get(API_MUSIC, timeout=5.0)
            dirs_resp = httpx.get(API_MUSIC_DIRS, timeout=5.0)
            if albums_resp.status_code == 200:
                self.all_albums = albums_resp.json()
                dirs = dirs_resp.json() if dirs_resp.status_code == 200 else []
                self.app.call_from_thread(self.update_ui_albums, dirs)
        except Exception:
            pass

        try:
            inbox = httpx.get(API_MUSIC_INBOX, timeout=5.0).json()
            if isinstance(inbox, list):
                self.app.call_from_thread(self.populate_inbox, inbox)
        except Exception:
            pass

        try:
            # .raise_for_status() para detectar errores de URL de inmediato
            tracker_resp = httpx.get(API_MUSIC_TRACKER, timeout=5.0)
            tracker_resp.raise_for_status()
            tracker = tracker_resp.json()

            annual_resp = httpx.get(API_MUSIC_TRACKER_ANNUAL, timeout=5.0)
            annual_resp.raise_for_status()
            annual = annual_resp.json()

            if isinstance(tracker, dict):
                self.app.call_from_thread(
                    self.populate_tracker, tracker, annual)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error en métricas: {e}", severity="error")
            pass

        try:
            wishlist = httpx.get(API_MUSIC_WISHLIST, timeout=5.0).json()
            if isinstance(wishlist, list):
                self.app.call_from_thread(self.populate_wishlist, wishlist)
        except Exception:
            pass

    def update_ui_albums(self, dirs: list) -> None:
        self.populate_tree(dirs)
        if getattr(self, 'current_dir', 'root') == "root":
            filtered = [a for a in self.all_albums if a.get(
                'directory') is None]
        else:
            filtered = [a for a in self.all_albums if str(
                a.get('directory')) == self.current_dir]
        self.populate_albums(filtered)

    def populate_albums(self, albums: list) -> None:
        table_inv = self.query_one("#music_table", DataTable)
        table_loans = self.query_one("#music_loans_table", DataTable)
        table_inv.clear()
        table_loans.clear()

        for a in albums:
            if not a.get('is_loaned'):
                status = "✔" if a.get('is_listened') else "✘"
                dur = f"{a.get('duration_minutes')}m" if a.get('duration_minutes') else "-"
                table_inv.add_row(
                    str(a.get('id')), a.get(
                        'title', '').upper(), a.get('artist', '-'),
                    str(a.get('release_year') or '-'), a.get('label', '-'),
                    a.get('format_type', 'VINYL'), dur, status, key=str(a.get('id'))
                )
            else:
                amigo = a.get('friend_name') or 'Desconocido'
                table_loans.add_row(
                    str(a.get('id')), a.get('title', '').upper(), amigo, "⇋ Prestado", key=str(a.get('id'))
                )

    def populate_inbox(self, items: list) -> None:
        table = self.query_one("#music_inbox_table", DataTable)
        table.clear()
        for item in items:
            table.add_row(str(item.get('id')), item.get(
                'barcode', '-'), item.get('date_scanned', '')[:10], key=str(item.get('id')))

    def populate_tracker(self, stats: dict, annual: list) -> None:
        md = self.query_one("#music_tracker_content", Markdown)
        # El backend ya filtra annual por el año actual
        count_year = len(annual)
        count_month = stats.get('albums_this_month', 0)

        # Implementación
        text = f"**Mes de {stats.get('current_month', '')}:** `{count_month} álbumes escuchados`  |  **Total Año:** `{count_year} álbumes escuchados`"
        md.update(text)

        table = self.query_one("#music_annual_table", DataTable)
        table.clear()
        for rec in annual:
            owned = "✔ Bóveda" if rec.get('is_owned') else "⇋ Digital/Externo"
            table.add_row(
                str(rec.get('id')),
                rec.get('title', '').upper(),
                rec.get('artist', '-'),
                owned,
                rec.get('date_listened', '')[:10],
                key=str(rec.get('id'))
            )

    def populate_wishlist(self, items: list) -> None:
        table = self.query_one("#music_wishlist_table", DataTable)
        table.clear()
        for item in items:
            table.add_row(
                str(item.get('id')), item.get(
                    'title', '').upper(), item.get('artist') or "-",
                item.get('release_year') or "-", item.get('date_found', '')[:10], key=str(item.get('id'))
            )

    # --- NAVEGACIÓN Y MOTOR FUZZY ---
    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#music_tabs", TabbedContent).active = tab_id

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        for widget in event.pane.query("*"):
            if isinstance(widget, DataTable):
                widget.focus()
                break

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.load_data()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.control.id == "music_inbox_table":
            self.action_process_barcode()
        elif event.control.id == "music_table":
            self.action_show_details()

    def action_focus_search(self) -> None:
        search_bar = self.query_one("#search_bar", Input)
        if search_bar.has_class("-visible"):
            search_bar.remove_class("-visible")
            search_bar.value = ""
            self.query_one("#music_table", DataTable).focus()
        else:
            search_bar.add_class("-visible")
            search_bar.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.control.id == "search_bar":
            query = event.value.lower()
            if not query:
                self.update_ui_albums(getattr(self, 'all_dirs', []))
                return
            filtered = [
                a for a in getattr(self, 'all_albums', [])
                if query in a.get('title', '').lower() or query in a.get('artist', 'desconocido').lower()
            ]
            self.populate_albums(filtered)
            tabs = self.query_one("#music_tabs", TabbedContent)
            if tabs.active != "tab_disquera":
                tabs.active = "tab_disquera"

    def action_go_back(self) -> None:
        search_bar = self.query_one("#search_bar", Input)
        if search_bar.has_class("-visible"):
            search_bar.remove_class("-visible")
            search_bar.value = ""
            self.query_one("#music_table", DataTable).focus()
            return
        self.app.pop_screen()

    # --- ACCIONES PRINCIPALES DE COLECCIÓN ---
    def action_show_details(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return
        table = self.query_one("#music_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.app.push_screen(MusicDetailsScreen(album_id=row_key))
        except Exception:
            self.app.notify("Selecciona un álbum.", severity="warning")

    def action_add_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return

        def handle_menu_choice(choice: str) -> None:
            if choice == "scan":
                self.app.push_screen(MusicScannerModal())
            elif choice == "name":
                def handle_title(title: str | None) -> None:
                    if title:
                        self.app.notify(
                            f"Consultando a Discogs para '{title}'...", title="Oráculo")
                        self.process_manual_scan(title)
                self.app.push_screen(MusicTitleModal(), handle_title)
            elif choice == "full":
                def handle_manual_save(payload: dict | None) -> None:
                    if payload:
                        self.process_manual_album(payload)
                self.app.push_screen(
                    MusicFullEditModal({}), handle_manual_save)

        self.app.push_screen(AddMusicMenuModal(), handle_menu_choice)

    @work(thread=True)
    def process_manual_scan(self, title: str) -> None:
        try:
            resp = httpx.post(API_MUSIC_SCAN, json={
                              "title": title}, timeout=15.0)
            if resp.status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, "¡Álbum archivado exitosamente!", title="Éxito")
                self.app.call_from_thread(self.load_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error: {resp.json().get('error')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    @work(thread=True)
    def process_manual_album(self, payload: dict) -> None:
        try:
            resp = httpx.post(API_MUSIC, json=payload, timeout=5.0)
            if resp.status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, "Álbum registrado manualmente.", title="Éxito")
                self.app.call_from_thread(self.load_data)
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Error al guardar.", severity="error")

    # --- EDICIÓN Y ELIMINACIÓN ---
    def action_edit_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return
        table = self.query_one("#music_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.fetch_and_edit_album(row_key)
        except Exception:
            self.app.notify("Selecciona un álbum en la tabla.",
                            severity="warning")

    @work(thread=True)
    def fetch_and_edit_album(self, album_id: str) -> None:
        try:
            resp = httpx.get(f"{API_MUSIC}{album_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.open_edit_modal_sync, resp.json(), album_id)
        except Exception:
            pass

    def open_edit_modal_sync(self, album: dict, album_id: str) -> None:
        def save_changes(payload: dict | None) -> None:
            if payload:
                self.process_edit_album(album_id, payload)
        self.app.push_screen(MusicFullEditModal(album), save_changes)

    @work(thread=True)
    def process_edit_album(self, album_id: str, payload: dict) -> None:
        try:
            resp = httpx.patch(f"{API_MUSIC}{album_id}/",
                               json=payload, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "¡Disco actualizado!", title="Éxito")
                self.app.call_from_thread(self.load_data)
        except Exception:
            pass

    def action_delete_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return
        table = self.query_one("#music_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            title = table.get_row(row_key)[1]

            def handle_confirm(confirm: bool) -> None:
                if confirm:
                    self.execute_delete_album(row_key)
            self.app.push_screen(ConfirmModal(
                f"¿Desechar los registros de '{title}'?"), handle_confirm)
        except Exception:
            self.app.notify("Selecciona un disco.", severity="warning")

    @work(thread=True)
    def execute_delete_album(self, album_id: str) -> None:
        try:
            httpx.delete(f"{API_MUSIC}{album_id}/", timeout=5.0)
            self.app.call_from_thread(
                self.app.notify, "Disco desechado.", title="Éxito")
            self.app.call_from_thread(self.load_data)
        except Exception:
            pass

    # --- INBOX FÍSICO ---
    def action_process_barcode(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_inbox":
            return
        table = self.query_one("#music_inbox_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                barcode = table.get_row(row_key)[1]
                self.app.notify(
                    f"Consultando a Discogs para EAN: {barcode}...", title="Traductor")
                self.process_barcode_api(row_key, barcode)
        except Exception:
            self.app.notify(
                "Selecciona un escaneo de la tabla.", severity="warning")

    @work(thread=True)
    def process_barcode_api(self, inbox_id: str, barcode: str) -> None:
        try:
            resp = httpx.post(API_MUSIC_PROCESS, json={
                              "barcode": barcode}, timeout=15.0)
            if resp.status_code == 201:
                httpx.delete(f"{API_MUSIC_INBOX}{inbox_id}/", timeout=5.0)
                self.app.call_from_thread(
                    self.app.notify, "¡Disco encontrado y guardado!", title="Éxito")
                self.app.call_from_thread(self.load_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error: {resp.json().get('error', 'Desconocido')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    def action_delete_inbox(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_inbox":
            return
        table = self.query_one("#music_inbox_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                httpx.delete(f"{API_MUSIC_INBOX}{row_key}/", timeout=5.0)
                self.app.notify("Escaneo descartado.")
                self.load_data()
        except Exception:
            pass

    # --- ÁRBOL DE DIRECTORIOS ---
    def populate_tree(self, dirs: list) -> None:
        tree = self.query_one("#sidebar", Tree)
        tree.root.expand()
        tree.root.data = "root"
        tree.clear()
        self.all_dirs = dirs

        for d in dirs:
            dir_albums = [a for a in self.all_albums if a.get(
                'directory') == d['id']]
            node_label = f"[{d.get('color_hex', 'magenta')}]■ {d['name']}[/] [dim]({len(dir_albums)})[/dim]"
            dir_node = tree.root.add(node_label, data=d['id'])
            for a in dir_albums:
                status = "✔" if a.get('is_listened') else "✘"
                short_title = a.get('title', '')[
                    :25] + "..." if len(a.get('title', '')) > 25 else a.get('title', '')
                dir_node.add_leaf(
                    f"[dim]{a['id']}[/dim] {short_title} [{status}]", data=f"music_{a['id']}")

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Tree)
        sidebar.toggle_class("-visible")
        if sidebar.has_class("-visible"):
            sidebar.focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is None or str(event.node.data).startswith("music_"):
            return
        data_val = str(event.node.data)

        self.current_dir = data_val
        if data_val == "root":
            filtered = [a for a in self.all_albums if a.get(
                'directory') is None]
        else:
            filtered = [a for a in self.all_albums if str(
                a.get('directory')) == data_val]

        self.populate_albums(filtered)
        self.action_switch_tab("tab_disquera")

    def action_create_dir(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return

        def do_create(payload: dict | None) -> None:
            if payload:
                httpx.post(API_MUSIC_DIRS, json=payload, timeout=5.0)
                self.app.notify(f"Estante '{payload['name']}' construido.")
                self.load_data()
        self.app.push_screen(DirModal(), do_create)

    def action_move_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return
        table = self.query_one("#music_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value

            def do_move(dest_val: str) -> None:
                if dest_val != "cancel":
                    target = None if dest_val == "root" else int(dest_val)
                    httpx.patch(f"{API_MUSIC}{row_key}/",
                                json={"directory": target}, timeout=5.0)
                    self.app.notify("Disco movido.")
                    self.load_data()
            self.app.push_screen(MoveToDirModal(
                getattr(self, 'all_dirs', [])), do_move)
        except Exception:
            pass

    def action_delete_dir(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return

        def do_select(dir_id: str) -> None:
            if dir_id != "cancel" and dir_id is not None:
                def do_confirm(confirm: bool) -> None:
                    if confirm:
                        httpx.delete(f"{API_MUSIC_DIRS}{dir_id}/", timeout=5.0)
                        self.app.notify("Estante destruido.")
                        self.load_data()
                self.app.push_screen(ConfirmModal(
                    "¿Seguro que deseas destruir este estante?"), do_confirm)
        self.app.push_screen(DeleteDirModal(
            getattr(self, 'all_dirs', [])), do_select)

    # --- PRÉSTAMOS ---
    def action_lend_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_disquera":
            return
        table = self.query_one("#music_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value

            def handle_lend(friend_name: str | None) -> None:
                if friend_name:
                    httpx.patch(f"{API_MUSIC}{row_key}/", json={"is_loaned": True,
                                "friend_name": friend_name}, timeout=5.0)
                    self.app.notify("Álbum prestado.")
                    self.load_data()
            self.app.push_screen(LendModal(), handle_lend)
        except Exception:
            pass

    def action_return_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_prestamos":
            return
        table = self.query_one("#music_loans_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            httpx.patch(f"{API_MUSIC}{row_key}/",
                        json={"is_loaned": False, "friend_name": ""}, timeout=5.0)
            self.app.notify("Álbum recuperado.")
            self.load_data()
        except Exception:
            pass

    # --- TRACKER MUSICAL ---
    def action_finish_album(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_tracker":
            return

        def do_finish(payload: dict | None) -> None:
            if payload and payload.get('title'):
                self.process_finish_album(payload)
        self.app.push_screen(FinishMusicModal(), do_finish)

    @work(thread=True)
    def process_finish_album(self, payload: dict) -> None:
        try:
            resp = httpx.post(API_MUSIC_TRACKER_FINISH,
                              json=payload, timeout=5.0)
            if resp.status_code == 201:
                # Actualiza automáticamente si está en el inventario
                album_to_mark = next(
                    (a for a in self.all_albums if a['title'].lower() == payload['title'].lower()), None)
                if album_to_mark:
                    httpx.patch(
                        f"{API_MUSIC}{album_to_mark['id']}/", json={"is_listened": True}, timeout=5.0)
                self.app.call_from_thread(
                    self.app.notify, "¡Sesión musical registrada!", title="Éxito")
                self.app.call_from_thread(self.load_data)
        except Exception:
            pass

    # --- REVERSIÓN DE HÁBITOS (DISQUERA) ---
    def action_log_minutes(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_tracker":
            return
            
        def do_log(payload: dict | None) -> None:
            if payload:
                self.process_log_minutes(payload)
        self.app.push_screen(LogMinutesModal(), do_log)
        
    @work(thread=True)
    def process_log_minutes(self, payload: dict) -> None:
        try:
            resp = httpx.post(API_MUSIC_TRACKER_LOG, json=payload, timeout=5.0)
            if resp.status_code == 201:
                self.app.call_from_thread(self.app.notify, "¡Minutos registrados!", title="Diario de Escucha")
                self.app.call_from_thread(self.load_data)
            else:
                self.app.call_from_thread(self.app.notify, f"Error: {resp.status_code}", severity="error")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error red: {e}", severity="error")

    def action_delete_habit(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_tracker":
            return

        table = self.query_one("#music_annual_table", DataTable)
        try:
            # Obtiene la ID y el título del álbum seleccionado
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            title = table.get_row(row_key)[1]

            def handle_confirm(confirm: bool) -> None:
                if confirm:
                    self.process_delete_habit(row_key)

            self.app.push_screen(ConfirmModal(
                f"¿Revertir la escucha de '{title}'? El álbum volverá a aparecer como pendiente."), handle_confirm)
        except Exception:
            self.app.notify(
                "Selecciona un registro en la tabla de hábitos.", severity="warning")

    @work(thread=True)
    def process_delete_habit(self, record_id: str) -> None:
        try:
            # Utiliza la constante que ya se tiene definida en constants.py
            resp = httpx.delete(
                f"{API_MUSIC_TRACKER_ANNUAL}{record_id}/", timeout=5.0)
            if resp.status_code == 204:
                self.app.call_from_thread(
                    self.app.notify, "Registro de escucha eliminado.", title="Historial Limpio")
                # Recarga inventario y hábitos
                self.app.call_from_thread(self.load_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, "No se pudo revertir el registro.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de conexión: {e}", severity="error")

    # --- RADAR MUSICAL (SCRAPER / WISHLIST) ---
    def action_sync_scraper(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_wishlist":
            return
        self.app.push_screen(SyncConsoleModal(service_name="scraper-music"))

    def action_add_watcher(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_wishlist":
            return

        def do_watch(keyword: str | None) -> None:
            if keyword:
                httpx.post(API_MUSIC_WATCHERS, json={
                           "keyword": keyword, "is_active": True}, timeout=5.0)
                self.app.notify(f"Vigilando: {keyword}")
        self.app.push_screen(WatcherModal(
            "Vigilar Artista/Sello", "Ej: Pink Floyd"), do_watch)

    def action_view_watchers(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_wishlist":
            return
        try:
            watchers = httpx.get(API_MUSIC_WATCHERS, timeout=5.0).json()

            def do_delete_watcher(w_id: int | None) -> None:
                if w_id:
                    httpx.delete(f"{API_MUSIC_WATCHERS}{w_id}/", timeout=5.0)
                    self.app.notify("Objetivo eliminado del radar.")
            self.app.push_screen(WatchersListModal(
                watchers), do_delete_watcher)
        except Exception:
            pass

    def action_delete_wishlist(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_wishlist":
            return
        table = self.query_one("#music_wishlist_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value

            def check_delete(confirm: bool | None) -> None:
                if confirm:
                    httpx.patch(f"{API_MUSIC_WISHLIST}{row_key}/",
                                json={"is_rejected": True}, timeout=5.0)
                    self.app.notify("Lanzamiento oculto.")
                    self.load_data()
            self.app.push_screen(ConfirmModal(
                "¿Añadir a la lista negra del scraper?"), check_delete)
        except Exception:
            pass

    def action_clear_wishlist(self) -> None:
        if self.query_one("#music_tabs", TabbedContent).active != "tab_wishlist":
            return

        def do_clear(confirm: bool | None) -> None:
            if confirm:
                items = httpx.get(API_MUSIC_WISHLIST, timeout=5.0).json()
                for item in items:
                    httpx.patch(
                        f"{API_MUSIC_WISHLIST}{item['id']}/", json={"is_rejected": True}, timeout=5.0)
                self.app.notify(f"Limpieza completa.")
                self.load_data()
        self.app.push_screen(ConfirmModal(
            "¿Ocultar TODOS los lanzamientos del tablón?"), do_clear)
