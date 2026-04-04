import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Label
from textual.containers import VerticalScroll, Vertical, Grid
from textual import work
from .constants import API_MOVIES


class MovieDetailsScreen(Screen):
    BINDINGS = [
        ("escape, b, left", "go_back", "Volver a la Cartelera"),
    ]

    CSS = """
    #movie_root { padding: 1 2; }
    #movie_header { 
        border: heavy $warning; 
        background: $surface; 
        margin-bottom: 1; 
        padding: 1 2; 
        align: center middle;
        content-align: center middle;
    }
    
    #movie_title { text-style: bold; color: $text; }
    #movie_subtitle { color: $text-muted; margin-top: 1; }

    #movie_grid { 
        grid-size: 3; 
        grid-columns: 1fr 2fr 2fr; /* Póster (1x) | Técnica (2x) | Cast & Sinopsis (2x) */
        grid-gutter: 2; 
    }
    
    .movie_panel { border: heavy $accent; padding: 0 1; background: $surface; height: auto; }
    
    #poster_panel { 
        border: double $success; 
        text-align: center; 
        color: $text;
        height: 100%;
        content-align: center middle;
    }
    """

    def __init__(self, movie_id: str, **kwargs):
        super().__init__(**kwargs)
        self.movie_id = movie_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="movie_root"):
            with Vertical(id="movie_header"):
                yield Label("Cargando cintas...", id="movie_title")
                yield Label("", id="movie_og_title")
            with Grid(id="movie_grid"):
                with Vertical(id="poster_panel"):
                    yield Markdown(id="poster_content")  # Col 1
                with Vertical(classes="movie_panel"):
                    yield Markdown(id="tech_panel")     # Col 2
                with Vertical(classes="movie_panel"):
                    yield Markdown(id="synopsis_panel")  # Col 3
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_movie()

    @work(thread=True)
    def fetch_movie(self) -> None:
        try:
            resp = httpx.get(f"{API_MOVIES}{self.movie_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_details, resp.json())
        except Exception:
            pass

    def render_details(self, m: dict) -> None:
        # Cabecera
        title = m.get('title', 'Sin Título').upper()
        og_title = f"[i]{m.get('original_title')}[/i]" if m.get(
            'original_title') else ""

        self.query_one("#movie_title", Label).update(f"[bold]🎬 {title}[/bold]")
        self.query_one("#movie_og_title", Label).update(og_title)

        # Col 1: Póster Tipográfico
        poster_md = f"## {title}\n\n🎬\n\n**{m.get('release_year', '-')}**\n\n*[dim]TMDB Data[/dim]*"
        self.query_one("#poster_content", Markdown).update(poster_md)

        # Col 2: Ficha Técnica
        watched = "✔ Sí" if m.get('is_watched') else "✘ No"
        tech_md = f"""### ❖ Datos Técnicos
**Director:** {m.get('director', '-')}
**Duración:** {m.get('duration_minutes', '-')} min
**Formato Físico:** {m.get('format_type', '-')}
**Año de Estreno:** {m.get('release_year', '-')}
**Géneros:** {', '.join(m.get('genres', [])) if m.get('genres') else '-'}

---
### ⌖ Estado de Colección
* **Visto:** {watched}
* **Préstamo:** {"⇋ Prestado" if m.get('is_loaned') else "❖ En Casa"}
"""
        self.query_one("#tech_panel", Markdown).update(tech_md)

        # Col 3: Cast & Sinopsis
        synopsis_md = f"""### Reparto Principal
{m.get('cast', 'Datos no disponibles.')}

---
### 📖 Sinopsis
{m.get('synopsis', 'Sin descripción.')}
"""
        self.query_one("#synopsis_panel", Markdown).update(synopsis_md)

    def action_go_back(self) -> None:
        self.app.pop_screen()


class MovieMainScreen(Screen):
    """El hub principal de tus películas."""

    BINDINGS = [
        ("escape", "go_back", "Volver al Bunker"),
        ("d", "show_details", "Ver Ficha Cinematográfica"),
    ]

    CSS = """
    DataTable { height: 1fr; margin: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="movies_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#movies_table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("ID", "Título", "Director",
                          "Año", "Formato", "Visto")
        self.load_movies()

    @work(thread=True)
    def load_movies(self) -> None:
        try:
            movies = httpx.get(API_MOVIES, timeout=5.0).json()
            if isinstance(movies, list):
                self.app.call_from_thread(self.populate_table, movies)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Error: {e}", severity="error")

    def populate_table(self, movies: list) -> None:
        table = self.query_one("#movies_table", DataTable)
        table.clear()
        for m in movies:
            watched = "✔" if m.get('is_watched') else "✘"
            table.add_row(
                str(m.get('id')),
                m.get('title', '').upper(),
                m.get('director', '-'),
                str(m.get('release_year', '-')),
                m.get('format_type', '-'),
                watched,
                key=str(m.get('id'))
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_show_details(self) -> None:
        table = self.query_one("#movies_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            if row_key:
                self.app.push_screen(MovieDetailsScreen(movie_id=row_key))
        except Exception:
            self.notify("Selecciona una película.", severity="warning")
