# Añade esto a tus importaciones al inicio del archivo
from textual.containers import VerticalScroll, Vertical, Grid
from textual.widgets import Label, Button
from textual.widgets import ProgressBar
import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, Button, Label
from textual.containers import VerticalScroll, Vertical, Horizontal, Grid
from textual import work
from .constants import API_LIBRARY, API_TRACKER, API_MOVIES
from .movie_screens import MovieMainScreen
from textual.widgets import ProgressBar


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
    """El centro de mando global con estadísticas unificadas y patrón BFF."""

    BINDINGS = [
        ("escape, b, left", "go_back", "Volver al Menú Principal"),
    ]

    CSS = """
    #dashboard_root { padding: 1 2; align: center middle; }
    .dash_title { text-align: center; text-style: bold; color: $success; margin-bottom: 1; width: 100%; }
    
    #dash_grid { grid-size: 2; grid-gutter: 2; height: 16; margin-bottom: 1; }
    .dash_panel { border: heavy $primary; padding: 1 2; background: $surface; }
    .dash_panel_title { text-align: center; text-style: bold; color: $warning; margin-bottom: 1; border-bottom: solid $warning; }
    
    #feed_panel { border: heavy $accent; padding: 1 2; background: $surface; height: auto; }
    .progress_label { margin-top: 1; color: $text-muted; text-style: bold; }
    ProgressBar { margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard_root"):
            yield Label("☢️  CENTRO DE MANDO GLOBAL  ☢️", classes="dash_title")

            with Grid(id="dash_grid"):
                with Vertical(classes="dash_panel"):
                    yield Label("SECTOR LITERARIO", classes="dash_panel_title")
                    yield Label("Progreso de Lectura de la Colección:", classes="progress_label")
                    yield ProgressBar(id="bar_books", show_eta=False)
                    yield Markdown("Calculando métricas...", id="dash_books")

                with Vertical(classes="dash_panel"):
                    yield Label("SECTOR CINEMATOGRÁFICO", classes="dash_panel_title")
                    yield Label("Progreso de Visionado:", classes="progress_label")
                    yield ProgressBar(id="bar_movies", show_eta=False)
                    yield Markdown("Calculando métricas...", id="dash_movies")

            with Vertical(id="feed_panel"):
                yield Label("ÚLTIMA ACTIVIDAD EN EL BUNKER", classes="dash_panel_title")
                yield Markdown("Sincronizando radares...", id="dash_feed")

        yield Footer()

    def on_mount(self) -> None:
        self.fetch_global_stats()

    @work(thread=True)
    def fetch_global_stats(self) -> None:
        try:
            from .constants import API_DASHBOARD
            # Una sola llamada en lugar de descargar toda la base de datos
            resp = httpx.get(API_DASHBOARD, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(self.render_dashboard, data)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error del servidor BFF: {resp.status_code}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error cargando el Centro de Mando: {e}", severity="error")

    def render_dashboard(self, data: dict) -> None:
        b = data.get("books", {})
        m = data.get("movies", {})
        feed = data.get("feed", [])

        # 1. Actualizar Barras de Progreso
        bar_books = self.query_one("#bar_books", ProgressBar)
        bar_movies = self.query_one("#bar_movies", ProgressBar)

        bar_books.total = b.get("total", 1)
        bar_books.progress = b.get("read", 0)

        bar_movies.total = m.get("total", 1)
        bar_movies.progress = m.get("watched", 0)

        # 2. Renderizar Libros
        book_md = f"""
* **Total en Colección:** `{b.get('total', 0)}` obras
* **Obras Terminadas:** `{b.get('read', 0)}`
* **Horas de Lectura Est.:** `{b.get('hours', 0)} hrs`
        """
        self.query_one("#dash_books", Markdown).update(book_md)

        # 3. Renderizar Películas
        movie_md = f"""
