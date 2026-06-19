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
from .modals import ConfirmModal, EvacuationModal
from .constants import API_BACKUP, API_RESTORE


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
        with VerticalScroll(id="dashboard_root"):
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

        # Actualizar Barras de Progreso
        bar_books = self.query_one("#bar_books", ProgressBar)
        bar_movies = self.query_one("#bar_movies", ProgressBar)

        bar_books.total = b.get("total", 1)
        bar_books.progress = b.get("read", 0)

        bar_movies.total = m.get("total", 1)
        bar_movies.progress = m.get("watched", 0)

        # Renderizar Libros
        book_md = f"""
* **Total en Colección:** `{b.get('total', 0)}` obras
* **Obras Terminadas:** `{b.get('read', 0)}`
* **Horas de Lectura Est.:** `{b.get('hours', 0)} hrs`
        """
        self.query_one("#dash_books", Markdown).update(book_md)

        # Renderizar Películas
        movie_md = f"""
* **Total en Bóveda:** `{m.get('total', 0)}` cintas
* **Cintas Vistas:** `{m.get('watched', 0)}`
* **Horas de Visionado:** `{m.get('hours', 0)} hrs`
        """
        self.query_one("#dash_movies", Markdown).update(movie_md)

        # Renderizar Feed Curado
        if not feed:
            feed_lines = ["* *Sin actividad detectada en el Bunker.*"]
        else:
            feed_lines = [f"* {line}" for line in feed]

        self.query_one("#dash_feed", Markdown).update("\n".join(feed_lines))

    def action_go_back(self) -> None:
        self.app.pop_screen()


