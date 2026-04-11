from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Button, Label, TabbedContent, TabPane, DataTable, Log, Input, RadioSet, RadioButton, SelectionList
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive
from textual import work
import httpx

API_POSADA_BASE = "http://127.0.0.1:8000/posada/api/"

# --- MODAL DE CONFIGURACIÓN ---


class SessionSetupModal(ModalScreen[dict]):
    """Ventana emergente para configurar la sesión y elegir la party."""

    CSS = """
    #session_setup_dialog { width: 50; height: auto; padding: 1 2; border: heavy $accent; background: $surface; }
    .modal_title { text-style: bold; margin-bottom: 1; text-align: center; width: 100%; }
    .form_buttons { height: 3; align: center middle; margin-top: 1; }
    .form_buttons Button { margin: 0 1; }
    .input_label { margin-top: 1; text-style: bold; color: $success; }
    #party_select { height: 6; border: solid $primary; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="session_setup_dialog"):
            yield Label("Configurar Expedición", classes="modal_title")

            yield Label("Categoría de la tarea:", classes="input_label")
            yield Input(placeholder="Ej. Inglés, Programación...", id="input_category")

            yield Label("Modo de tiempo:", classes="input_label")
            with RadioSet(id="time_mode"):
                yield RadioButton("Temporizador (Cuenta Regresiva)", id="mode_timer", value=True)
                yield RadioButton("Cronómetro (Libre)", id="mode_stopwatch")

            yield Label("Duración (minutos) - Solo Temporizador:", classes="input_label")
            yield Input(value="25", id="input_duration", type="integer")

            yield Label("Reclutar Party (Máx 5):", classes="input_label")
            yield SelectionList(id="party_select")

            with Horizontal(classes="form_buttons"):
                yield Button("Comenzar", variant="success", id="btn_confirm")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_mount(self) -> None:
        """Al abrir el modal, buscamos a los aventureros en la taberna."""
        self.fetch_available_adventurers()

    @work(thread=True)
    def fetch_available_adventurers(self) -> None:
        try:
            resp = httpx.get(f"{API_POSADA_BASE}status/", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(
                    self.populate_party_list, data.get("adventurers", []))
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, "El Gremio está incomunicado (Revisa Docker).", severity="error")

    def populate_party_list(self, adventurers: list) -> None:
        selection = self.query_one("#party_select", SelectionList)
        for adv in adventurers:
            if not adv.get("is_recovering"):
                label = f"{adv['name']} - {adv['class_name']} (Nv. {adv['level']})"
                selection.add_option((label, adv['id']))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
        elif event.button.id == "btn_confirm":
            mode = "timer" if self.query_one(
                "#mode_timer", RadioButton).value else "stopwatch"
            cat = self.query_one("#input_category", Input).value or "General"

            # Obtener los IDs seleccionados
            party_ids = self.query_one("#party_select", SelectionList).selected

            if len(party_ids) > 5:
                self.app.notify(
                    "¡No caben más de 5 aventureros en la mazmorra!", severity="warning")
                return

            try:
                dur = int(self.query_one("#input_duration", Input).value)
            except ValueError:
                dur = 25

            self.dismiss({"mode": mode, "category": cat,
                         "duration": dur, "party": party_ids})

# --- MODAL DE BOTÍN ---


class LootSummaryModal(ModalScreen[None]):
    """Ventana emergente que muestra el botín y la XP obtenidos."""

    CSS = """
    #loot_dialog { width: 50; height: auto; padding: 1 2; border: heavy $warning; background: $surface; }
    .loot_title { text-style: bold; color: $warning; margin-bottom: 1; text-align: center; width: 100%; }
    .loot_text { margin-bottom: 1; }
    #btn_claim_loot { width: 100%; margin-top: 1; }
    """

    def __init__(self, result_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.result_data = result_data

    def compose(self) -> ComposeResult:
        with Vertical(id="loot_dialog"):
            yield Label("¡Expedición Exitosa!", classes="loot_title")

            base_xp = self.result_data.get("base_xp", 0)
            loot = self.result_data.get("loot", {})

            yield Label(f"Experiencia Base: {base_xp} XP", classes="loot_text")

            loot_lines = []
            for coin, amount in loot.items():
                if amount > 0:
                    # Formatea el nombre de la moneda para que se vea bonito
                    coin_name = coin.replace('_', ' ').title()
                    loot_lines.append(f"- {amount} {coin_name}")

            if loot_lines:
                yield Label("Botín Encontrado:\n" + "\n".join(loot_lines), classes="loot_text")
            else:
                yield Label("Solo encontraste polvo esta vez.", classes="loot_text")

            yield Button("Reclamar y Volver al Gremio", variant="primary", id="btn_claim_loot")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_claim_loot":
            self.dismiss(None)

# --- PANTALLA PRINCIPAL ---


class PosadaMainScreen(Screen):
    """Pantalla principal para el sistema de Deep Work y RPG."""

    time_seconds = reactive(25 * 60)
    timer_active = reactive(False)
    is_countdown = reactive(True)

    BINDINGS = [
        ("c", "setup_timer", "Configurar Expedición"),
        ("s", "stop_timer", "Detener / Huir"),
        ("escape", "app.pop_screen", "Volver al Launcher"),
        ("q", "app.quit", "Salir de Bunker"),


    ]

    CSS = """
    #posada_root { padding: 1 2; }
    
    /* Layout forzado para evitar colapsos en el TabPane */
    #focus_layout { height: 25; margin-top: 1; } /* Altura fija obligatoria */
    #left_col { width: 45%; height: 100%; margin-right: 2; }
    #right_col { width: 50%; height: 100%; }
    
    .timer_panel { border: heavy $accent; align: center middle; height: 10; margin-bottom: 1; }
    .party_panel { border: round $success; padding: 1; height: 14; }
    .mud_log_panel { border: solid #888888; padding: 0 1; background: #0c0c0c; height: 100%; }
    
    #timer_display { text-style: bold; color: $warning; }
    .timer_buttons { height: 3; align: center middle; margin-top: 1; }
    .timer_buttons Button { margin: 0 1; }
    
    .guild_stats { height: auto; border: solid $primary; padding: 1; margin-bottom: 1; }
    .btn_consolidate { margin-top: 1; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="posada_root"):
            with TabbedContent(initial="tab_timer"):

                with TabPane("Sala de Enfoque", id="tab_timer"):
                    with Horizontal(id="focus_layout"):

                        with Vertical(id="left_col"):
                            with Vertical(classes="timer_panel"):
                                yield Label("25:00", id="timer_display")
                                with Horizontal(classes="timer_buttons"):
                                    yield Button("Configurar y Partir", id="btn_setup_timer", variant="success")
                                    yield Button("Detener / Huir", id="btn_stop_timer", variant="error")

                            with Vertical(classes="party_panel"):
                                yield Label("Grupo Activo (Max 5)")
                                yield DataTable(id="active_party_table")

                        # Columna Derecha (50% de la pantalla)
                        with Vertical(id="right_col", classes="mud_log_panel"):
                            yield Label("📜 Registro de Eventos")
                            yield Log(id="event_log", highlight=True)

                with TabPane("El Gremio (Bóveda)", id="tab_guild"):
                    with Vertical(classes="guild_stats"):
                        yield Label("Cargando...", id="lbl_guild_level")
                        yield Label("Cargando bóveda...", id="lbl_guild_vault")
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
        table_adv = self.query_one("#all_adventurers_table", DataTable)
        table_adv.add_columns("Nombre", "Clase", "Nivel",
                              "XP", "Riqueza", "Estado")
        self.query_one("#missions_table", DataTable).add_columns(
            "Misión", "Recompensa Base", "Estado")

        self.query_one("#event_log", Log).write_line(
            "La taberna está silenciosa. Esperando órdenes del Maestro...")
        self.clock_ticker = self.set_interval(1, self.tick_timer, pause=True)

        # Sincroniza la interfaz con la base de datos
        self.sync_guild_status()

    # --- LLAMADAS A LA API ---
    @work(thread=True)
    def sync_guild_status(self) -> None:
        try:
            resp = httpx.get(f"{API_POSADA_BASE}status/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.render_guild_status, resp.json())
        except Exception as e:
            pass

    def render_guild_status(self, data: dict) -> None:
        """Actualiza los paneles del Gremio con los datos de Django."""
        guild = data.get("guild", {})
        adventurers = data.get("adventurers", [])

        self.query_one("#lbl_guild_level", Label).update(
            f"Nivel del Maestro: {guild.get('level')} | XP: {guild.get('xp')}")

        inv = guild.get("inventory", {})
        vault_text = f"Bóveda: {inv.get('marco', 0)} Marcos, {inv.get('talento', 0)} Talentos, {inv.get('sueldo', 0)} Sueldos, {inv.get('iota', 0)} Iotas, {inv.get('ardite', 0)} Ardites"
        self.query_one("#lbl_guild_vault", Label).update(vault_text)

        table_adv = self.query_one("#all_adventurers_table", DataTable)
        table_adv.clear()
        for adv in adventurers:
            status = "Enfermería" if adv.get("is_recovering") else "Disponible"
            table_adv.add_row(adv["name"], adv["class_name"], str(
                adv["level"]), str(adv["xp"]), adv["wealth_summary"], status)

    # --- RELOJ DUAL Y BINDINGS ---
    def watch_time_seconds(self, time_seconds: int) -> None:
        minutes, seconds = divmod(time_seconds, 60)
        try:
            self.query_one("#timer_display", Label).update(
                f"{minutes:02d}:{seconds:02d}")
        except Exception:
            pass

    def tick_timer(self) -> None:
        if self.is_countdown:
            if self.time_seconds > 0:
                self.time_seconds -= 1
            else:
                self.clock_ticker.pause()
                self.timer_active = False
                self.handle_session_end(success=True)
        else:
            self.time_seconds += 1

    def action_setup_timer(self) -> None:
        if not self.timer_active:
            self.app.push_screen(SessionSetupModal(), self.start_session)

    def action_stop_timer(self) -> None:
        if self.timer_active:
            self.clock_ticker.pause()
            self.timer_active = False
            success_status = not self.is_countdown
            self.handle_session_end(success=success_status)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_setup_timer":
            self.action_setup_timer()
        elif event.button.id == "btn_stop_timer":
            self.action_stop_timer()

    def start_session(self, result: dict | None) -> None:
        if result is None:
            return

        log = self.query_one("#event_log", Log)
        self.timer_active = True

        self.active_party_ids = result.get("party", [])
        cat = result["category"]
        self.session_category = cat

        if result["mode"] == "timer":
            self.is_countdown = True
            self.session_duration_mins = result["duration"]
            self.time_seconds = result["duration"] * 60
            log.write_line(
                f"\n⏳ [Misión: {cat}] Temporizador de {result['duration']} min iniciado con {len(self.active_party_ids)} aventureros.")
        else:
            self.is_countdown = False
            self.time_seconds = 0
            log.write_line(
                f"\n⏱️ [Misión: {cat}] Cronómetro libre iniciado con {len(self.active_party_ids)} aventureros.")

        self.clock_ticker.resume()

    def handle_session_end(self, success: bool):
        log = self.query_one("#event_log", Log)
        if success:
            log.write_line("¡Exploración completada con éxito!")
            log.write_line(
                "Enviando reporte al Gremio (Calculando en la Bóveda)...")

            # Determina los minutos reales a enviar a la BD
            if self.is_countdown:
                duration_mins = getattr(self, 'session_duration_mins', 25)
            else:
                # En cronómetro, los segundos que hayan pasado
                duration_mins = self.time_seconds // 60

            # Previene que se gane "0" si se hacen pruebas rápidas
            if duration_mins < 1:
                duration_mins = 1

            cat = getattr(self, 'session_category', 'General')
            party = getattr(self, 'active_party_ids', [])

            self.submit_session(duration_mins, cat, party)
        else:
            log.write_line(
                "Has cancelado la misión. La party huyó perdiendo su progreso.")
            self.time_seconds = 25 * 60
            self.is_countdown = True

    @work(thread=True)
    def submit_session(self, duration: int, category: str, party: list) -> None:
        """Envía los datos de la sesión terminada a Django."""
        payload = {
            "duration_minutes": duration,
            "category": category,
            "adventurer_ids": party
        }
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}session/complete/", json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(self.show_loot_summary, data)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error del Motor RPG: {resp.status_code}", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, "Fallo crítico al reclamar botín.", severity="error")

    def show_loot_summary(self, data: dict) -> None:
        """Se ejecuta cuando la API devuelve los resultados con éxito."""
        log = self.query_one("#event_log", Log)

        # Escribe los logs narrativos (MUD Log) del motor en la terminal
        for event_msg in data.get("log", []):
            log.write_line(f"📜 {event_msg}")

        # Muestra la ventana emergente de victoria
        engine_details = data.get("engine_details", {})
        self.app.push_screen(LootSummaryModal(engine_details))

        # Recarga silenciosamente los paneles del Gremio para reflejar el nuevo dinero
        self.sync_guild_status()

        # Resetea el reloj
        self.time_seconds = 25 * 60
        self.is_countdown = True