* **Total en Bóveda:** `{m.get('total', 0)}` cintas
* **Cintas Vistas:** `{m.get('watched', 0)}`
* **Horas de Visionado:** `{m.get('hours', 0)} hrs`
        """
        self.query_one("#dash_movies", Markdown).update(movie_md)

        # 4. Renderizar Feed Curado
        if not feed:
            feed_lines = ["* *Sin actividad detectada en el Bunker.*"]
        else:
            feed_lines = [f"* {line}" for line in feed]

        self.query_one("#dash_feed", Markdown).update("\n".join(feed_lines))

    def action_go_back(self) -> None:
        self.app.pop_screen()


class BunkerLauncherScreen(Screen):
    """La pantalla de bienvenida y centro de selección de operaciones."""

    CSS = """
    #launcher_root { 
        align: center middle; 
        background: $surface-darken-2;
        padding: 2 4;
        /* Habilitamos el scroll vertical nativo si la terminal es pequeña */
        overflow-y: auto; 
    }
    #sys_status {
        width: 80;
        text-align: right;
        color: $warning;
        text-style: bold;
        margin-bottom: 1;
    }
    .ascii_logo { 
        text-align: center; 
        text-style: bold; 
        color: $success; 
        margin-bottom: 2; 
    }
    #launcher_grid {
        grid-size: 2;
        grid-gutter: 1 4; /* Reducimos el espacio vertical entre filas de 2 a 1 */
        width: 80;
        height: auto;
        margin-bottom: 2;
    }
    .module_panel {
        height: auto; /* Dejamos que el panel abrace su contenido, ahorrando espacio */
        padding: 1 2;
        border: heavy $primary;
        background: $surface;
        align: center middle;
        content-align: center middle;
    }
    .module_panel_offline {
        height: auto;
        padding: 1 2;
        border: dashed $error;
        background: $surface-darken-1;
        align: center middle;
        content-align: center middle;
        opacity: 0.7;
    }
    .module_title { 
        text-align: center; 
        text-style: bold; 
        margin-bottom: 1; 
    }
    .launcher_btn { 
        width: 100%; 
        text-style: bold; 
    }
    #btn_quit {
        width: 80;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        ascii_art = """
        ██████╗ ██╗   ██╗███╗   ██╗██╗  ██╗███████╗██████╗ 
        ██╔══██╗██║   ██║████╗  ██║██║ ██╔╝██╔════╝██╔══██╗
        ██████╔╝██║   ██║██╔██╗ ██║█████╔╝ █████╗  ██████╔╝
        ██╔══██╗██║   ██║██║╚██╗██║██╔═██╗ ██╔══╝  ██╔══██╗
        ██████╔╝╚██████╔╝██║ ╚████║██║  ██╗███████╗██║  ██║
        ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
        """
        # Cambiamos Vertical por VerticalScroll para blindar la responsividad
        with VerticalScroll(id="launcher_root"):
            yield Label("SISTEMA: [green]ONLINE[/green] | NÚCLEO: [green]ESTABLE[/green]", id="sys_status")
            yield Label(ascii_art, classes="ascii_logo")

            with Grid(id="launcher_grid"):
                # Módulo 1: Biblioteca
                with Vertical(classes="module_panel"):
                    yield Label("📚 MÓDULO 1: BIBLIOTECA", classes="module_title", id="lbl_lib")
                    yield Button("INICIAR ENLACE", id="btn_lib", classes="launcher_btn", variant="primary")

                # Módulo 2: Videoclub
                with Vertical(classes="module_panel"):
                    yield Label("🎬 MÓDULO 2: VIDEOCLUB", classes="module_title")
                    yield Button("INICIAR ENLACE", id="btn_movie", classes="launcher_btn", variant="warning")

                # Módulo 3: Centro de Mando
                with Vertical(classes="module_panel"):
                    yield Label("☢️ MÓDULO 3: MÉTRICAS GLOBALES", classes="module_title")
                    yield Button("CENTRO DE MANDO", id="btn_dash", classes="launcher_btn", variant="success")

                # Módulo 4 y 5: Espacio para el futuro
                with Vertical(classes="module_panel_offline"):
                    yield Label("[red]⚠️ MÓDULOS 4 Y 5[/red]", classes="module_title")
                    yield Button("SISTEMAS OFFLINE", id="btn_null", classes="launcher_btn", variant="default", disabled=True)

            yield Button("DESCONECTAR SISTEMA (Salir)", id="btn_quit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib":
            from .library_screen import LibraryMainScreen
            self.app.push_screen(LibraryMainScreen())
        elif event.button.id == "btn_movie":
            from .movie_screens import MovieMainScreen
            self.app.push_screen(MovieMainScreen())
        elif event.button.id == "btn_dash":
            from .screens import BunkerDashboardScreen
            self.app.push_screen(BunkerDashboardScreen())
        elif event.button.id == "btn_quit":
            self.app.exit()
