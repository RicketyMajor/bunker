from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Button, Label, TabbedContent, TabPane, DataTable, Log, Input, RadioSet, RadioButton
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive

# --- MODAL DE CONFIGURACIÓN ---


class SessionSetupModal(ModalScreen[dict]):
    """Ventana emergente para configurar la sesión de Deep Work."""

    CSS = """
    #session_setup_dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    .modal_title { text-style: bold; margin-bottom: 1; text-align: center; width: 100%; }
    .form_buttons { height: 3; align: center middle; margin-top: 1; }
    .form_buttons Button { margin: 0 1; }
    .input_label { margin-top: 1; text-style: bold; color: $success; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="session_setup_dialog"):
            yield Label("⚙️ Configurar Expedición", classes="modal_title")

            yield Label("Categoría de la tarea:", classes="input_label")
            yield Input(placeholder="Ej. Inglés, Programación...", id="input_category")

            yield Label("Modo de tiempo:", classes="input_label")
            with RadioSet(id="time_mode"):
                yield RadioButton("Temporizador (Cuenta Regresiva)", id="mode_timer", value=True)
                yield RadioButton("Cronómetro (Libre)", id="mode_stopwatch")

            yield Label("Duración (minutos) - Solo Temporizador:", classes="input_label")
            yield Input(value="25", id="input_duration", type="integer")

            with Horizontal(classes="form_buttons"):
                yield Button("Comenzar", variant="success", id="btn_confirm")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
        elif event.button.id == "btn_confirm":
            mode = "timer" if self.query_one(
                "#mode_timer", RadioButton).value else "stopwatch"
            cat = self.query_one("#input_category", Input).value or "General"

            try:
                dur = int(self.query_one("#input_duration", Input).value)
            except ValueError:
                dur = 25

            self.dismiss({"mode": mode, "category": cat, "duration": dur})


# --- PANTALLA PRINCIPAL ---
class PosadaMainScreen(Screen):
    """Pantalla principal para el sistema de Deep Work y RPG."""

    # Variables reactivas unificadas
    time_seconds = reactive(25 * 60)
    timer_active = reactive(False)
    is_countdown = reactive(True)  # True = Temporizador, False = Cronómetro

    BINDINGS = [
        ("escape", "app.pop_screen", "Volver al Launcher"),
        ("q", "app.quit", "Salir de Bunker"),
        ("c", "setup_timer", "Configurar Expedición"),
        ("s", "stop_timer", "Detener / Huir")
    ]

    CSS = """
    #posada_root { padding: 1 2; height: 100%; }
    #focus_grid { grid-size: 2 2; grid-columns: 1fr 1fr; grid-rows: 1fr 1fr; height: 100%; grid-gutter: 1 2; }
    .timer_panel { border: heavy $accent; padding: 1; height: 100%; align: center middle; }
    .party_panel { border: round $success; padding: 1; height: 100%; }
    .mud_log_panel { border: solid #888888; padding: 0 1; background: #0c0c0c; row-span: 2; height: 100%; }
    
    #timer_display { text-style: bold; color: $warning; text-align: center; width: 100%; }
    
    .timer_buttons { height: auto; width: 100%; align: center middle; margin-top: 1; }
    .timer_buttons Button { margin: 0 1; }
    
    .guild_stats { height: auto; border: solid $primary; padding: 1; margin-bottom: 1; }
    .btn_consolidate { margin-top: 1; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="posada_root"):
            with TabbedContent(initial="tab_timer"):

                with TabPane("Sala de Enfoque", id="tab_timer"):
                    with Grid(id="focus_grid"):
                        with Vertical(classes="timer_panel"):
                            yield Label("25:00", id="timer_display")
                            with Horizontal(classes="timer_buttons"):
                                yield Button("Configurar y Partir", id="btn_setup_timer", variant="success")
                                yield Button("Detener / Huir", id="btn_stop_timer", variant="error")

                        with Vertical(classes="mud_log_panel"):
                            yield Label("📜 Registro de Eventos")
                            yield Log(id="event_log", highlight=True)

                        with Vertical(classes="party_panel"):
                            yield Label("🗡️ Grupo Activo (Max 5)")
                            yield DataTable(id="active_party_table")

                with TabPane("El Gremio (Bóveda)", id="tab_guild"):
                    with Vertical(classes="guild_stats"):
                        yield Label("Nivel del Maestro: 1 | XP: 0")
                        yield Label("Bóveda: 0 Talentos, 0 Marcos, 0 Ardites...")
                        yield Button("Consolidar Riqueza (Mesa del Cambista)", id="btn_consolidate", classes="btn_consolidate", variant="warning")
                    yield Label("Todos los Aventureros Reclutados:")
                    yield DataTable(id="all_adventurers_table")

                with TabPane("Tablón de Misiones", id="tab_missions"):
                    yield Label("Marca tus hábitos diarios para obtener recompensas rápidas.")
                    yield DataTable(id="missions_table")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#active_party_table", DataTable).add_columns(
            "Nombre", "Clase", "Raza", "Nivel", "Estado")
        self.query_one("#all_adventurers_table", DataTable).add_columns(
            "Nombre", "Clase", "Nivel", "XP", "Riqueza")
        self.query_one("#missions_table", DataTable).add_columns(
            "Misión", "Recompensa Base", "Estado")

        self.query_one("#event_log", Log).write_line(
            "La taberna está silenciosa. Esperando órdenes del Maestro...")
        self.clock_ticker = self.set_interval(1, self.tick_timer, pause=True)

    # --- LÓGICA DEL RELOJ DUAL ---
    def watch_time_seconds(self, time_seconds: int) -> None:
        """Formatea el tiempo (sea hacia arriba o hacia abajo)."""
        minutes, seconds = divmod(time_seconds, 60)
        self.query_one("#timer_display", Label).update(
            f"{minutes:02d}:{seconds:02d}")

    def tick_timer(self) -> None:
        if self.is_countdown:
            if self.time_seconds > 0:
                self.time_seconds -= 1
            else:
                self.clock_ticker.pause()
                self.timer_active = False
                self.handle_session_end(success=True)
        else:
            # Modo Cronómetro: cuenta infinita hacia adelante
            self.time_seconds += 1

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_setup_timer":
            if not self.timer_active:
                # Llama al Modal y espera la respuesta en la función start_session
                self.app.push_screen(SessionSetupModal(), self.start_session)

        elif event.button.id == "btn_stop_timer":
            if self.timer_active:
                self.clock_ticker.pause()
                self.timer_active = False
                # En cronómetro, detenerse siempre es un "éxito" porque no hay meta
                success_status = not self.is_countdown
                self.handle_session_end(success=success_status)

    def start_session(self, result: dict | None) -> None:
        """Callback que se ejecuta cuando el Modal se cierra."""
        if result is None:
            return  # El usuario pulsó Cancelar

        log = self.query_one("#event_log", Log)
        self.timer_active = True

        cat = result["category"]

        if result["mode"] == "timer":
            self.is_countdown = True
            self.time_seconds = result["duration"] * 60
            log.write_line(
                f"\n⏳ [Misión: {cat}] Temporizador de {result['duration']} min iniciado.")
        else:
            self.is_countdown = False
            self.time_seconds = 0
            log.write_line(
                f"\n⏱️ [Misión: {cat}] Cronómetro libre iniciado. ¡Adelante!")

        self.clock_ticker.resume()

    def handle_session_end(self, success: bool):
        log = self.query_one("#event_log", Log)
        if success:
            log.write_line("✅ ¡Exploración completada con éxito!")
            log.write_line(
                "💰 Calculando botín y experiencia... (Pendiente API Backend)")
        else:
            log.write_line(
                "❌ Has cancelado la misión. La party huyó perdiendo su progreso.")
            self.time_seconds = 25 * 60
            self.is_countdown = True

    # --- ACCIONES DE TECLADO (BINDINGS) ---
    def action_setup_timer(self) -> None:
        """Se ejecuta al presionar 'c' o el botón de configurar."""
        if not self.timer_active:
            self.app.push_screen(SessionSetupModal(), self.start_session)

    def action_stop_timer(self) -> None:
        """Se ejecuta al presionar 's' o el botón de detener."""
        if self.timer_active:
            self.clock_ticker.pause()
            self.timer_active = False
            success_status = not self.is_countdown
            self.handle_session_end(success=success_status)

    # --- EVENTOS DE BOTONES VISUALES ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Redirige los clics visuales a las mismas acciones del teclado."""
        if event.button.id == "btn_setup_timer":
            self.action_setup_timer()
        elif event.button.id == "btn_stop_timer":
            self.action_stop_timer()
