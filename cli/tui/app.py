import httpx
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Static, Markdown
from textual.containers import VerticalScroll
from textual import work

API_LIBRARY = "http://localhost:8000/api/books/library/"

# ==============================================================================
# 📄 PANTALLA SECUNDARIA: DETALLES DEL LIBRO
# ==============================================================================


class BookDetailsScreen(Screen):
    """Pantalla superpuesta que muestra los detalles completos de un libro."""

    # Atajos exclusivos de esta pantalla
    BINDINGS = [
        ("escape, b, left", "go_back", "Volver a la Tabla"),
        ("q", "app.quit", "Salir de la Biblioteca")
    ]

    def __init__(self, book_id: str, **kwargs):
        super().__init__(**kwargs)
        self.book_id = book_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # Usamos VerticalScroll para que la sinopsis pueda bajar si es muy larga
        with VerticalScroll(id="details_container"):
            yield Markdown("Cargando los archivos de la base de datos...", id="details_content")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_details()

    @work(thread=True)
    def fetch_details(self) -> None:
        """Petición asíncrona para obtener el perfil completo del libro."""
        try:
            resp = httpx.get(f"{API_LIBRARY}{self.book_id}/", timeout=5.0)
            if resp.status_code == 200:
                book = resp.json()
                self.app.call_from_thread(self.render_details, book)
            else:
                self.app.call_from_thread(
                    self.show_error, f"Error {resp.status_code} al buscar el libro.")
        except Exception as e:
            self.app.call_from_thread(self.show_error, f"Error de red: {e}")

    def render_details(self, book: dict) -> None:
        """Genera el contenido visual en formato Markdown para aprovechar Textual."""
        content = self.query_one("#details_content", Markdown)

        generos_str = ", ".join(book.get('genre_list', [])) if book.get(
            'genre_list') else "Sin clasificar"
        estado = "✔ Leído" if book.get('is_read') else "✘ Pendiente"
        ubicacion = "⇋ Prestado" if book.get(
            'is_loaned') else "❖ En Estantería"

        # Construimos el Markdown dinámico
        md_text = f"""
# {book.get('title', 'Sin Título').upper()}
{f"*{book.get('subtitle')}*" if book.get('subtitle') else ""}

**Autor:** {book.get('author_name', 'Desconocido')}
**Editorial:** {book.get('publisher') or '-'} | **Formato:** {book.get('format_type', '-')} | **Géneros:** {generos_str}
**Páginas:** {book.get('page_count') or '-'} | **Publicación:** {book.get('publish_date') or '-'}

---

### ⌖ Estado Físico
* **Lectura:** {estado}
* **Ubicación:** {ubicacion}

"""
        # Inyectamos detalles extra si existen (Ej: Tomos de manga)
        details = book.get('details', {})
        if details:
            md_text += "### ◈ Detalles Adicionales\n"
            for k, v in details.items():
                if isinstance(v, list):
                    v = ", ".join(v)
                md_text += f"* **{k.replace('_', ' ').title()}:** {v}\n"

        # Inyectamos la sinopsis
        desc = book.get('description')
        if desc:
            md_text += f"\n### Sinopsis\n{desc}"

        # Actualizamos el widget en pantalla
        content.update(md_text)

    def show_error(self, message: str) -> None:
        content = self.query_one("#details_content", Markdown)
        content.update(f"### ❌ Error\n{message}")

    def action_go_back(self) -> None:
        """Destruye esta pantalla y revela la que estaba debajo."""
        self.app.pop_screen()


# ==============================================================================
# 🏠 PANTALLA PRINCIPAL: EL INVENTARIO
# ==============================================================================
class NeoLibraryApp(App):
    """El nuevo entorno inmersivo TUI de tu biblioteca."""

    CSS = """
    Screen {
        background: $surface-darken-1;
    }
    DataTable {
        height: 100%;
        margin: 1 2;
    }
    #details_container {
        margin: 2 4;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    """

    BINDINGS = [
        ("q", "quit", "Salir de la Biblioteca"),
        ("d", "show_details", "Ver Detalles"),  # NUEVO ATAJO
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(id="books_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("ID", "Título", "Autor",
                          "Formato", "Editorial", "Estado")
        self.load_books()

    @work(thread=True)
    def load_books(self) -> None:
        try:
            resp = httpx.get(API_LIBRARY, timeout=5.0)
            books = resp.json()
            orphan_books = [b for b in books if b.get('directory') is None]
            self.call_from_thread(self.populate_table, orphan_books)
        except Exception:
            pass

    def populate_table(self, books: list) -> None:
        table = self.query_one(DataTable)
        table.clear()

        for book in books:
            status = "✔ Leído" if book.get('is_read') else "✘ Pendiente"
            row_key = str(book.get('id'))

            table.add_row(
                str(book.get('id')),
                book.get('title', 'Sin título').upper(),
                book.get('author_name', 'Desconocido'),
                book.get('format_type', '-'),
                book.get('publisher') or '-',
                status,
                key=row_key
            )
        table.focus()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        table = self.query_one(DataTable)
        table.sort(event.column_key)

    # ACCIÓN: ATRAPAMOS LA TECLA 'D'
    def action_show_details(self) -> None:
        """Extrae el ID de la fila seleccionada y empuja la pantalla de detalles."""
        table = self.query_one(DataTable)
        try:
            # Obtiene la coordenada actual del cursor
            coordinate = table.cursor_coordinate
            # Traduce esa coordenada a la llave (ID) que guardamos en la Fase 39
            row_key = table.coordinate_to_cell_key(coordinate).row_key.value

            if row_key:
                # Empujamos la nueva pantalla pasándole el ID
                self.push_screen(BookDetailsScreen(book_id=row_key))
        except Exception:
            pass
