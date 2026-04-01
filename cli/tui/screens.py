import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, Button, Label
from textual.containers import VerticalScroll, Vertical, Horizontal, Grid
from textual import work
from .constants import API_LIBRARY
from .movie_screens import MovieMainScreen


class BookDetailsScreen(Screen):
    BINDINGS = [
        ("escape, b, left", "go_back", "Volver a la Tabla"),
        ("q", "app.quit", "Salir")
    ]

    # CSS Integrado en la Pantalla
    CSS = """
    #details_root { padding: 1 2; }
    
    #header_panel { 
        border: heavy $accent; 
        background: $surface;
        margin-bottom: 1;
        padding: 1 2;
        height: auto;
        text-align: center; 
    }
    
    #details_grid { 
        grid-size: 2;
        grid-columns: 1fr 2fr;
        grid-gutter: 2;
    }
    
    .info_panel { 
        border: heavy $accent; 
        padding: 0 1; 
        background: $surface; 
        height: auto; 
    }
    """

    def __init__(self, book_id: str, **kwargs):
        super().__init__(**kwargs)
        self.book_id = book_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # CONTENEDORES GRID
        with VerticalScroll(id="details_root"):
            yield Markdown("Cargando...", id="header_panel")
            with Grid(id="details_grid"):
                with Vertical(classes="info_panel"):
                    yield Markdown(id="tech_panel")
                with Vertical(classes="info_panel"):
                    yield Markdown(id="synopsis_panel")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_details()

    @work(thread=True)
    def fetch_details(self) -> None:
        try:
            resp = httpx.get(f"{API_LIBRARY}{self.book_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_details, resp.json())
        except Exception:
            pass

    def render_details(self, book: dict) -> None:
        # Cabecera
        title = book.get('title', 'Sin Título').upper()
        subtitle = f"*{book.get('subtitle')}*" if book.get('subtitle') else ""
        author = book.get('author_name', 'Desconocido')

        # Título y autor centrados dentro de su panel
        header_md = f"# {title}\n{subtitle}\n### ✎ Autor: {author}"
        self.query_one("#header_panel", Markdown).update(header_md)

        # Ficha Técnica
        generos_str = ", ".join(book.get('genre_list', [])) if book.get(
            'genre_list') else "Sin clasificar"
        estado = "✔ Leído" if book.get('is_read') else "✘ Pendiente"
        ubicacion = "⇋ Prestado" if book.get(
            'is_loaned') else "❖ En Estantería"

        tech_md = f"""### ❖ Ficha Técnica
**Editorial:** {book.get('publisher') or '-'}
**Formato:** {book.get('format_type', '-')}
**Géneros:** {generos_str}
**Páginas:** {book.get('page_count') or '-'}
**Publicación:** {book.get('publish_date') or '-'}

---
### ⌖ Estado Físico
* **Lectura:** {estado}
* **Ubicación:** {ubicacion}
"""
        self.query_one("#tech_panel", Markdown).update(tech_md)

        # Sinopsis y Detalles Extra (Derecha)
        synopsis_md = ""
        details = book.get('details', {})
        if details:
            synopsis_md += "### ◈ Detalles Adicionales\n"
            for k, v in details.items():
                if isinstance(v, list):
                    v = ", ".join(v)
                synopsis_md += f"* **{k.replace('_', ' ').title()}:** {v}\n"
            synopsis_md += "\n---\n"

        desc = book.get('description')
        synopsis_md += f"### 📖 Sinopsis\n{desc if desc else '*Sin descripción disponible.*'}"

        self.query_one("#synopsis_panel", Markdown).update(synopsis_md)

    def action_go_back(self) -> None:
        self.app.pop_screen()


class BunkerLauncherScreen(Screen):
    """La pantalla de bienvenida y centro de selección de operaciones."""

    CSS = """
    #launcher_root { 
        align: center middle; 
        background: $surface-darken-2;
    }
    #launcher_panel {
        width: 50;
        height: auto;
        padding: 2 4;
        border: heavy $success;
        background: $surface;
        content-align: center middle;
    }
    .launcher_title { 
        text-align: center; 
        text-style: bold; 
        color: $success; 
        margin-bottom: 2; 
    }
    .launcher_btn { 
        width: 100%; 
        margin-bottom: 1; 
        text-style: bold; 
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="launcher_root"):
            with Vertical(id="launcher_panel"):
                yield Label("B U N K E R", classes="launcher_title")
                yield Button("1. Acceder a la Biblioteca", id="btn_lib", classes="launcher_btn", variant="primary")
                yield Button("2. Acceder al Videoclub", id="btn_movie", classes="launcher_btn", variant="warning")
                yield Button("3. Salir del Sistema", id="btn_quit", classes="launcher_btn", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib":
            self.app.pop_screen()
        elif event.button.id == "btn_movie":
            self.app.push_screen(MovieMainScreen())
        elif event.button.id == "btn_quit":
            self.app.exit()
