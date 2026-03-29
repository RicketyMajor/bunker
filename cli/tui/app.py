import httpx
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, TabbedContent, Tree
from .tabs import InventoryTab, InboxTab, LoansTab, TrackerTab, WishlistTab
from textual import work
from .constants import *
from .screens import BookDetailsScreen
from .modals import IsbnModal, QuickEditModal


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
    
    IsbnModal, QuickEditModal { align: center middle; }
    #isbn_dialog { width: 40; height: 15; padding: 1 2; border: heavy $accent; background: $surface; }
    #edit_dialog { width: 50; height: 23; padding: 1 2; border: heavy $warning; background: $surface; }
    .modal_title { text-style: bold; margin-bottom: 1; }
    .form_buttons { height: auto; margin-top: 1; align: center middle; }
    Button { margin: 0 1; }
    #tracker_content { height: auto; margin: 1 2; padding: 0 1; border-left: thick $success; background: $surface; }
    #annual_table { height: 1fr; margin: 0 2 1 2; }
    """

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("ctrl+b", "toggle_sidebar", "Explorador"),
        ("a", "add_book", "Añadir (ISBN)"),
        ("e", "edit_book", "Editar Ficha"),
        ("d", "show_details", "Ver Detalles"),
        ("1", "switch_tab('tab_library')", "Inv"),
        ("2", "switch_tab('tab_inbox')", "Inbox"),
        ("3", "switch_tab('tab_loans')", "Préstamos"),
        ("4", "switch_tab('tab_tracker')", "Hábitos"),
        ("5", "switch_tab('tab_wishlist')", "Tablón"),
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

        # Configurar Tabla 6: Registro Anual (Hábitos)
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

        for d in dirs:
            count = sum(1 for b in self.all_books if b.get(
                'directory') == d['id'])
            node_label = f"[{d.get('color_hex', 'cyan')}]■ {d['name']}[/] [dim]({count})[/dim]"
            tree.root.add(node_label, data=d['id'])

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
        # 1. Panel de Markdown superior
        md = self.query_one("#tracker_content", Markdown)
        text = f"""
# ∑ Hábitos de Lectura ({stats.get('current_month', 'Mes')} {stats.get('current_year', '')})
---
* **Páginas leídas este mes:** `{stats.get('pages_this_month', 0)}`
* **Libros terminados este mes:** `{stats.get('books_this_month', 0)}`
"""
        md.update(text)

        # 2. Tabla Anual inferior
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

    def action_add_book(self) -> None:
        def check_isbn(isbn: str | None) -> None:
            if isbn:
                self.notify(
                    f"Buscando oráculos globales para {isbn}...", title="Escáner")
                self.process_isbn_add(isbn)
        self.push_screen(IsbnModal(), check_isbn)

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

    def open_edit_modal_sync(self, book: dict, book_id: str) -> None:
        def save_changes(payload: dict | None) -> None:
            if payload:
                self.notify("Guardando cambios en el servidor...")
                self.process_edit(book_id, payload)
        self.push_screen(QuickEditModal(book), save_changes)

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
        dir_id = event.node.data
        if dir_id == "root":
            filtered_books = [
                b for b in self.all_books if b.get('directory') is None]
            self.notify("Mostrando raíz (Archivos sin agrupar)")
        else:
            filtered_books = [
                b for b in self.all_books if b.get('directory') == dir_id]
            self.notify(f"Universo filtrado ({len(filtered_books)} obras)")
        self.populate_books(filtered_books)
        self.action_switch_tab("tab_library")

    def action_process_inbox(self): self.notify(
        "Próximamente: Procesar Escaneos (Fase 47)")

    def action_lend_book(self): self.notify(
        "Próximamente: Prestar Libro (Fase 47)")

    def action_return_book(self): self.notify(
        "Próximamente: Devolver Libro (Fase 47)")

    def action_log_pages(self): self.notify(
        "Próximamente: Anotar Páginas (Fase 47)")

    def action_finish_book(self): self.notify(
        "Próximamente: Registrar Terminado (Fase 47)")

    def action_sync_scraper(self): self.notify(
        "Próximamente: Despertar Scraper (Fase 48)")

    def action_add_watcher(self): self.notify(
        "Próximamente: Vigilar Autor (Fase 48)")

    def action_wishlist_details(self): self.notify(
        "Próximamente: Enlace Wishlist (Fase 48)")
