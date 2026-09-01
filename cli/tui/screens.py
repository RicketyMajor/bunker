from textual.containers import VerticalScroll, Vertical, Grid
from textual.widgets import Label, Button
from textual.widgets import ProgressBar
from datetime import datetime
from textual.reactive import reactive
import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, Button, Label
from textual.containers import VerticalScroll, Vertical, Horizontal, Grid
from textual import work
from .constants import API_LIBRARY, API_TRACKER, API_MOVIES
from .movie_screens import MovieMainScreen
from textual.widgets import ProgressBar
from .modals import ConfirmModal, EvacuationModal, BriefingScreen
from .constants import API_BACKUP, API_RESTORE



# The launcher clock's digits. Lived in `posada_screens.py` until the 2026-08-27 split and was
# imported from there at module level — which is why removing that module would have stopped the
# whole TUI from starting. It has nothing to do with the Posada; it is glyphs.
ASCII_NUMS = {
    '0': ["███", "█ █", "█ █", "█ █", "███"],
    '1': [" ██", "  █", "  █", "  █", "███"],
    '2': ["███", "  █", "███", "█  ", "███"],
    '3': ["███", "  █", "███", "  █", "███"],
    '4': ["█ █", "█ █", "███", "  █", "  █"],
    '5': ["███", "█  ", "███", "  █", "███"],
    '6': ["███", "█  ", "███", "█ █", "███"],
    '7': ["███", "  █", "  █", "  █", "  █"],
    '8': ["███", "█ █", "███", "█ █", "███"],
    '9': ["███", "█ █", "███", "  █", "███"],
    ':': ["   ", " ▄ ", "   ", " ▀ ", "   "],
}


