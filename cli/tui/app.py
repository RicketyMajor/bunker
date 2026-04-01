import httpx
import datetime
import webbrowser
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, TabbedContent, Tree
from textual.binding import Binding
from .tabs import InventoryTab, InboxTab, LoansTab, TrackerTab, WishlistTab
from textual import work
from .constants import *
from .screens import BookDetailsScreen
from .modals import IsbnModal, FullEditModal, LendModal, DirModal, SyncConsoleModal, WatcherModal, LogPagesModal, ConfirmModal, AddMenuModal, ManualAddModal, ScannerModal, FinishBookModal, WatchersListModal, MoveToDirModal


class NeoLibraryApp(App):
    all_books = []

    CSS = """
    Screen { background: $surface-darken-1; }
    DataTable { height: 1fr; margin: 1 2; }
    #details_container { margin: 2 4; padding: 1 2; border: heavy $accent; background: $surface; }

    #sidebar {
        dock: left; width: 35; height: 100%;
        background: $surface-darken-2; border-right: vkey $background;
        display: none;
    }
    #sidebar.-visible { display: block; }
    
    IsbnModal, FullEditModal, LendModal, DirModal, SyncConsoleModal, WatcherModal, LogPagesModal, ConfirmModal { align: center middle; }
    #isbn_dialog { width: 40; height: 15; padding: 1 2; border: heavy $accent; background: $surface; }
    #full_edit_dialog { width: 80; height: 90%; padding: 1 2; border: heavy $warning; background: $surface; } 
    .edit_label { text-style: bold; margin-top: 1; color: $text-muted; }
    #lend_dialog { width: 40; height: 15; padding: 1 2; border: heavy $success; background: $surface; }
    #dir_dialog { width: 40; height: 17; padding: 1 2; border: heavy $accent; background: $surface; }
    .modal_title { text-style: bold; margin-bottom: 1; }
    .form_buttons { height: auto; margin-top: 1; align: center middle; }

    Button { margin: 0 1; }
    #tracker_content { height: auto; margin: 1 2 0 2; padding: 1; border: solid $success; background: $surface; }
    #annual_table { height: 1fr; margin: 0 2 1 2; }
    #sync_dialog { width: 80%; height: 80%; padding: 1 2; border: heavy $success; background: $surface; }
    #watcher_dialog, #pages_dialog { width: 40; height: 15; padding: 1 2; border: heavy $accent; background: $surface; }
    #sync_log { height: 1fr; border: solid $primary; background: #0c0c0c; }

    AddMenuModal, ManualAddModal { align: center middle; }
    #add_menu_dialog { width: 40; height: auto; padding: 1 2; border: heavy $accent; background: $surface; }
    #add_menu_dialog Button { width: 100%; margin-bottom: 1; }

    ScannerModal { align: center middle; }
    #scanner_dialog { width: 50; height: 35; padding: 1 2; border: heavy $success; background: $surface; }
    #scanner_qr { height: 1fr; background: #000000; color: #ffffff; text-align: center; } 

    FinishBookModal, WatchersListModal { align: center middle; }
    #finish_dialog { width: 50; height: 22; padding: 1 2; border: heavy $warning; background: $surface; }
    #watchers_list_dialog { width: 80; height: 25; padding: 1 2; border: heavy $accent; background: $surface; }
    #watchers_scroll { height: 1fr; border: solid $primary; padding: 1; margin-bottom: 1; }

    MoveToDirModal { align: center middle; }
    #move_dir_dialog { width: 50; height: 22; padding: 1 2; border: heavy $accent; background: $surface; content-align: center middle;}
    """

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("ctrl+b", "toggle_sidebar", "Explorador"),
        ("ctrl+t", "toggle_dark", "Tema"),
        Binding("1", "switch_tab('tab_library')",
                "1-5 Cambiar Pestañas", show=True),
        Binding("2", "switch_tab('tab_inbox')", "Inbox", show=False),
        Binding("3", "switch_tab('tab_loans')", "Préstamos", show=False),
        Binding("4", "switch_tab('tab_tracker')", "Hábitos", show=False),
        Binding("5", "switch_tab('tab_wishlist')", "Tablón", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Tree("📁 Raíz de la Biblioteca", id="sidebar")
        with TabbedContent(initial="tab_library", id="main_tabs"):
            yield InventoryTab("▤ Inventario", id="tab_library")
            yield InboxTab("◈ Inbox", id="tab_inbox")
            yield LoansTab("⇋ Préstamos", id="tab_loans")
            yield TrackerTab("∑ Hábitos", id="tab_tracker")
            yield WishlistTab("★ Tablón", id="tab_wishlist")
        yield Footer()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Cambia el foco automáticamente al contenido de la pestaña activa para actualizar los Atajos del Footer."""
        for widget in event.pane.query("*"):
            if isinstance(widget, (DataTable, Markdown)):
                widget.focus()
                break

    def on_mount(self) -> None:
        t_books = self.query_one("#books_table", DataTable)
        t_books.cursor_type = "row"
        t_books.zebra_stripes = True
        t_books.add_columns("ID", "Título", "Autor",
                            "Formato", "Editorial", "Estado")

        t_inbox = self.query_one("#inbox_table", DataTable)
        t_inbox.cursor_type = "row"
        t_inbox.zebra_stripes = True
        t_inbox.add_columns("ID", "ISBN", "Fecha de Escaneo")

        t_loans = self.query_one("#loans_table", DataTable)
        t_loans.cursor_type = "row"
        t_loans.zebra_stripes = True
        t_loans.add_columns("Libro", "Amigo", "Fecha Préstamo",
                            "Vencimiento", "Devuelto")

        t_wishlist = self.query_one("#wishlist_table", DataTable)
        t_wishlist.cursor_type = "row"
        t_wishlist.zebra_stripes = True
        t_wishlist.add_columns("ID", "Título", "Editorial", "Precio", "Fecha")

        t_annual = self.query_one("#annual_table", DataTable)
        t_annual.cursor_type = "row"
        t_annual.zebra_stripes = True
        t_annual.add_columns("ID", "Título", "Autor", "Propiedad", "Terminado")

        self.load_all_data()

    @work(thread=True)
    def load_all_data(self) -> None:
        try:
            books = httpx.get(API_LIBRARY, timeout=5.0).json()
            dirs = httpx.get(API_DIRECTORIES, timeout=5.0).json()
            if isinstance(books, list):
                self.all_books = books
                orphan = [b for b in books if b.get('directory') is None]
                self.app.call_from_thread(self.populate_books, orphan)
                self.app.call_from_thread(self.populate_tree, dirs)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error en Inventario: {e}", severity="error")

        try:
            inbox = httpx.get(API_INBOX, timeout=5.0).json()
            if isinstance(inbox, list):
                self.app.call_from_thread(self.populate_inbox, inbox)
        except Exception:
            pass

        try:
            loans = httpx.get(API_LOANS, timeout=5.0).json()
            if isinstance(loans, list):
                self.app.call_from_thread(self.populate_loans, loans)
        except Exception:
            pass

        try:
            tracker = httpx.get(API_TRACKER, timeout=5.0).json()
            if isinstance(tracker, dict):
                self.app.call_from_thread(self.populate_tracker, tracker)
        except Exception:
            pass

        try:
            wishlist = httpx.get(API_WISHLIST, timeout=5.0).json()
            if isinstance(wishlist, list):
                self.app.call_from_thread(self.populate_wishlist, wishlist)
        except Exception:
            pass

        # Cargar Hábitos y Registro Anual
        try:
            tracker = httpx.get(API_TRACKER, timeout=5.0).json()
            annual = httpx.get(API_TRACKER_ANNUAL, timeout=5.0).json()
            if isinstance(tracker, dict):
                self.app.call_from_thread(
                    self.populate_tracker, tracker, annual)
        except Exception:
            pass

    def populate_wishlist(self, items: list) -> None:
        table = self.query_one("#wishlist_table", DataTable)
        table.clear()
        for item in items:
            date_str = item.get('date_found', '')[:10]
            table.add_row(
                str(item.get('id')), item.get('title', '').upper(),
                item.get('publisher') or "-", item.get('price') or "-",
                date_str, key=str(item.get('id'))
            )

    def populate_tree(self, dirs: list) -> None:
        tree = self.query_one("#sidebar", Tree)
        tree.root.expand()
        tree.root.data = "root"
        tree.clear()

        self.all_dirs = dirs  # Guarda en memoria para usarlo luego al Mover

        for d in dirs:
            dir_books = [b for b in self.all_books if b.get(
                'directory') == d['id']]
            count = len(dir_books)
            node_label = f"[{d.get('color_hex', 'cyan')}]■ {d['name']}[/] [dim]({count})[/dim]"

            # Añade la carpeta
            dir_node = tree.root.add(node_label, data=d['id'])

            # Añade los libros como "Hojas" dentro de la carpeta
            for b in dir_books:
                status = "✔" if b.get('is_read') else "✘"
                # Formato: "ID - Título [Estado]"
                title_short = b['title'][:25] + \
                    "..." if len(b['title']) > 25 else b['title']
                dir_node.add_leaf(
                    f"[dim]{b['id']}[/dim] {title_short} [{status}]", data=f"book_{b['id']}")

    def populate_books(self, books: list) -> None:
        table = self.query_one("#books_table", DataTable)
        table.clear()
        for book in books:
            status = "✔ Leído" if book.get('is_read') else "✘ Pendiente"
            row_key = str(book.get('id'))
            table.add_row(
                str(book.get('id')), book.get('title', 'Sin título').upper(),
                book.get('author_name', 'Desconocido'), book.get(
                    'format_type', '-'),
                book.get('publisher') or '-', status, key=row_key
            )

    def populate_inbox(self, items: list) -> None:
        table = self.query_one("#inbox_table", DataTable)
        table.clear()
        for item in items:
            table.add_row(str(item.get('id')), item.get('isbn'), item.get(
                'date_scanned', '')[:10], key=str(item.get('id')))

    def populate_loans(self, loans: list) -> None:
        table = self.query_one("#loans_table", DataTable)
        table.clear()
        for loan in loans:
            status = "✔ Sí" if loan.get('returned') else "✘ No"
            table.add_row(loan.get('book_title', '-'), loan.get('friend_name', '-'), loan.get(
                'loan_date', ''), loan.get('due_date', ''), status, key=str(loan.get('id')))

    def populate_tracker(self, stats: dict, annual: list) -> None:
        md = self.query_one("#tracker_content", Markdown)

        # El conteo de obras terminadas ahora es el largo de la lista anual
        obras_anuales = len(annual)

        # Muestra la info de forma horizontal
        text = f"""**Mes de {stats.get('current_month', '')}:** Páginas: `{stats.get('pages_this_month', 0)}`  |  **Total Año:** `{obras_anuales} obras terminadas`"""
        md.update(text)

        # Actualización de la tabla
        table = self.query_one("#annual_table", DataTable)
        table.clear()
        for rec in annual:
            owned_str = "✔ Estantería" if rec.get('is_owned') else "⇋ Externo"
            table.add_row(
                str(rec.get('id')),
                rec.get('title', '').upper(),
                rec.get('author_name', 'Desconocido'),
                owned_str,
                rec.get('date_finished', '')[:10],
                key=str(rec.get('id'))
            )

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        event.control.sort(event.column_key)

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#main_tabs", TabbedContent).active = tab_id

    def action_show_details(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            return
        table = self.query_one("#books_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.push_screen(BookDetailsScreen(book_id=row_key))
        except Exception:
            pass

    # ================= ADQUISICIONES =================
    def action_add_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            return

        # Callback del menú principal
        def handle_menu_choice(choice: str | None) -> None:
            if choice == "scan":
                # Lanzam el modal del Escáner SSH
                self.push_screen(ScannerModal())
            elif choice == "isbn":
                self.push_screen(IsbnModal(), self.handle_isbn_input)
            elif choice == "manual":
                self.push_screen(ManualAddModal(), self.handle_manual_input)

        self.push_screen(AddMenuModal(), handle_menu_choice)

    # Camino 1: ISBN
    def handle_isbn_input(self, isbn: str | None) -> None:
        if isbn:
            self.notify(
                f"Buscando oráculos globales para {isbn}...", title="Escáner")
            self.process_isbn_add(isbn)

    # Camino 2: Ingreso Manual
    def handle_manual_input(self, payload: dict | None) -> None:
        if payload and payload.get("title"):  # Validación básica
            self.notify("Guardando ingreso manual en el servidor...")
            self.process_manual_add(payload)
        elif payload:
            self.notify("El Título de la obra es obligatorio.",
                        severity="error")

    @work(thread=True)
    def process_manual_add(self, payload: dict) -> None:
        try:
            resp = httpx.post(API_LIBRARY, json=payload, timeout=5.0)
            if resp.status_code == 201:
                self.app.call_from_thread(
                    self.notify, "¡Obra registrada magistralmente!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
            else:
                self.app.call_from_thread(
                    self.notify, f"Error: {resp.text}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error de red: {e}", severity="error")

    @work(thread=True)
    def process_isbn_add(self, isbn: str) -> None:
        try:
            resp = httpx.post(API_SCAN, json={"isbn": isbn}, timeout=10.0)
            if resp.status_code in [200, 201]:
                self.app.call_from_thread(
                    self.notify, "¡Libro registrado exitosamente!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
            else:
                self.app.call_from_thread(
                    self.notify, f"Error: {resp.json().get('error', 'Desconocido')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error de red: {e}", severity="error")

    def action_edit_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            self.notify(
                "La edición solo está disponible en el Inventario.", severity="warning")
            return
        table = self.query_one("#books_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.notify("Descargando ficha de edición...", timeout=1)
                self.fetch_and_edit(row_key)
        except Exception:
            self.notify("Selecciona un libro en la tabla primero.",
                        severity="warning")

    @work(thread=True)
    def fetch_and_edit(self, book_id: str) -> None:
        try:
            resp = httpx.get(f"{API_LIBRARY}{book_id}/", timeout=5.0)
            if resp.status_code == 200:
                book = resp.json()
                self.app.call_from_thread(
                    self.open_edit_modal_sync, book, book_id)
        except Exception:
            self.app.call_from_thread(
                self.notify, "Error al obtener datos.", severity="error")

    # ================= EDITAR FICHA =================
    # Cambia tu open_edit_modal_sync para usar el nuevo FullEditModal
    def open_edit_modal_sync(self, book: dict, book_id: str) -> None:
        def save_changes(payload: dict | None) -> None:
            if payload:
                self.notify("Guardando cambios en el servidor...")
                self.process_edit(book_id, payload)
        self.push_screen(FullEditModal(book), save_changes)

    @work(thread=True)
    def process_edit(self, book_id: str, payload: dict) -> None:
        try:
            resp = httpx.patch(f"{API_LIBRARY}{book_id}/",
                               json=payload, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.notify, "¡Ficha actualizada!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
            else:
                self.app.call_from_thread(
                    self.notify, "Error al actualizar.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.notify, "Error de red.", severity="error")

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Tree)
        sidebar.toggle_class("-visible")
        if sidebar.has_class("-visible"):
            sidebar.focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is None:
            return

        data_val = str(event.node.data)
        # Si el usuario hace clic en un archivo, ignora el evento de filtro
        if data_val.startswith("book_"):
            return

        if data_val == "root":
            filtered_books = [
                b for b in self.all_books if b.get('directory') is None]
        else:
            filtered_books = [b for b in self.all_books if str(
                b.get('directory')) == data_val]

        self.populate_books(filtered_books)
        self.action_switch_tab("tab_library")

    # ================= PRÉSTAMOS =================
    def action_lend_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            return
        table = self.query_one("#books_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                def do_lend(friend_name: str | None) -> None:
                    if friend_name:
                        self.process_lend(row_key, friend_name)
                self.push_screen(LendModal(), do_lend)
        except Exception:
            self.notify("Selecciona un libro.", severity="warning")

    @work(thread=True)
    def process_lend(self, book_id: str, friend_name: str) -> None:
        try:
            f_resp = httpx.get(API_FRIENDS, timeout=5.0).json()
            friend_id = next(
                (f['id'] for f in f_resp if f['name'].lower() == friend_name.lower()), None)
            if not friend_id:
                friend_id = httpx.post(
                    API_FRIENDS, json={"name": friend_name}, timeout=5.0).json()['id']

            loan_payload = {"book": int(book_id), "friend": friend_id,
                            "loan_date": datetime.datetime.now().strftime("%Y-%m-%d")}
            if httpx.post(API_LOANS, json=loan_payload, timeout=5.0).status_code == 201:
                httpx.patch(f"{API_LIBRARY}{book_id}/",
                            json={"is_loaned": True}, timeout=5.0)
                self.app.call_from_thread(
                    self.notify, f"¡Prestado a {friend_name}!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    def action_return_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_loans":
            return
        table = self.query_one("#loans_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.process_return(row_key)
        except Exception:
            self.notify("Selecciona un préstamo activo.", severity="warning")

    @work(thread=True)
    def process_return(self, loan_id: str) -> None:
        try:
            book_id = httpx.get(f"{API_LOANS}{loan_id}/",
                                timeout=5.0).json().get('book')
            if httpx.delete(f"{API_LOANS}{loan_id}/", timeout=5.0).status_code == 204:
                httpx.patch(f"{API_LIBRARY}{book_id}/",
                            json={"is_loaned": False}, timeout=5.0)
                self.app.call_from_thread(
                    self.notify, "¡Libro devuelto a la estantería!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    # ================= DIRECTORIOS =================
    def action_create_dir(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            return

        def do_create(payload: dict | None) -> None:
            if payload:
                self.process_create_dir(payload)
        self.push_screen(DirModal(), do_create)

    @work(thread=True)
    def process_create_dir(self, payload: dict) -> None:
        try:
            if httpx.post(API_DIRECTORIES, json=payload, timeout=5.0).status_code == 201:
                self.app.call_from_thread(
                    self.notify, f"Directorio '{payload['name']}' creado", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

# ================= INBOX =================
    def action_process_inbox(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_inbox":
            return
        table = self.query_one("#inbox_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                # Se Usa la tabla para extraer el ISBN sin pedirlo de nuevo
                isbn = table.get_row(row_key)[1]
                self.notify(f"Procesando ISBN: {isbn}...")
                self.process_inbox_item(row_key, isbn)
        except Exception:
            self.notify("Selecciona un escaneo de la tabla.",
                        severity="warning")

    @work(thread=True)
    def process_inbox_item(self, inbox_id: str, isbn: str) -> None:
        try:
            resp = httpx.post(API_SCAN, json={"isbn": isbn}, timeout=10.0)
            if resp.status_code in [200, 201]:
                httpx.delete(f"{API_INBOX}{inbox_id}/", timeout=5.0)
                self.app.call_from_thread(
                    self.notify, "¡Procesado y guardado en Inventario!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
            else:
                self.app.call_from_thread(
                    self.notify, f"Error: {resp.json().get('error')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    # ================= TRACKER =================
    def action_log_pages(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_tracker":
            return

        def do_log(pages: int | None) -> None:
            if pages:
                self.process_log_pages(pages)
        self.push_screen(LogPagesModal(), do_log)

    @work(thread=True)
    def process_log_pages(self, pages: int) -> None:
        try:
            if httpx.post(API_TRACKER_PAGES, json={"pages": pages}, timeout=5.0).status_code == 201:
                self.app.call_from_thread(
                    self.notify, f"{pages} páginas anotadas.", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    # ================= TRACKER: TERMINAR LIBRO =================
    def action_finish_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_tracker":
            return

        def do_finish(payload: dict | None) -> None:
            if payload and payload.get('title'):
                self.process_finish_book(payload)
        self.push_screen(FinishBookModal(), do_finish)

    @work(thread=True)
    def process_finish_book(self, payload: dict) -> None:
        try:
            # 1. Registramos en el Tracker
            resp = httpx.post(API_TRACKER_FINISH, json=payload, timeout=5.0)
            if resp.status_code == 201:
                # 2. TRANSACCIÓN DISTRIBUIDA: Buscamos si el libro existe en Inventario
                lib_resp = httpx.get(API_LIBRARY, params={
                                     "title": payload['title']}, timeout=5.0)
                if lib_resp.status_code == 200 and lib_resp.json():
                    book_id = lib_resp.json()[0]['id']
                    # 3. Lo marcamos como leído automáticamente!
                    httpx.patch(f"{API_LIBRARY}{book_id}/",
                                json={"is_read": True}, timeout=5.0)

                self.app.call_from_thread(
                    self.notify, "¡Victoria Registrada y Sincronizada!", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    # ================= WISHLIST: GESTIÓN AVANZADA =================
    def action_view_watchers(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_wishlist":
            return
        self.notify("Consultando base de datos...", timeout=1)
        self.fetch_and_show_watchers()

    @work(thread=True)
    def fetch_and_show_watchers(self) -> None:
        try:
            watchers = httpx.get(API_WATCHERS, timeout=5.0).json()

            def do_delete_watcher(w_id: int | None) -> None:
                if w_id:
                    self.process_delete_watcher(w_id)
            self.app.call_from_thread(
                self.push_screen, WatchersListModal(watchers), do_delete_watcher)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    @work(thread=True)
    def process_delete_watcher(self, watcher_id: int) -> None:
        try:
            if httpx.delete(f"{API_WATCHERS}{watcher_id}/", timeout=5.0).status_code == 204:
                self.app.call_from_thread(
                    self.notify, "Autor eliminado del radar.", title="Éxito")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    def action_clear_wishlist(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_wishlist":
            return

        def do_clear(confirm: bool | None) -> None:
            if confirm:
                self.process_clear_wishlist()
        self.push_screen(ConfirmModal(
            "¿Ocultar TODOS los libros del tablón actual?"), do_clear)

    @work(thread=True)
    def process_clear_wishlist(self) -> None:
        try:
            items = httpx.get(API_WISHLIST, timeout=5.0).json()
            for item in items:
                httpx.patch(
                    f"{API_WISHLIST}{item['id']}/", json={"is_rejected": True}, timeout=5.0)
            self.app.call_from_thread(
                self.notify, f"{len(items)} libros enviados a la lista negra.", title="Limpieza")
            self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    # ================= WISHLIST & SCRAPER =================
    def action_sync_scraper(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_wishlist":
            return
        # 🚀 Abre la consola de Matrix
        self.push_screen(SyncConsoleModal())

    def action_add_watcher(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_wishlist":
            return

        def do_watch(keyword: str | None) -> None:
            if keyword:
                self.process_add_watcher(keyword)
        self.push_screen(WatcherModal(), do_watch)

    @work(thread=True)
    def process_add_watcher(self, keyword: str) -> None:
        try:
            if httpx.post(API_WATCHERS, json={"keyword": keyword, "is_active": True}, timeout=5.0).status_code == 201:
                self.app.call_from_thread(
                    self.notify, f"Vigilando: {keyword}", title="Scraper")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    def action_wishlist_details(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_wishlist":
            return
        table = self.query_one("#wishlist_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.process_wishlist_link(row_key)
        except Exception:
            self.notify("Selecciona un lanzamiento.", severity="warning")

    @work(thread=True)
    def process_wishlist_link(self, item_id: str) -> None:
        try:
            resp = httpx.get(f"{API_WISHLIST}{item_id}/", timeout=5.0)
            if resp.status_code == 200:
                url = resp.json().get('buy_url')
                if url:
                    # Lanza el navegador de tu sistema operativo nativamente
                    webbrowser.open(url)
                    self.app.call_from_thread(
                        self.notify, "Abriendo enlace en tu navegador...")
                else:
                    self.app.call_from_thread(
                        self.notify, "No hay enlace disponible.")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

# ================= MOTOR DE ELIMINACIÓN GLOBAL =================

    def action_delete_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            return
        table = self.query_one("#books_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            title = table.get_row(row_key)[1]
            if row_key:
                def check_delete(confirm: bool | None) -> None:
                    if confirm:
                        self.process_delete_book(row_key)
                self.push_screen(ConfirmModal(
                    f"¿Eliminar permanentemente '{title}'?"), check_delete)
        except Exception:
            self.notify("Selecciona un libro primero.", severity="warning")

    @work(thread=True)
    def process_delete_book(self, book_id: str) -> None:
        try:
            if httpx.delete(f"{API_LIBRARY}{book_id}/", timeout=5.0).status_code == 204:
                self.app.call_from_thread(
                    self.notify, "Libro borrado del servidor.", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    def action_delete_inbox(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_inbox":
            return
        table = self.query_one("#inbox_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                def check_delete(confirm: bool | None) -> None:
                    if confirm:
                        self.process_delete_inbox(row_key)
                self.push_screen(ConfirmModal(
                    "¿Descartar este escaneo defectuoso?"), check_delete)
        except Exception:
            self.notify("Selecciona un escaneo.", severity="warning")

    @work(thread=True)
    def process_delete_inbox(self, inbox_id: str) -> None:
        try:
            if httpx.delete(f"{API_INBOX}{inbox_id}/", timeout=5.0).status_code == 204:
                self.app.call_from_thread(
                    self.notify, "Escaneo descartado.", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    def action_delete_wishlist(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_wishlist":
            return
        table = self.query_one("#wishlist_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                def check_delete(confirm: bool | None) -> None:
                    if confirm:
                        self.process_delete_wishlist(row_key)
                self.push_screen(ConfirmModal(
                    "¿Añadir a la lista negra del scraper?"), check_delete)
        except Exception:
            self.notify("Selecciona un lanzamiento.", severity="warning")

    @work(thread=True)
    def process_delete_wishlist(self, item_id: str) -> None:
        try:
            # Usa PATCH para el Soft Delete
            if httpx.patch(f"{API_WISHLIST}{item_id}/", json={"is_rejected": True}, timeout=5.0).status_code == 200:
                self.app.call_from_thread(
                    self.notify, "Lanzamiento oculto para siempre.", title="Éxito")
                self.app.call_from_thread(self.load_all_data)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

# ================= TRANSFERENCIA ENTRE DIRECTORIOS =================
    def action_move_book(self) -> None:
        if self.query_one("#main_tabs", TabbedContent).active != "tab_library":
            return
        table = self.query_one("#books_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                def do_move(dest_val: str) -> None:
                    if dest_val != "cancel":
                        target_id = None if dest_val == "root" else int(
                            dest_val)
                        self.process_move_book(row_key, target_id)

                # Le pasa la lista de directorios almacenada en memoria
                self.push_screen(MoveToDirModal(
                    getattr(self, 'all_dirs', [])), do_move)
        except Exception:
            self.notify("Selecciona un libro en la tabla.", severity="warning")

    @work(thread=True)
    def process_move_book(self, book_id: str, dest_dir: int | None) -> None:
        try:
            resp = httpx.patch(f"{API_LIBRARY}{book_id}/",
                               json={"directory": dest_dir}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.notify, "¡Libro transferido de carpeta!", title="Éxito")
                # Refresca el árbol visualmente
                self.app.call_from_thread(self.load_all_data)
            else:
                self.app.call_from_thread(
                    self.notify, "Error al transferir.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")
