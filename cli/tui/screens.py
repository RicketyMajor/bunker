from textual.containers import VerticalScroll, Vertical, Grid
from textual.widgets import Label, Button
from textual.widgets import ProgressBar
from datetime import datetime
from textual.reactive import reactive
from .posada_screens import ASCII_NUMS
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
    """Centro de Mando Cyberpunk — Dashboard principal del Bunker."""

    dashboard_data = reactive({})
    _clock_blink = reactive(True)
    _boot_done = reactive(False)

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
        
        padding: 0 1;
        overflow-y: auto;
        overflow-x: hidden;
    }

    /* ── HEADER: LOGO + STATUS ── */
    #header_section {
        height: auto;
        width: 100%;
        align: center middle;
        margin-bottom: 0;
    }
    #logo_label {
        color: $success;
        text-style: bold;
        text-align: center;
        width: 100%;
    }
    #status_bar {
        height: 1;
        width: 100%;
        background: $surface;
        color: $success;
        text-align: center;
        text-style: bold;
        margin-bottom: 0;
        padding: 0 2;
    }

    /* ── SYSTEM ROW: PRESTIGIO + RELOJ ── */
    #system_row {
        height: 9;
        layout: horizontal;
        margin-bottom: 0;
    }
    #prestige_panel {
        width: 1fr;
        height: 100%;
        border: tall $accent;
        background: $surface;
        padding: 0 2;
        content-align: center middle;
    }
    #prestige_title {
        text-style: bold;
        color: $warning;
        text-align: center;
        width: 100%;
    }
    #prestige_gauge {
        text-align: center;
        width: 100%;
        color: $success;
        margin-top: 1;
    }
    #prestige_info {
        text-align: center;
        width: 100%;
        color: $text-muted;
        text-style: italic;
    }

    #clock_panel {
        width: 40;
        height: 100%;
        border: tall $accent;
        background: $surface;
        align: center middle;
        margin-left: 1;
    }
    #ascii_clock {
        text-align: center;
        color: $accent;
        text-style: bold;
        width: 100%;
    }
    #clock_date {
        text-align: center;
        width: 100%;
        color: $text-muted;
        text-style: bold;
    }

    /* ── BODY: 3 PANELES ── */
    #body_row {
        height: auto;
        min-height: 18;
        margin-bottom: 0;
        layout: horizontal;
    }

    .cyber_panel {
        width: 1fr;
        height: 100%;
        border: tall $primary;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }
    #metrics_panel { border: tall $primary; margin-right: 1; }
    #collections_panel { border: tall $accent; margin-right: 1; }
    #feed_panel { border: tall $success; }

    .cyber_title {
        text-style: bold;
        color: $accent;
        text-align: center;
        width: 100%;
        padding: 0 0;
    }
    .cyber_separator {
        color: #1a3a4a;
        text-align: center;
        width: 100%;
        height: 1;
    }

    .metric_line {
        height: 1;
        color: $text;
        padding: 0 1;
    }
    .collection_block {
        height: auto;
        padding: 0 1;
    }
    .col_header {
        text-style: bold;
        color: $text;
    }
    .col_bar {
        color: $success;
    }
    .col_stat {
        color: $text-muted;
        margin-bottom: 1;
    }
    .feed_item {
        color: $text-muted;
        padding: 0 1;
    }

    /* ── MODULES BAR ── */
    #modules_bar {
        height: 3;
        margin-top: 0;
        align: center middle;
        layout: horizontal;
        background: $surface;
    }
    .mod_btn {
        min-width: 16;
        margin: 0 0;
        border: tall $primary;
        background: $surface;
        color: $text;
    }
    .mod_btn:hover {
        background: $primary;
        color: $success;
    }
    .mod_btn_danger {
        min-width: 10;
        margin: 0 0;
        background: $error-muted;
        color: $text;
        border: tall $error;
    }
    .mod_btn_danger:hover {
        background: $error;
    }
    .mod_btn_warn {
        min-width: 10;
        margin: 0 0;
        background: $warning-muted;
        color: $warning;
        border: tall $warning;
    }
    .mod_btn_warn:hover {
        background: $warning;
    }

    /* ── BOOT OVERLAY ── */
    #boot_log {
        display: none;
    }
    """

    # ── LOGO ASCII CYBERPUNK ──
    LOGO = (
        "[$success]██████╗  ██╗   ██╗ ███╗   ██╗ ██╗  ██╗ ███████╗ ██████╗ [/]\n"
        "[$success]██╔══██╗ ██║   ██║ ████╗  ██║ ██║ ██╔╝ ██╔════╝ ██╔══██╗[/]\n"
        "[$success]██████╔╝ ██║   ██║ ██╔██╗ ██║ █████╔╝  █████╗   ██████╔╝[/]\n"
        "[$success]██╔══██╗ ██║   ██║ ██║╚██╗██║ ██╔═██╗  ██╔══╝   ██╔══██╗[/]\n"
        "[$success]██████╔╝ ╚██████╔╝ ██║ ╚████║ ██║  ██╗ ███████╗ ██║  ██║[/]\n"
        "[$success]╚═════╝   ╚═════╝  ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝[/]"
    )

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="launcher_root"):

            # ── 1. HEADER ──
            with Vertical(id="header_section"):
                yield Label(self.LOGO, id="logo_label")
                yield Label("◈ INICIALIZANDO SISTEMAS... ◈", id="status_bar")

            # ── 2. SYSTEM ROW ──
            with Horizontal(id="system_row"):
                with Vertical(id="prestige_panel"):
                    yield Label("⚜  GREMIO  ─  NIVEL --", id="prestige_title")
                    yield Label("[dim]░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[/dim] 0%", id="prestige_gauge")
                    yield Label("Esperando telemetría...", id="prestige_info")

                with Vertical(id="clock_panel"):
                    yield Label("", id="ascii_clock")
                    yield Label("", id="clock_date")

            # ── 3. BODY ROW ──
            with Horizontal(id="body_row"):
                # Panel Métricas
                with Vertical(id="metrics_panel", classes="cyber_panel"):
                    yield Label("◈ MÉTRICAS DEL SISTEMA ◈", classes="cyber_title")
                    yield Label("────────────────────────────", classes="cyber_separator")
                    yield Label("  Actividad 7d │ [dim]--[/]", id="metric_sparkline", classes="metric_line")
                    yield Label("  Aventureros  │ [dim]-- activos[/]", id="metric_advs", classes="metric_line")
                    yield Label("  Héroe Líder  │ [dim]--[/]", id="metric_leader", classes="metric_line")
                    yield Label("  Patrimonio   │ [dim]-- Talentos[/]", id="metric_wealth", classes="metric_line")
                    yield Label("  Hábitos Hoy  │ [dim]--/--[/]", id="metric_habits", classes="metric_line")
                    yield Label("  Racha Hábitos│ [dim]--[/]", id="metric_streak", classes="metric_line")
                    yield Label("  Racha Lectura│ [dim]--[/]", id="metric_read_streak", classes="metric_line")
                    yield Label("  Kanban Pend. │ [dim]-- tareas[/]", id="metric_kanban", classes="metric_line")
                    yield Label("  Eventos Hoy  │ [dim]-- eventos[/]", id="metric_calendar", classes="metric_line")

                # Panel Colecciones
                with Vertical(id="collections_panel", classes="cyber_panel"):
                    yield Label("◈ COLECCIONES EN VIVO ◈", classes="cyber_title")
                    yield Label("────────────────────────────", classes="cyber_separator")
                    with Vertical(classes="collection_block"):
                        yield Label("[#00e5ff]▸[/] BIBLIOTECA", classes="col_header", id="lib_title")
                        yield Label("[dim]░░░░░░░░░░░░░░░░░░░░[/dim] 0%", id="bar_books", classes="col_bar")
                        yield Label("  --/-- leídos • --h est.", id="stat_books", classes="col_stat")
                        yield Label("", id="stat_books_health", classes="col_stat")

                    with Vertical(classes="collection_block"):
                        yield Label("[#ffb000]▸[/] VIDEOCLUB", classes="col_header", id="mov_title")
                        yield Label("[dim]░░░░░░░░░░░░░░░░░░░░[/dim] 0%", id="bar_movies", classes="col_bar")
                        yield Label("  --/-- vistas • --h", id="stat_movies", classes="col_stat")

                    with Vertical(classes="collection_block"):
                        yield Label("[#ff00ff]▸[/] DISQUERA", classes="col_header", id="mus_title")
                        yield Label("[dim]░░░░░░░░░░░░░░░░░░░░[/dim] 0%", id="bar_music", classes="col_bar")
                        yield Label("  --/-- escuch. • --h", id="stat_music", classes="col_stat")

                # Panel Feed
                with Vertical(id="feed_panel", classes="cyber_panel"):
                    yield Label("◈ TRÁFICO DE RED ◈", classes="cyber_title")
                    yield Label("────────────────────────────", classes="cyber_separator")
                    for i in range(10):
                        yield Label("", id=f"feed_{i}", classes="feed_item")

            # ── 4. MODULES BAR ──
            with Horizontal(id="modules_bar"):
                yield Button("[ 1 ] BIBLIOTECA", id="btn_lib", classes="mod_btn")
                yield Button("[ 2 ] VIDEOCLUB", id="btn_movie", classes="mod_btn")
                yield Button("[ 3 ] DISQUERA", id="btn_music", classes="mod_btn")
                yield Button("[ 4 ] POSADA", id="btn_posada", classes="mod_btn")
                yield Button("[ 5 ] AJEDREZ", id="btn_chess", classes="mod_btn")
                yield Button("BACKUP", id="btn_evac", classes="mod_btn_warn")
                yield Button("SALIR", id="btn_quit", classes="mod_btn_danger")

    def on_mount(self) -> None:
        self.tick_clock()
        self.set_interval(1.0, self.tick_clock)
        self.fetch_dashboard()
        self.set_interval(15.0, self.fetch_dashboard)

    def tick_clock(self) -> None:
        from datetime import datetime
        try:
            from .posada_screens import ASCII_NUMS
        except ImportError:
            return

        now = datetime.now()
        self._clock_blink = not self._clock_blink
        time_str = now.strftime("%H:%M:%S")
        lines = ["", "", "", "", ""]

        for char in time_str:
            if char == ':':
                if self._clock_blink:
                    pattern = ["   ", " ▄ ", "   ", " ▀ ", "   "]
                else:
                    pattern = ["   ", "   ", "   ", "   ", "   "]
            else:
                pattern = ASCII_NUMS.get(char, ["   "] * 5)
            for i in range(5):
                lines[i] += pattern[i] + " "

        try:
            self.query_one("#ascii_clock", Label).update("\n".join(lines))
            # Date in cyberpunk format
            date_str = now.strftime("%Y.%m.%d // %a").upper()
            self.query_one("#clock_date", Label).update(f"[#555555]{date_str}[/]")
        except Exception:
            pass

    def create_sparkline(self, data: list) -> str:
        """Genera un minigráfico ASCII basado en una serie temporal."""
        if not data or max(data) == 0:
            return "[dim]▁▁▁▁▁▁▁[/dim] (0m)"
        bars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        max_val = max(data)
        sparkline = ""
        for val in data:
            idx = int((val / max_val) * 7) if max_val > 0 else 0
            sparkline += bars[idx]
        return f"[#00ff41]{sparkline}[/] ({data[-1]}m)"

    def create_gauge(self, current: int, total: int, width: int = 20) -> str:
        """Genera una barra ASCII: ████████░░░░░░░░░░░░ 42%"""
        if total == 0:
            return f"[dim]{'░' * width}[/dim] 0%"
        pct = min(current / total, 1.0)
        filled = int(pct * width)
        empty = width - filled
        pct_val = int(pct * 100)
        # Color by percentage
        if pct_val >= 70:
            color = "#00ff41"
        elif pct_val >= 30:
            color = "#ffb000"
        else:
            color = "#ff4444"
        return f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/dim] {pct_val}%"

    def create_prestige_gauge(self, current: int, total: int, width: int = 30) -> str:
        """Gauge especial para prestigio con gradiente."""
        if total == 0:
            return f"[dim]{'░' * width}[/dim] 0%"
        pct = min(current / total, 1.0)
        filled = int(pct * width)
        empty = width - filled
        pct_val = int(pct * 100)
        return f"[#ffb000]{'█' * filled}[/][dim]{'░' * empty}[/dim] [bold #ffb000]{pct_val}%[/]"

    @work(thread=True)
    def fetch_dashboard(self) -> None:
        try:
            from .constants import API_DASHBOARD
            import httpx
            resp = httpx.get(API_DASHBOARD, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.update_reactive_data, resp.json())
            else:
                self.app.call_from_thread(self.update_status_bar, "red")
        except Exception:
            self.app.call_from_thread(self.update_status_bar, "offline")

    def update_reactive_data(self, data: dict) -> None:
        self.dashboard_data = data

    def update_status_bar(self, mode: str) -> None:
        try:
            sb = self.query_one("#status_bar", Label)
            if mode == "offline":
                sb.update("[#ff4444]◈ OFFLINE ─── ESPERANDO BACKEND ─── REINTENTAR EN 15s ◈[/]")
            elif mode == "red":
                sb.update("[#ffb000]◈ API NO ENCONTRADA ─── VERIFICAR DOCKER ◈[/]")
        except Exception:
            pass

    def watch_dashboard_data(self, data: dict) -> None:
        if not data:
            return

        if not self._boot_done:
            self._boot_done = True
            posada = data.get("posada", {})
            te = posada.get("today_events") or 0
            hc = posada.get("habits_completed") or 0
            ht = posada.get("habits_total") or 0
            msgs = []
            if te > 0:
                msgs.append(f"Tienes {te} evento(s) HOY.")
            if hc < ht:
                msgs.append(f"Faltan {ht - hc} hábito(s) por completar.")
            
            if msgs:
                msg_body = "\n".join(msgs)
                self.app.notify(msg_body, title="🚨 Alerta del Bunker", severity="warning", timeout=8.0)
                try:
                    import subprocess
                    subprocess.Popen(["notify-send", "-a", "Bunker", "-u", "critical", "🚨 Alerta del Bunker", msg_body])
                except Exception:
                    pass
                
                try:
                    self.app.bell()
                except Exception:
                    import sys
                    sys.stdout.write('\a')
                    sys.stdout.flush()

        try:
            # ── STATUS BAR ──
            sb = self.query_one("#status_bar", Label)
            sb.update("[#00ff41]◈ EN VIVO[/] [#555555]│[/] [#00e5ff]SISTEMA: ONLINE[/] [#555555]│[/] [#00ff41]NÚCLEO: ESTABLE[/] [#555555]│[/] [#8b5cf6]TELEMETRÍA: OK[/]")

            # ── PRESTIGIO ──
            posada = data.get("posada") or {}
            guild = posada.get("guild") or {}
            lvl = guild.get("prestige_level", 1)
            pres = guild.get("prestige", 0)
            meta = guild.get("prestige_meta", 100)

            self.query_one("#prestige_title", Label).update(
                f"[#ffb000]⚜  GREMIO  ─  NIVEL {lvl}[/]  [#555555]│[/]  [#c0c0c0]{pres}[/][#555555]/{meta} pts[/]"
            )
            gauge = self.create_prestige_gauge(pres, meta)
            self.query_one("#prestige_gauge", Label).update(gauge)
            self.query_one("#prestige_info", Label).update(
                f"[#555555]Siguiente nivel: {meta - pres} pts restantes[/]"
            )

            # ── MÉTRICAS ──
            dw_history = posada.get("dw_history", [])
            sparkline_str = self.create_sparkline(dw_history)
            self.query_one("#metric_sparkline", Label).update(
                f"  [#8b5cf6]⏱[/]  Actividad 7d [#555555]│[/] {sparkline_str}"
            )

            advs = posada.get("active_adventurers") or []
            self.query_one("#metric_advs", Label).update(
                f"  [#00e5ff]⊕[/]  Aventureros  [#555555]│[/] [bold #00e5ff]{len(advs)}[/] desplegados"
            )

            top = posada.get("top_adventurer") or {}
            top_name = top.get("name", "Nadie")
            top_lvl = top.get("level", 0)
            self.query_one("#metric_leader", Label).update(
                f"  [#ffb000]★[/]  Héroe Líder  [#555555]│[/] [bold #ffb000]{top_name}[/] [dim](Nv.{top_lvl})[/]"
            )

            nw = guild.get("net_worth") or 0
            self.query_one("#metric_wealth", Label).update(
                f"  [#ffd700]◆[/]  Patrimonio   [#555555]│[/] [bold #ffd700]{nw}[/] Talentos"
            )

            hc = posada.get("habits_completed") or 0
            ht = posada.get("habits_total") or 0
            habit_gauge = self.create_gauge(hc, ht, width=10)
            self.query_one("#metric_habits", Label).update(
                f"  [#00ff41]✓[/]  Hábitos Hoy  [#555555]│[/] {habit_gauge} [dim]{hc}/{ht}[/]"
            )

            streak = posada.get("top_streak") or {}
            str_name = streak.get("name", "Ninguna")
            str_val = streak.get("streak", 0)
            flame = "[#ff4444]▲[/]" if str_val > 5 else "[#ffb000]▲[/]"
            self.query_one("#metric_streak", Label).update(
                f"  {flame}  Racha Hábitos[#555555]│[/] [bold]{str_name}[/] [dim]({str_val}d)[/]"
            )

            b = data.get("books") or {}
            b_streak = b.get("streak", 0)
            read_icon = "[#00ff41]▤[/]" if b_streak > 0 else "[#555555]▤[/]"
            self.query_one("#metric_read_streak", Label).update(
                f"  {read_icon}  Racha Lectura[#555555]│[/] [bold #00ff41]{b_streak}[/] [dim]días[/]"
            )

            pt = posada.get("pending_tasks") or 0
            self.query_one("#metric_kanban", Label).update(
                f"  [#00e5ff]▦[/]  Kanban Pend. [#555555]│[/] [bold]{pt}[/] tareas"
            )

            te = posada.get("today_events") or 0
            ev_color = "#ff00ff" if te > 0 else "#555555"
            self.query_one("#metric_calendar", Label).update(
                f"  [{ev_color}]◉[/]  Eventos Hoy  [#555555]│[/] [{ev_color}]{te} programados[/]"
            )

            # ── COLECCIONES ──
            b = data.get("books") or {}
            b_read = b.get("read", 0)
            b_total = b.get("total", 0)
            b_hours = b.get("hours", 0)
            self.query_one("#bar_books", Label).update(self.create_gauge(b_read, max(b_total, 1)))
            self.query_one("#stat_books", Label).update(
                f"  [dim]{b_read}/{b_total} completados • {b_hours}h est.[/]"
            )
            
            health = (b_read / b_total * 100) if b_total > 0 else 0
            if b_total > 0 and health < 50:
                self.query_one("#stat_books_health", Label).update(f"  [#ff4444]⚠️ Tu bóveda acumula polvo ({health:.1f}%)[/]")
            else:
                self.query_one("#stat_books_health", Label).update(f"  [#00ff41]✔ Bóveda Saludable ({health:.1f}%)[/]")

            m = data.get("movies") or {}
            m_watched = m.get("watched", 0)
            m_total = m.get("total", 0)
            m_hours = m.get("hours", 0)
            self.query_one("#bar_movies", Label).update(self.create_gauge(m_watched, max(m_total, 1)))
            self.query_one("#stat_movies", Label).update(
                f"  [dim]{m_watched}/{m_total} vistas • {m_hours}h est.[/]"
            )

            mu = data.get("music") or {}
            mu_listened = mu.get("listened", 0)
            mu_total = mu.get("total", 0)
            mu_hours = mu.get("hours", 0)
            self.query_one("#bar_music", Label).update(self.create_gauge(mu_listened, max(mu_total, 1)))
            self.query_one("#stat_music", Label).update(
                f"  [dim]{mu_listened}/{mu_total} escuchados • {mu_hours}h est.[/]"
            )

            # ── FEED ──
            feed = data.get("feed") or []
            from datetime import datetime
            now = datetime.now()
            for i in range(10):
                lbl = self.query_one(f"#feed_{i}", Label)
                if i < len(feed):
                    ts = now.strftime("%H:%M")
                    lbl.update(f"  [#555555]{ts}[/] [#1a3a4a]│[/] {feed[i]}")
                else:
                    lbl.update("")

        except Exception as e:
            try:
                sb = self.query_one("#status_bar", Label)
                sb.update(f"[#ff4444]◈ ERROR UI ─── {str(e)[:50]} ◈[/]")
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib": self.action_launch_lib()
        elif event.button.id == "btn_movie": self.action_launch_movie()
        elif event.button.id == "btn_music": self.action_launch_music()
        elif event.button.id == "btn_posada": self.action_launch_posada()
        elif event.button.id == "btn_chess": self.action_launch_chess()
        elif event.button.id == "btn_evac": self.app.notify("Mantenimiento.", severity="warning")
        elif event.button.id == "btn_quit": self.app.exit()

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
        import os
        token = os.environ.get("BUNKER_BACKUP_TOKEN", "bunker_local_secure_99")
        try:
            resp = httpx.post(API_BACKUP, headers={"X-Bunker-Token": token}, timeout=15.0)
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
        import os
        token = os.environ.get("BUNKER_BACKUP_TOKEN", "bunker_local_secure_99")
        try:
            resp = httpx.post(API_RESTORE, headers={"X-Bunker-Token": token}, timeout=15.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "Búnker restaurado con éxito. Datos recargados.", title="Restauración Exitosa")
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error al restaurar: {resp.json().get('error', 'Revisa si existe el archivo json.')}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