class WeeklyReviewScreen(Screen):
    """La revisión semanal. Se muestra una vez por semana ISO y espera si no abres Bunker.

    Full-screen, not a modal, because the spec says full-screen — and because it is the one
    thing the Bunker says that is worth stopping for.
    """

    BINDINGS = [("escape", "cerrar", "Cerrar"), ("enter", "cerrar", "Cerrar")]

    def __init__(self, review: dict) -> None:
        super().__init__()
        self.review = review

    def compose(self) -> ComposeResult:
        with Vertical(id="review_box"):
            yield Label(f"◈ REVISIÓN DE LA SEMANA {self.review['semana']} ◈",
                        classes="modal_title")
            yield Label(f"contra la semana {self.review['anterior']}", classes="review_sub")
            for m in self.review["metricas"]:
                delta = m["actual"] - m["previa"]
                # Rich markup, not Textual CSS variables: `[$success]` inside a Label is not
                # a colour, it is four literal characters on screen.
                color = "green" if delta > 0 else ("red" if delta < 0 else "dim")
                signo = f"+{delta}" if delta > 0 else str(delta)
                yield Label(f"[bold]{m['etiqueta']:<18}[/] {m['actual']:>6}   "
                            f"[dim](semana previa {m['previa']})[/]  [{color}]{signo}[/]")

            # Aquí iba el bloque de prestigio: dos números y nunca el neto, más el desglose
            # por fuente. `_revision()` dejó de emitir `prestigio` el 2026-08-27 —el ledger se
            # fue a La Posada— y el `.get()` lo mató en silencio, igual que las cinco claves de
            # `BriefingScreen`. Ambas pantallas comen del mismo payload y el barrido del split
            # sólo pasó por el productor.

            yield Button("Continuar", variant="success", id="btn_cerrar_review")

    def action_cerrar(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


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


class BunkerLauncherScreen(Screen):
    """Centro de Mando Cyberpunk — Dashboard principal del Bunker."""

    dashboard_data = reactive({})
    _clock_blink = reactive(True)
    _boot_done = reactive(False)

    BINDINGS = [
        ("1", "launch_lib", "Biblioteca"),
        ("2", "launch_movie", "Videoclub"),
        ("3", "launch_music", "Disquera"),
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

    /* ── SYSTEM ROW: RELOJ ── */
    #system_row {
        height: 9;
        layout: horizontal;
        margin-bottom: 0;
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
            # El panel del Gremio estaba a la izquierda del reloj hasta el 2026-08-27.
            with Horizontal(id="system_row"):
                with Vertical(id="clock_panel"):
                    yield Label("", id="ascii_clock")
                    yield Label("", id="clock_date")

            # ── 3. BODY ROW ──
            with Horizontal(id="body_row"):
                # Panel Métricas
                with Vertical(id="metrics_panel", classes="cyber_panel"):
                    yield Label("◈ MÉTRICAS DEL SISTEMA ◈", classes="cyber_title")
                    yield Label("────────────────────────────", classes="cyber_separator")
                    # Ocho de estas nueve líneas eran de la Posada — aventureros, patrimonio,
                    # hábitos, kanban, calendario — y se fueron con ella el 2026-08-27.
                    yield Label("  Racha Lectura│ [dim]--[/]", id="metric_read_streak", classes="metric_line")

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
                yield Button("BACKUP", id="btn_evac", classes="mod_btn_warn")
                yield Button("SALIR", id="btn_quit", classes="mod_btn_danger")

    def on_mount(self) -> None:
        self.tick_clock()
        self.set_interval(1.0, self.tick_clock)
        self.fetch_dashboard()
        self.set_interval(15.0, self.fetch_dashboard)
        # Una sola vez, sin `set_interval`: el parte es de entrada, no un refresco.
        self.fetch_briefing()

    def tick_clock(self) -> None:
        from datetime import datetime

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

    @work(thread=True)
    def fetch_briefing(self) -> None:
        """El parte diario. Si no contesta, el Launcher aparece igual: eso es el requisito."""
        try:
            from .constants import API_BRIEFING, API_BRIEFING_SEEN
            import httpx
            resp = httpx.get(API_BRIEFING, timeout=3.0)
            if resp.status_code != 200:
                return
            datos = resp.json()
            # LAS DOS, no una u otra. La razón original era `logros_nuevos`: el briefing era
            # el único que los pintaba y el POST de abajo adelanta `last_entry_at` pase lo que
            # pase, así que mostrar sólo la revisión los quemaba en silencio. Los logros
            # salieron con la Posada el 2026-08-27 y esa razón ya no existe. El orden se
            # mantiene por la de al lado, que sigue viva: `marcar_visto` sólo debe marcar lo
            # que se llegó a PINTAR, y para eso hay que pintar las dos antes del POST.
            #
            # El briefing va primero y la revisión encima, así que la revisión sigue siendo
            # lo que se ve al entrar —que es lo que pide la spec— y al cerrarla aparece el
            # briefing debajo en vez de perderse.
            con_revision = bool(datos.get("show_review") and datos.get("review"))
            self.app.call_from_thread(self.mostrar_briefing, datos)
            if con_revision:
                self.app.call_from_thread(self.mostrar_review, datos["review"])
            # El POST va DESPUÉS de mostrarlo, y ese orden es el requisito: marca como visto
            # sólo lo que se llegó a pintar. Al revés, un GET que expira dejaría los logros
            # marcados sin que nadie los haya leído nunca, y no hay vuelta atrás.
            #
            # `con_revision` es lo que se PINTÓ, no lo que el payload pidió: si `show_review`
            # viniera true con `review` en None, marcar la semana como vista quemaría la
            # revisión de esa semana sin que nadie la haya visto, y no hay vuelta atrás.
            try:
                httpx.post(API_BRIEFING_SEEN, json={"con_revision": con_revision}, timeout=3.0)
            except Exception:
                pass
        # El `except` desnudo es el requisito, no descuido: si el endpoint falla o tarda, el
        # Launcher tiene que aparecer igual. No lo conviertas en un crash.
        except Exception:
            pass

    def mostrar_briefing(self, datos: dict) -> None:
        self.app.push_screen(BriefingScreen(datos))

    def mostrar_review(self, review: dict) -> None:
        self.app.push_screen(WeeklyReviewScreen(review))

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
            # Las dos alertas de arranque — eventos de calendario y hábitos pendientes — eran
            # de la Posada. El inventario no tiene nada urgente que decir al entrar.
            msgs = []
            
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

            # ── MÉTRICAS ──
            # El bloque PRESTIGIO y ocho de las nueve métricas eran de la Posada. La racha de
            # lectura es la única que no lo era, y es lo que queda.
            b = data.get("books") or {}
            b_streak = b.get("streak", 0)
            read_icon = "[#00ff41]▤[/]" if b_streak > 0 else "[#555555]▤[/]"
            self.query_one("#metric_read_streak", Label).update(
                f"  {read_icon}  Racha Lectura[#555555]│[/] [bold #00ff41]{b_streak}[/] [dim]días[/]"
            )

            # ── COLECCIONES ──
            b = data.get("books") or {}
            b_read = b.get("read", 0)
            b_total = b.get("total", 0)
            self.query_one("#bar_books", Label).update(self.create_gauge(b_read, max(b_total, 1)))
            self.query_one("#stat_books", Label).update(
                f"  [dim]{b_read}/{b_total} completados[/]"
            )
            
            health = (b_read / b_total * 100) if b_total > 0 else 0
            if b_total > 0 and health < 50:
                self.query_one("#stat_books_health", Label).update(f"  [#ff4444]⚠️ Tu bóveda acumula polvo ({health:.1f}%)[/]")
            else:
                self.query_one("#stat_books_health", Label).update(f"  [#00ff41]✔ Bóveda Saludable ({health:.1f}%)[/]")

            m = data.get("movies") or {}
            m_watched = m.get("watched", 0)
            m_total = m.get("total", 0)
            self.query_one("#bar_movies", Label).update(self.create_gauge(m_watched, max(m_total, 1)))
            self.query_one("#stat_movies", Label).update(
                f"  [dim]{m_watched}/{m_total} vistas[/]"
            )

            mu = data.get("music") or {}
            mu_listened = mu.get("listened", 0)
            mu_total = mu.get("total", 0)
            self.query_one("#bar_music", Label).update(self.create_gauge(mu_listened, max(mu_total, 1)))
            self.query_one("#stat_music", Label).update(
                f"  [dim]{mu_listened}/{mu_total} escuchados[/]"
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

    # ── FUNCIONES DE SEGURIDAD ──
    @work(thread=True)
    def process_backup(self) -> None:
        from cli.config import BACKUP_TOKEN as token
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
        from cli.config import BACKUP_TOKEN as token
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

