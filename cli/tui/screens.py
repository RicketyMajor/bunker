import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, Button, Label
from textual.containers import VerticalScroll, Vertical, Horizontal, Grid
from textual import work
from .constants import API_LIBRARY, API_TRACKER, API_MOVIES
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
        align: center middle;
        content-align: center middle;
    }
    
    #header_title { text-style: bold; color: $text; }
    #header_author { color: $success; margin-top: 1; }
    
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
            with Vertical(id="header_panel"):
                yield Label("Cargando...", id="header_title")
                yield Label("", id="header_subtitle")
                yield Label("", id="header_author")
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
        subtitle = f"[i]{book.get('subtitle')}[/i]" if book.get('subtitle') else ""
        author = book.get('author_name', 'Desconocido')

        self.query_one("#header_title", Label).update(f"[bold]{title}[/bold]")
        self.query_one("#header_subtitle", Label).update(subtitle)
        self.query_one("#header_author", Label).update(f"✎ Autor: {author}")

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

        # Sinopsis y Detalles Extra
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


class BunkerDashboardScreen(Screen):
    """El centro de mando global con estadísticas unificadas."""

    BINDINGS = [
        ("escape, b, left", "go_back", "Volver al Menú Principal"),
    ]

    CSS = """
    #dashboard_root { padding: 2 4; align: center middle; }
    .dash_title { text-align: center; text-style: bold; color: $accent; margin-bottom: 2; width: 100%; }
    #dash_grid { grid-size: 2; grid-gutter: 4; height: auto; }
    .dash_panel { border: heavy $primary; padding: 1 2; background: $surface; height: 15; }
    .dash_panel_title { text-align: center; text-style: bold; color: $success; margin-bottom: 1; border-bottom: solid $success; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard_root"):
            yield Label("CENTRO DE MANDO GLOBAL", classes="dash_title")
            with Grid(id="dash_grid"):
                with Vertical(classes="dash_panel"):
                    yield Label("SECTOR LITERARIO", classes="dash_panel_title")
                    yield Markdown("Calculando métricas...", id="dash_books")
                with Vertical(classes="dash_panel"):
                    yield Label("SECTOR CINEMATOGRÁFICO", classes="dash_panel_title")
                    yield Markdown("Calculando métricas...", id="dash_movies")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_global_stats()

    @work(thread=True)
    def fetch_global_stats(self) -> None:
        try:
            # Consume el tracker de libros
            books_stats = httpx.get(API_TRACKER, timeout=5.0).json()

            # Consume el inventario de películas para calcular
            movies_resp = httpx.get(API_MOVIES, timeout=5.0).json()
            movies_watched = len(
                [m for m in movies_resp if m.get('is_watched')])
            movies_total = len(movies_resp)

            self.app.call_from_thread(
                self.render_dashboard, books_stats, movies_watched, movies_total)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error cargando el Centro de Mando: {e}", severity="error")

    def render_dashboard(self, b_stats: dict, m_watched: int, m_total: int) -> None:
        # Render libros
        book_md = f"""
* **Páginas leídas este mes:** `{b_stats.get('pages_this_month', 0)}`
* **Libros terminados este mes:** `{b_stats.get('books_this_month', 0)}`
        """
        self.query_one("#dash_books", Markdown).update(book_md)

        # Render películas
        movie_md = f"""
* **Películas Vistas (Histórico):** `{m_watched}`
* **Total en Colección:** `{m_total}`
* **Pendientes de ver:** `{m_total - m_watched}`
        """
        self.query_one("#dash_movies", Markdown).update(movie_md)

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
                yield Label("☢️  B U N K E R  ☢️", classes="launcher_title")
                yield Button("1. Acceder a la Biblioteca", id="btn_lib", classes="launcher_btn", variant="primary")
                yield Button("2. Acceder al Videoclub", id="btn_movie", classes="launcher_btn", variant="warning")
                yield Button("3. Centro de Mando", id="btn_dash", classes="launcher_btn", variant="success")
                yield Button("4. Salir del Sistema", id="btn_quit", classes="launcher_btn", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib":
            self.app.pop_screen()
        elif event.button.id == "btn_movie":
            from .movie_screens import MovieMainScreen
            self.app.push_screen(MovieMainScreen())
        elif event.button.id == "btn_dash":
            self.app.push_screen(BunkerDashboardScreen())
        elif event.button.id == "btn_quit":
            self.app.exit()