class BunkerLauncherScreen(Screen):
    """Centro de Mando en Vivo — Dashboard principal del Bunker (Estilo Abtop)."""

    BINDINGS = [
        ("1", "launch_lib", "Biblioteca"),
        ("2", "launch_movie", "Videoclub"),
        ("3", "launch_music", "Disquera"),
        ("4", "launch_posada", "Posada"),
        ("5", "launch_chess", "Ajedrez"),
        ("q", "app.quit", "Desconectar"),
    ]

    CSS = """
    #launcher_root {
        width: 100%;
        height: 100%;
        background: $surface;
        padding: 1;
    }

    /* ── HEADER ── */
    #header_row { 
        height: auto;
        margin-bottom: 1; 
        layout: horizontal;
    }
    #logo_compact { 
        width: 1fr; 
        color: $success; 
        text-style: bold; 
        content-align: left middle; 
    }
    #prestige_panel { 
        width: 45; 
        border: tall $warning; 
        background: $surface-darken-1; 
        padding: 0 1; 
    }
    #prestige_label { text-style: bold; color: $warning; text-align: center; width: 100%; }
    #prestige_bar_label { color: $text-muted; text-align: center; width: 100%; margin-top: 1; }
    ProgressBar { margin: 0; }

    /* ── BODY (Grid Rígido) ── */
    #body_row { 
        height: 1fr; /* Ocupa todo el espacio restante automáticamente */
        layout: grid;
        grid-size: 3;
        grid-columns: 1fr 1fr 1.2fr;
        grid-gutter: 1 2;
    }
    
    .launcher_panel {
        height: 100%;
        border: round $primary;
        background: $surface-darken-1;
        padding: 0 1;
    }
    
    #posada_panel { border: round #8a2be2; }
    #feed_panel { border: round $accent; }
    
    .panel_title { 
        text-style: bold; 
        color: $accent; 
        text-align: center; 
        width: 100%; 
        margin-bottom: 1; 
        border-bottom: solid $primary; 
    }
    
    .metric_line { height: 1; color: $text; }
    
    .collection_title { text-style: bold; margin-top: 1; }
    .collection_stat { color: $text-muted; }
    .collection_live { color: $success; text-style: bold; }
    
    .feed_item { margin-bottom: 1; color: $text; }

    /* ── FOOTER ── */
    #modules_bar {
        height: 3;
        margin-top: 1;
        align: center middle;
        layout: horizontal;
    }
    #modules_bar Button { margin: 0 1; min-width: 12; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="launcher_root"):
            
            # ── HEADER: Logo + Prestigio ──
            with Horizontal(id="header_row"):
                yield Label(
                    "██████╗ ██╗   ██╗███╗   ██╗██╗  ██╗███████╗██████╗ \n"
                    "██╔══██╗██║   ██║████╗  ██║██║ ██╔╝██╔════╝██╔══██╗\n"
                    "██████╔╝██║   ██║██╔██╗ ██║█████╔╝ █████╗  ██████╔╝\n"
                    "██╔══██╗██║   ██║██║╚██╗██║██╔═██╗ ██╔══╝  ██╔══██╗\n"
                    "██████╔╝╚██████╔╝██║ ╚████║██║  ██╗███████╗██║  ██║\n"
                    "╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝\n"
                    "[dim]Centro de Operaciones y Control Estratégico[/dim]",
                    id="logo_compact"
                )
                with Vertical(id="prestige_panel"):
                    yield Label("⚜️  GREMIO Nv. -- — Prestigio: --/--", id="prestige_label")
                    yield ProgressBar(id="prestige_bar", show_eta=False) # <- CORREGIDO
                    yield Label("SISTEMA: ESPERANDO TELEMETRÍA...", id="prestige_bar_label")

            # ── BODY: 3 Columnas en Grid ──
            with Horizontal(id="body_row"):

                # Columna Izquierda: Estado de la Posada
                with Vertical(id="posada_panel", classes="launcher_panel"):
                    yield Label("⚔️  MÉTRICAS DEL SISTEMA", classes="panel_title")
                    yield Label("⏱️  DW Hoy: [dim]-- min[/]", id="metric_dw", classes="metric_line")
                    yield Label("👥 Aventureros: [dim]-- activos[/]", id="metric_advs", classes="metric_line")
                    yield Label("🏆 Líder: [dim]--[/]", id="metric_leader", classes="metric_line")
                    yield Label("💰 Patrimonio: [dim]-- Talentos[/]", id="metric_wealth", classes="metric_line")
                    yield Label("", id="metric_sep1", classes="metric_line")
                    yield Label("✅ Hábitos: [dim]--/--[/]", id="metric_habits", classes="metric_line")
                    yield Label("🔥 Racha: [dim]--[/]", id="metric_streak", classes="metric_line")
                    yield Label("📋 Kanban: [dim]-- pendientes[/]", id="metric_kanban", classes="metric_line")
                    yield Label("📅 Calendar: [dim]-- eventos hoy[/]", id="metric_calendar", classes="metric_line")

                # Columna Central: Barras de Colección
                with Vertical(id="collections_panel", classes="launcher_panel"):
                    yield Label("📊  COLECCIONES EN VIVO", classes="panel_title")

                    yield Label("📚 BIBLIOTECA", classes="collection_title", id="lib_title")
                    yield ProgressBar(id="bar_books", show_eta=False) # <- CORREGIDO
                    yield Label("--/-- leídos • --h est.", id="stat_books", classes="collection_stat")

                    yield Label("🎬 VIDEOCLUB", classes="collection_title", id="mov_title")
                    yield ProgressBar(id="bar_movies", show_eta=False) # <- CORREGIDO
                    yield Label("--/-- vistas • --h", id="stat_movies", classes="collection_stat")

                    yield Label("🎵 DISQUERA", classes="collection_title", id="mus_title")
                    yield ProgressBar(id="bar_music", show_eta=False) # <- CORREGIDO
                    yield Label("--/-- escuchados • --h", id="stat_music", classes="collection_stat")

                # Columna Derecha: Feed de Actividad (El único con Scroll interno)
                with VerticalScroll(id="feed_panel", classes="launcher_panel"):
                    yield Label("📡  TRÁFICO DE RED", classes="panel_title")
                    for i in range(15): 
                        yield Label("", id=f"feed_{i}", classes="feed_item")

            # ── FOOTER: Módulos ──
            with Horizontal(id="modules_bar"):
                yield Button("[1] Biblioteca", id="btn_lib", variant="primary")
                yield Button("[2] Videoclub", id="btn_movie", variant="primary")
                yield Button("[3] Disquera", id="btn_music", variant="primary")
                yield Button("[4] Posada", id="btn_posada", variant="primary")
                yield Button("[5] Ajedrez", id="btn_chess", variant="primary")
                yield Button("Backup", id="btn_evac", variant="warning")
                yield Button("Salir", id="btn_quit", variant="error")

    def on_mount(self) -> None:
        self.fetch_dashboard()
        # En la fase 3 ajustaremos el temporizador de polling
        self.set_interval(30, self.fetch_dashboard)

    @work(thread=True)
    def fetch_dashboard(self) -> None:
        """Función temporal para la Fase 1. Previene bloqueos si la API no existe."""
        try:
            from .constants import API_DASHBOARD
            resp = httpx.get(API_DASHBOARD, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_dashboard, resp.json())
            else:
                self.app.call_from_thread(self.update_status, "SISTEMA: [yellow]API NO ENCONTRADA[/yellow]")
        except Exception:
            self.app.call_from_thread(self.update_status, "SISTEMA: [red]OFFLINE (ESPERANDO BACKEND)[/red]")

    def update_status(self, text: str) -> None:
        try:
            self.query_one("#prestige_bar_label", Label).update(text)
        except Exception:
            pass

    def render_dashboard(self, data: dict) -> None:
        """Lógica de renderizado que completaremos en la Fase 3."""
        self.update_status("[blink]🔴 EN VIVO[/blink] │ SISTEMA: [green]ONLINE[/green] │ NÚCLEO: [green]ESTABLE[/green]")
        pass

    # ── NAVEGACIÓN Y ACCIONES DE BOTONES ──
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib":
            self.action_launch_lib()
        elif event.button.id == "btn_movie":
            self.action_launch_movie()
        elif event.button.id == "btn_music":
            self.action_launch_music()
        elif event.button.id == "btn_posada":
            self.action_launch_posada()
        elif event.button.id == "btn_chess":
            self.action_launch_chess()
        elif event.button.id == "btn_evac":
            self.app.notify("Sistema de evacuación temporalmente desactivado para mantenimiento.", severity="warning")
        elif event.button.id == "btn_quit":
            self.app.exit()

    def action_launch_lib(self) -> None:
        from .library_screen import LibraryMainScreen
        self.app.push_screen(LibraryMainScreen())

    def action_launch_movie(self) -> None:
        from .movie_screens import MovieMainScreen
        self.app.push_screen(MovieMainScreen())

    def action_launch_music(self) -> None:
        from .music_screens import MusicMainScreen
        self.app.push_screen(MusicMainScreen())

    def action_launch_posada(self) -> None:
        from .posada_screens import PosadaMainScreen
        self.app.push_screen(PosadaMainScreen())

    def action_launch_chess(self) -> None:
        from .chess_screens import ChessMainScreen
        self.app.push_screen(ChessMainScreen())

    # ── FUNCIONES DE SEGURIDAD ──
    @work(thread=True)
    def process_backup(self) -> None:
        try:
            resp = httpx.post(API_BACKUP, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(
                    self.app.notify, f"Cápsula lista en: {data.get('path')}", title="Éxito")
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error: {resp.json().get('error', 'Desconocido')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    @work(thread=True)
    def process_restore(self) -> None:
        try:
            resp = httpx.post(API_RESTORE, timeout=15.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "Búnker restaurado con éxito. Datos recargados.", title="Restauración Exitosa")
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error al restaurar: {resp.json().get('error', 'Revisa si existe el archivo json.')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

