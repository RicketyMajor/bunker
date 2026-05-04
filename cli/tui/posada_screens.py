from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Button, Label, TabbedContent, TabPane, DataTable, Log, Input, RadioSet, RadioButton, SelectionList, Select
from textual.containers import Vertical, Horizontal, Grid, VerticalScroll
from textual.reactive import reactive
from textual.binding import Binding
from textual import work
import httpx
from textual_plotext import PlotextPlot

API_POSADA_BASE = "http://127.0.0.1:8000/posada/api/"

# --- GENERADOR DE RELOJ ASCII ---
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
    ':': ["   ", " ▄ ", "   ", " ▀ ", "   "]
}


def get_ascii_time(time_str: str) -> str:
    """Convierte un string como '25:00' en un bloque de texto gigante ASCII."""
    lines = ["", "", "", "", ""]
    for char in time_str:
        if char in ASCII_NUMS:
            for i in range(5):
                lines[i] += ASCII_NUMS[char][i] + "  "
    return "\n".join(lines)

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

# --- MODAL DE RECLUTAMIENTO (AVATAR) ---


class CharacterCreationModal(ModalScreen[dict]):
    """Ventana emergente que fuerza la creación del primer aventurero."""

    CSS = """
    #char_setup_dialog { width: 50; height: auto; padding: 1 2; border: heavy $success; background: $surface; }
    .modal_title { text-style: bold; margin-bottom: 1; text-align: center; width: 100%; color: $warning; }
    .char_label { margin-top: 1; text-style: bold; color: $success; }
    #btn_create_char { width: 100%; margin-top: 2; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="char_setup_dialog"):
            yield Label("📜 CONTRATO DE GREMIO", classes="modal_title")
            yield Label("Tu Gremio está vacío. Debes crear a tu Avatar para comenzar:", classes="char_label")

            yield Input(placeholder="Nombre del héroe...", id="char_name")

            yield Label("Clase:")
            yield Select((("Artífice", "ART"), ("Bárbaro", "BBN"), ("Bardo", "BRD"), ("Clérigo", "CLR"), ("Druida", "DRD"), ("Guerrero", "FTR"), ("Monje", "MNK"), ("Paladín", "PAL"), ("Explorador", "RGR"), ("Pícaro", "ROG"), ("Hechicero", "SOR"), ("Brujo", "WLK"), ("Mago", "WIZ")), id="char_class", value="FTR")

            yield Label("Raza:")
            yield Select((("Humano", "HUM"), ("Enano", "DWF"), ("Elfo", "ELF"), ("Mediano", "HLF"), ("Gnomo", "GNM"), ("Semielfo", "HEF"), ("Semiorco", "HOC"), ("Dracónido", "DGB"), ("Tiefling", "TIE")), id="char_race", value="HUM")

            yield Label("Género:")
            yield Select((("Masculino", "M"), ("Femenino", "F"), ("Otro / Misterioso", "O")), id="char_gender", value="O")

            yield Button("Firmar Contrato y Unirse", variant="success", id="btn_create_char")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_create_char":
            name = self.query_one(
                "#char_name", Input).value or "Aventurero Desconocido"
            cls = self.query_one("#char_class", Select).value
            race = self.query_one("#char_race", Select).value
            gen = self.query_one("#char_gender", Select).value
            self.dismiss({"name": name, "adv_class": cls,
                         "race": race, "gender": gen})

# --- MODAL DE DETALLES DEL AVENTURERO ---


class AdventurerDetailsModal(ModalScreen[None]):
    """Ficha de personaje con scroll y desglose total de riqueza."""

    CSS = """
    #adv_details_dialog { width: 75; height: 35; padding: 1 2; border: double $primary; background: $surface; }
    .title_bar { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; }
    .stats_grid { grid-size: 2; grid-columns: 1fr 1fr; border: solid $accent; padding: 1; margin-bottom: 1; height: auto; }
    .wealth_grid { grid-size: 3; grid-columns: 1fr 1fr 1fr; border: solid $warning; padding: 1; margin-bottom: 1; height: auto; }
    .inv_grid { grid-size: 2; grid-columns: 1fr 1fr; border: solid $success; padding: 1; height: auto; }
    .section_title { color: $success; text-style: bold; margin-top: 1; }
    #btn_close_details { width: 100%; margin-top: 1; }
    """

    def __init__(self, adv_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.adv_data = adv_data

    def compose(self) -> ComposeResult:
        a = self.adv_data
        with Vertical(id="adv_details_dialog"):
            yield Label(f"📜 FICHA: {a.get('name')} | {a.get('class_name')} | {a.get('race')}", classes="title_bar")

            # Usamos VerticalScroll para que quepa todo
            with VerticalScroll():
                yield Label(f"❤️ HP: {a.get('hp')} | Nivel {a.get('level')} ({a.get('xp')} XP)")
                # --- SECCIÓN DE ATRIBUTOS ---
                yield Label("Atributos:", classes="section_title")
                with Grid(classes="stats_grid"):
                    yield Label(f"Fuerza: {a.get('str')}")
                    yield Label(f"Inteligencia: {a.get('int')}")
                    yield Label(f"Destreza: {a.get('dex')}")
                    yield Label(f"Sabiduría: {a.get('wis')}")
                    yield Label(f"Constitución: {a.get('con')}")
                    yield Label(f"Carisma: {a.get('cha')}")
                    yield Label(f"Suerte: {a.get('luk')}")
                # --- SECCIÓN DE EQUIPO ---
                yield Label("Equipo:", classes="section_title")
                with Grid(classes="inv_grid"):
                    yield Label(f"Mano Principal: {a.get('equip_main_hand')}")
                    yield Label(f"Mano Secundaria: {a.get('equip_off_hand')}")
                    yield Label(f"Cabeza: {a.get('equip_head')}")
                    yield Label(f"Torso: {a.get('equip_torso')}")
                    yield Label(f"Manos: {a.get('equip_hands')}")
                    yield Label(f"Piernas: {a.get('equip_legs')}")
                    yield Label(f"Pies: {a.get('equip_feet')}")
                    yield Label(f"Collar: {a.get('equip_necklace')}")
                    yield Label(f"Anillo 1: {a.get('equip_ring_1')}")
                    yield Label(f"Anillo 2: {a.get('equip_ring_2')}")
                    yield Label(f"Brazalete: {a.get('equip_bracelet')}")
                    yield Label(f"Aretes: {a.get('equip_earring')}")
                    yield Label("")

                # --- SECCIÓN DE COMBATE ---
                yield Label("Efectividad en Combate:", classes="section_title")
                with Grid(classes="stats_grid"):
                    yield Label(f"⚔️ Daño Total: {a.get('combat_damage')}")
                    yield Label(f"🛡️ Armadura Total: {a.get('combat_armor')}")
                # --- SECCIÓN DE RIQUEZA ---
                yield Label("Tesoro Personal:", classes="section_title")
                w = a.get('wealth', {})
                with Grid(classes="wealth_grid"):
                    yield Label(f"Marco: {w.get('marco', 0)}")
                    yield Label(f"Real: {w.get('real', 0)}")
                    yield Label(f"Talento: {w.get('talento', 0)}")
                    yield Label(f"Sueldo: {w.get('sueldo', 0)}")
                    yield Label(f"P. Plata: {w.get('silver_penny', 0)}")
                    yield Label(f"Iota: {w.get('iota', 0)}")
                    yield Label(f"P. Cobre: {w.get('copper_penny', 0)}")
                    yield Label(f"Drabín: {w.get('drabin', 0)}")
                    yield Label(f"Ardite: {w.get('ardite', 0)}")
                    yield Label(f"P. Hierro: {w.get('iron_penny', 0)}")
                    yield Label(f"1/2 P. Hierro: {w.get('iron_half_penny', 0)}")

            yield Button("Abrir Mochila", variant="success", id="btn_open_backpack")
            yield Button("Cerrar Ficha", variant="primary", id="btn_close_details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_details":
            self.dismiss(None)
        elif event.button.id == "btn_open_backpack":
            # Lanza el Modal de Inventario sobre este modal
            self.app.push_screen(InventoryModal(
                "adv", self.adv_data["id"], f"Mochila de {self.adv_data['name']}"))

# --- MODAL DE GESTIÓN DE INVENTARIO ---


class InventoryModal(ModalScreen[None]):
    """Visor de mochilas y cofre del gremio."""

    CSS = """
    #inv_dialog { width: 80; height: 35; padding: 1 2; border: heavy $accent; background: $surface; }
    .inv_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; margin-top: 1; align: center middle; }
    .btn_row Button { margin: 0 1; }
    #select_adv { width: 30; margin-right: 1; }
    """

    def __init__(self, target_type: str, target_id: int, title: str, **kwargs):
        super().__init__(**kwargs)
        self.target_type = target_type
        self.target_id = target_id
        self.modal_title = title
        self.slots_cache = []

    def compose(self) -> ComposeResult:
        with Vertical(id="inv_dialog"):
            yield Label(self.modal_title, classes="inv_title")
            yield DataTable(id="inventory_table")

            with Horizontal(classes="btn_row"):
                if self.target_type == "adv":
                    yield Button("Enviar Objeto al Cofre", id="btn_to_guild", variant="primary")
                    yield Button("Vender Chatarra", id="btn_sell", variant="warning")
                else:
                    yield Button("Vender Chatarra", id="btn_sell", variant="warning")
                    # se llena de forma dinámica
                    yield Select([], id="select_adv")
                    yield Button("Dar a Aventurero", id="btn_to_adv", variant="success")

                yield Button("Cerrar", id="btn_close_inv", variant="error")

    def on_mount(self):
        table = self.query_one("#inventory_table", DataTable)
        table.add_columns("Cant.", "Objeto", "Tipo", "Stats")
        self.fetch_inventory()
        if self.target_type == "guild":
            self.fetch_adventurers_for_select()

    @work(thread=True)
    def fetch_adventurers_for_select(self):
        resp = httpx.get(f"{API_POSADA_BASE}status/")
        if resp.status_code == 200:
            advs = resp.json().get("adventurers", [])
            self.app.call_from_thread(self.populate_select, advs)

    def populate_select(self, advs):
        sel = self.query_one("#select_adv", Select)
        sel.set_options([(a["name"], a["id"]) for a in advs])
        if advs:
            sel.value = advs[0]["id"]

    @work(thread=True)
    def fetch_inventory(self):
        resp = httpx.get(
            f"{API_POSADA_BASE}inventory/{self.target_type}/{self.target_id}/")
        if resp.status_code == 200:
            self.slots_cache = resp.json().get("slots", [])
            self.app.call_from_thread(self.refresh_table)

    def refresh_table(self):
        table = self.query_one("#inventory_table", DataTable)
        table.clear()
        for s in self.slots_cache:
            name_rich = f"[[{s['color']}]{s['item_name']}[/]]"
            table.add_row(str(s['qty']), name_rich, s['type'],
                          s['stats'], key=str(s['slot_id']))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_close_inv":
            self.dismiss(None)
            return

        table = self.query_one("#inventory_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            slot_id = int(row_key.value)
        except Exception:
            self.app.notify(
                "Selecciona un objeto de la tabla primero.", severity="warning")
            return

        if event.button.id == "btn_to_guild":
            self.send_action("to_guild", slot_id)
        elif event.button.id == "btn_to_adv":
            sel = self.query_one("#select_adv", Select).value
            if not sel:
                return
            self.send_action("to_adv", slot_id, sel)
        elif event.button.id == "btn_sell":
            self.send_action("sell", slot_id)

    @work(thread=True)
    def send_action(self, action, slot_id, adv_id=None):
        payload = {"action": action, "slot_id": slot_id, "adv_id": adv_id}
        resp = httpx.post(f"{API_POSADA_BASE}inventory/action/", json=payload)
        if resp.status_code == 200:
            self.app.call_from_thread(
                self.app.notify, "Acción completada con éxito.", severity="success")
            self.app.call_from_thread(self.fetch_inventory)

# --- MODAL DE NUEVO HÁBITO ---


class NewHabitModal(ModalScreen[dict]):
    CSS = """
    #habit_dialog { width: 50; height: auto; padding: 1 2; border: solid $success; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="habit_dialog"):
            yield Label("Nuevo Hábito Diario", classes="modal_title")
            yield Input(placeholder="Ej: Ir al gimnasio...", id="habit_name")
            yield Label("Días válidos (0=Lun, 6=Dom. Ej: 0,1,2,3,4):")
            yield Input(value="0,1,2,3,4,5,6", id="habit_days")
            yield Label("Dificultad y Recompensa:")
            yield Select((("Rango S (Épico)", "S"), ("Rango A (Difícil)", "A"), ("Rango B (Medio)", "B"), ("Rango C (Fácil)", "C")), id="habit_diff", value="C")
            with Horizontal(classes="btn_row"):
                yield Button("Añadir", variant="success", id="btn_save_habit")
                yield Button("Cancelar", variant="error", id="btn_cancel_habit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_habit":
            self.dismiss(None)
        elif event.button.id == "btn_save_habit":
            name = self.query_one("#habit_name", Input).value
            diff = self.query_one("#habit_diff", Select).value
            days = self.query_one("#habit_days", Input).value
            if name:
                self.dismiss(
                    {"name": name, "difficulty": diff, "valid_days": days})
            else:
                self.app.notify(
                    "El hábito necesita un nombre.", severity="error")

# --- MODAL DE NUEVO GRÁFICO ---


class NewChartModal(ModalScreen[dict]):
    """Ventana para crear un nuevo lienzo de seguimiento (Tracker)."""

    CSS = """
    #new_chart_dialog { width: 50; height: auto; padding: 1 2; border: solid $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="new_chart_dialog"):
            yield Label("Crear Nuevo Tracker", classes="modal_title")
            yield Input(placeholder="Título (Ej: Horas de Sueño)", id="chart_title")
            yield Input(placeholder="Eje Y (Ej: Horas)", id="chart_y_label", value="Horas")
            yield Input(placeholder="Eje X (Ej: Día del Mes)", id="chart_x_label", value="Día")
            yield Input(placeholder="Meta Eje X (Ej: 30 para un mes)", id="chart_goal_x", value="30")

            yield Label("Polaridad del Gráfico:")
            yield Select(
                (("Positivo (Subir es bueno, ej: Ejercicio)", "POS"),
                 ("Negativo (Bajar es bueno, ej: Redes Sociales)", "NEG")),
                id="chart_polarity", value="POS"
            )

            with Horizontal(classes="btn_row"):
                yield Button("Crear Gráfico", variant="success", id="btn_save_chart")
                yield Button("Cancelar", variant="error", id="btn_cancel_chart")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_chart":
            self.dismiss(None)
        elif event.button.id == "btn_save_chart":
            title = self.query_one("#chart_title", Input).value
            y_lbl = self.query_one("#chart_y_label", Input).value
            x_lbl = self.query_one("#chart_x_label", Input).value
            goal = self.query_one("#chart_goal_x", Input).value
            pol = self.query_one("#chart_polarity", Select).value

            if title and goal.isdigit():
                self.dismiss({
                    "title": title, "y_label": y_lbl, "x_label": x_lbl,
                    "goal_x": int(goal), "polarity": pol
                })
            else:
                self.app.notify(
                    "Faltan datos o la meta no es un número.", severity="error")

# --- MODAL DE AÑADIR DATO AL GRÁFICO ---


class AddChartDataModal(ModalScreen[dict]):
    """Ventana para ingresar coordenadas manuales al gráfico actual."""

    CSS = """
    #add_data_dialog { width: 40; height: auto; padding: 1 2; border: solid $success; background: $surface; }
    .modal_title { text-style: bold; color: $success; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="add_data_dialog"):
            yield Label("Añadir Coordenada (X, Y)", classes="modal_title")
            yield Input(placeholder="Valor Eje X (Ej: 14)", id="input_x")
            yield Input(placeholder="Valor Eje Y (Ej: 2.5)", id="input_y")
            with Horizontal(classes="btn_row"):
                yield Button("Guardar", variant="success", id="btn_save_data")
                yield Button("Cancelar", variant="error", id="btn_cancel_data")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_data":
            self.dismiss(None)
        elif event.button.id == "btn_save_data":
            x_val = self.query_one("#input_x", Input).value
            y_val = self.query_one("#input_y", Input).value
            try:
                # Plotext requiere números para graficar correctamente
                self.dismiss({"x": float(x_val), "y": float(y_val)})
            except ValueError:
                self.app.notify(
                    "Ambos valores deben ser numéricos (Ej: 2.5).", severity="error")


# --- PESTAÑAS ---


class TimerTab(TabPane):
    can_focus = True
    BINDINGS = [("c", "setup_timer", "Configurar"), ("p", "pause_timer",
                                                     "Pausar/Seguir"), ("s", "stop_timer", "Detener")]


class GuildTab(TabPane):
    can_focus = True
    BINDINGS = [("d", "show_details", "Detalles"), ("x", "delete_adventurer",
                                                    "Eliminar"), ("n", "new_adventurer", "Nuevo Avatar")]


class TavernTab(TabPane):
    can_focus = True
    BINDINGS = [("r", "recruit", "Reclutar"),
                ("f", "refresh_tavern", "Invitar Rondas")]


class MissionsTab(TabPane):
    can_focus = True
    BINDINGS = [
        ("m", "complete_habit", "Marcar Hecho"),
        ("+", "add_habit", "Añadir Hábito"),
        ("<", "prev_chart", "Gráfico Anterior"),
        (">", "next_chart", "Siguiente Gráfico"),
        ("a", "add_chart_data", "Añadir Dato al Gráfico"),
        ("n", "new_chart", "Crear Nuevo Gráfico")
    ]

# --- PANTALLA PRINCIPAL ---


class PosadaMainScreen(Screen):
    """Pantalla principal para el sistema de Deep Work y RPG."""

    time_seconds = reactive(25 * 60)
    timer_active = reactive(False)
    is_countdown = reactive(True)

    BINDINGS = [
        # Globales
        ("escape", "app.pop_screen", "Salir Posada"),
        ("q", "app.quit", "Salir Bunker"),
        ("1", "switch_tab('tab_timer')", "Enfoque"),
        ("2", "switch_tab('tab_guild')", "Gremio"),
        ("3", "switch_tab('tab_tavern')", "Taberna"),
        ("4", "switch_tab('tab_missions')", "Misiones"),

        # Controles Ocultos
        Binding("c", "setup_timer", "Configurar", show=False),
        Binding("p", "pause_timer", "Pausar", show=False),
        Binding("s", "stop_timer", "Detener", show=False),
        Binding("d", "show_details", "Detalles", show=False),
        Binding("x", "delete_adventurer", "Eliminar", show=False),
        Binding("n", "new_adventurer", "Nuevo Avatar", show=False),
        Binding("r", "recruit", "Reclutar", show=False),
        Binding("f", "refresh_tavern", "Invitar", show=False),
        Binding("m", "complete_habit", "Marcar Hecho", show=False),
        Binding("+", "add_habit", "Añadir Hábito", show=False),
        Binding("<", "prev_chart", "Gráfico Anterior", show=False),
        Binding(">", "next_chart", "Siguiente Gráfico", show=False),
        Binding("a", "add_chart_data", "Añadir Dato", show=False),
        Binding("g", "new_chart", "Crear Gráfico", show=False),
        Binding("D", "delete_chart", "Borrar Gráfico", show=False),
        Binding("-", "delete_habit", "Borrar Hábito", show=False),
        Binding("u", "undo_habit", "Deshacer Hábito", show=False),
        Binding("R", "claim_chart", "Reclamar Gráfico",
                show=False),

    ]

    CSS = """
    #posada_root { padding: 1 2; }
    
    #focus_layout { height: 25; margin-top: 1; } 
    #left_col { width: 45%; height: 100%; margin-right: 2; }
    #right_col { width: 50%; height: 100%; }
    
    .timer_panel { border: heavy $accent; align: center middle; height: 13; margin-bottom: 1; padding: 1; }
    .party_panel { border: round $success; padding: 1; height: 1fr; }
    .mud_log_panel { border: solid #888888; padding: 0 1; background: #0c0c0c; height: 100%; }
    
    #timer_display { text-style: bold; color: $warning; text-align: center; width: 100%; content-align: center middle; }
    .timer_buttons { height: 3; align: center middle; margin-top: 1; }
    .timer_buttons Button { margin: 0 1; }
    
    .guild_stats { height: auto; border: solid $primary; padding: 1; margin-bottom: 1; }
    .btn_consolidate { margin-top: 1; width: 100%; }
    .half_width { width: 50%; height: 100%; padding: 0 1; }
    #tab_controls {
        dock: bottom;
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        background: $panel;
        border-top: solid $primary;
        padding: 0 1;
    }
    Log {
        text-opacity: 0.9;
    }
    .log-damage {
        color: $error;
        text-style: bold;
    }

    
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="posada_root"):
            with TabbedContent(initial="tab_timer"):

                with TabPane("Sala de Enfoque", id="tab_timer"):
                    with Horizontal(id="focus_layout"):

                        # Columna Izquierda
                        with Vertical(id="left_col"):
                            with Vertical(classes="timer_panel"):
                                # Reloj Gigante
                                yield Label(get_ascii_time("25:00"), id="timer_display")
                                with Horizontal(classes="timer_buttons"):
                                    yield Button("Configurar y Partir", id="btn_setup_timer", variant="success")
                                    # Los botones limpios, sin data_bind
                                    yield Button("Pausar", id="btn_pause_timer", variant="warning")
                                    yield Button("Continuar", id="btn_resume_timer", variant="success")
                                    yield Button("Detener / Huir", id="btn_stop_timer", variant="error")

                            with Vertical(classes="party_panel"):
                                yield Label("Grupo Activo (Max 5)")
                                yield DataTable(id="active_party_table")

                        # Columna Derecha (MUD Log)
                        with Vertical(id="right_col", classes="mud_log_panel"):
                            yield Label("📜 Registro de Eventos")
                            yield Log(id="event_log", highlight=True)

                with TabPane("El Gremio (Bóveda)", id="tab_guild"):
                    with Vertical(classes="guild_stats"):
                        yield Label("Cargando...", id="lbl_guild_level")
                        yield Label("Cargando bóveda...", id="lbl_guild_vault")
                        yield Button("Consolidar Riqueza", id="btn_consolidate", classes="btn_consolidate", variant="warning")
                    yield Label("Todos los Aventureros Reclutados:")
                    yield DataTable(id="all_adventurers_table")

                with TabPane("La Taberna", id="tab_tavern"):
                    yield Label("Aventureros buscando un Gremio (Nivel 1):", classes="section_title")
                    yield DataTable(id="tavern_table")
                    with Horizontal(classes="timer_buttons"):
                        yield Button("Reclutar Seleccionado (r)", id="btn_recruit", variant="success")
                        yield Button("Invitar Rondas (f)", id="btn_refresh_tavern", variant="primary")

                with TabPane("Tablón de Misiones", id="tab_missions"):
                    with Horizontal():
                        # Los Hábitos
                        with Vertical(id="habits_col", classes="half_width"):
                            yield Label("Tareas Diarias (+ Añadir | m Marcar)")
                            yield DataTable(id="missions_table")

                        # Gráfico Analítico
                        with Vertical(id="stats_col", classes="half_width"):
                            yield Label("Cargando gráficos...", id="chart_title_label", classes="section_title")
                            yield PlotextPlot(id="productivity_plot")
        yield Label("", id="tab_controls")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#active_party_table", DataTable).add_columns(
            "Nombre", "Clase", "Raza", "Nivel", "Estado")
        table_adv = self.query_one("#all_adventurers_table", DataTable)
        table_adv.add_columns("Nombre", "Clase", "Nivel",
                              "XP", "Riqueza", "Equipamiento", "Estado")
        self.query_one("#missions_table", DataTable).add_columns(
            "Misión", "Recompensa Base", "Estado")

        self.query_one("#event_log", Log).write_line(
            "La taberna está silenciosa. Esperando órdenes del Maestro...")
        self.clock_ticker = self.set_interval(1, self.tick_timer, pause=True)

        self.query_one("#tavern_table", DataTable).add_columns(
            "Nombre", "Clase", "Raza", "Estadísticas Base (13 pts)")
        self.refresh_tavern_api()  # Llena la taberna al entrar

        # Sincroniza la interfaz con la base de datos
        self.sync_guild_status()
        self.fetch_missions_data()
        self.set_timer_ui_state("idle")
        self.query_one("#tab_timer").focus()
        self.query_one("#tab_controls", Label).update(
            "Sala de Enfoque -> [c] Configurar Expedición  |  [p] Pausar / Seguir  |  [s] Detener / Huir")

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

    @work(thread=True)
    def request_consolidation(self) -> None:
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}guild/consolidate/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "El Cambista ha consolidado tus monedas de menor valor.", severity="success")
                self.sync_guild_status()
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al consolidar riqueza.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "El Cambista no responde.", severity="error")

    def render_guild_status(self, data: dict) -> None:
        """Actualiza los paneles del Gremio con los datos de Django."""
        guild = data.get("guild", {})
        adventurers = data.get("adventurers", [])

        self.adventurers_cache = adventurers

        self.query_one("#lbl_guild_level", Label).update(
            f"Nivel del Maestro: {guild.get('level')} | XP: {guild.get('xp')}")

        inv = guild.get("inventory", {})
        vault_text = (
            f"Marcos: {inv.get('marco', 0)} | Reales: {inv.get('real', 0)} | Talentos: {inv.get('talento', 0)} | Sueldos: {inv.get('sueldo', 0)}\n"
            f"P. Plata: {inv.get('silver_penny', 0)} | Iotas: {inv.get('iota', 0)} | P. Cobre: {inv.get('copper_penny', 0)} | Drabines: {inv.get('drabin', 0)}\n"
            f"Ardites: {inv.get('ardite', 0)} | P. Hierro: {inv.get('iron_penny', 0)} | 1/2 P. Hierro: {inv.get('iron_half_penny', 0)}"
        )
        self.query_one("#lbl_guild_vault", Label).update(vault_text)

        table_adv = self.query_one("#all_adventurers_table", DataTable)
        table_adv.clear()
        for adv in adventurers:
            status = "Enfermería" if adv.get("is_recovering") else "Disponible"

            # En la tabla principal muestra solo un resumen rápido
            resumen_equipo = "Ver Detalles (d)"

            # key=str(adv['id']) ancla la fila de la tabla a la base de datos
            table_adv.add_row(
                adv["name"], adv["class_name"], str(
                    adv["level"]), str(adv["xp"]),
                adv["wealth_summary"], resumen_equipo, status,
                key=str(adv["id"])
            )

        # SI EL GREMIO ESTÁ VACÍO, FUERZA LA CREACIÓN DEL AVATAR
        if not adventurers:
            self.app.push_screen(CharacterCreationModal(),
                                 self.submit_new_character)

    @work(thread=True)
    def submit_new_character(self, result: dict | None) -> None:
        """Envía el nuevo personaje a Django y recarga la interfaz."""
        if result is None:
            return
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}adventurer/create/", json=result, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "¡Avatar creado! Bienvenido a La Posada.", severity="success")
                self.sync_guild_status()
            else:
                # error de cupo lleno
                error_msg = resp.json().get("message", "Error al crear el personaje.")
                self.app.call_from_thread(
                    self.app.notify, error_msg, severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, "Fallo de conexión.", severity="error")

    # --- MÁQUINA DE ESTADOS DE BOTONES ---
    def set_timer_ui_state(self, state: str) -> None:
        """Controla qué botones se ven según el estado del reloj (idle, running, paused)."""
        btn_setup = self.query_one("#btn_setup_timer", Button)
        btn_pause = self.query_one("#btn_pause_timer", Button)
        btn_resume = self.query_one("#btn_resume_timer", Button)
        btn_stop = self.query_one("#btn_stop_timer", Button)

        if state == "idle":
            btn_setup.display = True
            btn_pause.display = False
            btn_resume.display = False
            btn_stop.display = False
            try:
                self.query_one("#active_party_table", DataTable).clear()
            except Exception:
                pass
        elif state == "running":
            btn_setup.display = False
            btn_pause.display = True
            btn_resume.display = False
            btn_stop.display = True
        elif state == "paused":
            btn_setup.display = False
            btn_pause.display = False
            btn_resume.display = True
            btn_stop.display = True

    # --- LÓGICA DEL RELOJ DUAL Y BINDINGS ---
    def watch_time_seconds(self, time_seconds: int) -> None:
        """Actualiza el reloj gigante a cada segundo."""
        minutes, seconds = divmod(time_seconds, 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        try:
            self.query_one("#timer_display", Label).update(
                get_ascii_time(time_str))
        except Exception:
            pass

    def tick_timer(self) -> None:
        """El reloj que reproduce el destino en tiempo real."""
        # Calcula los segundos transcurridos reales
        if self.is_countdown:
            total_sec = getattr(self, 'session_duration_mins', 25) * 60
            elapsed = total_sec - self.time_seconds
        else:
            elapsed = self.time_seconds

        # Revisa si hay un evento programado en este segundo
        for event in getattr(self, 'session_script', []):
            if event["second"] == elapsed:
                # Formatea el timestamp para que se vea como [14:32] en el log
                m, s = divmod(elapsed, 60)
                self.query_one("#event_log", Log).write_line(
                    f"[{m:02d}:{s:02d}] {event['message']}")

        # Lógica normal del reloj
        if self.is_countdown:
            if self.time_seconds > 0:
                self.time_seconds -= 1
            else:
                self.clock_ticker.pause()
                self.timer_active = False
                self.set_timer_ui_state("idle")
                self.handle_session_end(success=True)
        else:
            self.time_seconds += 1

    # --- BINDINGS Y EVENTOS DE INTERFAZ ---
    def action_setup_timer(self) -> None:
        if self.query_one(TabbedContent).active != "tab_timer":
            return
        if not self.timer_active:
            self.app.push_screen(SessionSetupModal(), self.prepare_session)

    def action_pause_timer(self) -> None:
        if self.query_one(TabbedContent).active != "tab_timer":
            return
        if self.timer_active:
            self.clock_ticker.pause()
            self.timer_active = False
            self.set_timer_ui_state("paused")
            self.query_one("#event_log", Log).write_line(
                "La expedición se detiene. Los monstruos acechan...")

    def action_resume_timer(self) -> None:
        if self.query_one(TabbedContent).active != "tab_timer":
            return
        if not self.timer_active and self.time_seconds > 0:
            self.clock_ticker.resume()
            self.timer_active = True
            self.set_timer_ui_state("running")
            self.query_one("#event_log", Log).write_line(
                "Se reanuda la marcha en la oscuridad.")

    def action_stop_timer(self) -> None:
        if self.query_one(TabbedContent).active != "tab_timer":
            return
        if self.timer_active or self.query_one("#btn_resume_timer", Button).display:
            self.clock_ticker.pause()
            self.timer_active = False
            self.set_timer_ui_state("idle")
            success_status = not self.is_countdown
            self.handle_session_end(success=success_status)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_setup_timer":
            self.action_setup_timer()
        elif event.button.id == "btn_pause_timer":
            self.action_pause_timer()
        elif event.button.id == "btn_resume_timer":
            self.action_resume_timer()
        elif event.button.id == "btn_stop_timer":
            self.action_stop_timer()
        elif event.button.id == "btn_consolidate":
            # Llama a la API para ir al cambista
            self.request_consolidation()
        elif event.button.id == "btn_recruit":
            self.action_recruit()
        elif event.button.id == "btn_refresh_tavern":
            self.action_refresh_tavern()

    def action_show_details(self) -> None:
        """Abre la ficha del personaje seleccionado en la tabla del Gremio."""
        if self.query_one(TabbedContent).active != "tab_guild":
            return
        table = self.query_one("#all_adventurers_table", DataTable)
        try:
            # Obtiene la fila donde está el cursor
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            # Busca en el caché el aventurero que coincida con esa llave
            adv_data = next(a for a in getattr(
                self, 'adventurers_cache', []) if str(a['id']) == row_key.value)
            self.app.push_screen(AdventurerDetailsModal(adv_data))
        except Exception:
            self.app.notify(
                "Selecciona un aventurero de la tabla primero.", severity="warning")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Cambia el texto de nuestra Barra de Acción dependiendo de la pestaña."""
        lbl = self.query_one("#tab_controls", Label)
        pane_id = event.pane.id

        if pane_id == "tab_timer":
            lbl.update(
                "Sala de Enfoque -> [c] Configurar Expedición  |  [p] Pausar / Seguir  |  [s] Detener / Huir")
        elif pane_id == "tab_guild":
            lbl.update(
                "El Gremio -> [d] Ver Detalles y Equipo  |  [x] Eliminar Aventurero  |  [n] Reclutar Avatar Inicial")
        elif pane_id == "tab_tavern":
            lbl.update(
                "La Taberna -> [r] Reclutar Seleccionado  |  [f] Pagar Rondas de Cerveza (Refrescar)")
        elif pane_id == "tab_missions":
            lbl.update(
                "Misiones -> [m] Marcar | [u] Deshacer | [-] Borrar | [<][>] Carrusel | [a] Coordenada | [R] Reclamar")

    def action_switch_tab(self, tab_id: str) -> None:
        """Permite navegar súper rápido entre pestañas presionando 1, 2, 3 o 4."""
        self.query_one(TabbedContent).active = tab_id

    # --- FLUJO DE INICIO MUD (PRE-CÁLCULO) ---
    def prepare_session(self, result: dict | None) -> None:
        """Paso 1: Recibe configuración y pide el guion al backend."""
        if result is None:
            return

        log = self.query_one("#event_log", Log)
        log.clear()
        log.write_line("Consultando al Oráculo del Gremio...")

        self.active_party_ids = result.get("party", [])
        self.session_category = result["category"]

        # Si es cronómetro, pide un guion de 120 mins para que no se quede sin eventos
        dur = result["duration"] if result["mode"] == "timer" else 120

        self.request_session_script(
            dur, self.session_category, self.active_party_ids, result)

    @work(thread=True)
    def request_session_script(self, duration: int, category: str, party: list, original_result: dict) -> None:
        """Paso 2: Llamada HTTP asíncrona para iniciar la sesión y traer los eventos."""
        payload = {"duration_minutes": duration,
                   "category": category, "adventurer_ids": party}
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}session/start/", json=payload, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(
                    self.begin_timer_with_script, data, original_result)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error del Oráculo: {resp.status_code}", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Fallo de red al contactar al Gremio.", severity="error")

    def begin_timer_with_script(self, data: dict, result: dict) -> None:
        """Paso 3: Guarda el guion, dibuja la party y arranca el reloj en vivo."""
        self.current_session_id = data.get("session_id")
        self.session_script = data.get("script", [])

        log = self.query_one("#event_log", Log)
        party_table = self.query_one("#active_party_table", DataTable)
        party_table.clear()

        for adv_id in self.active_party_ids:
            for adv in getattr(self, 'adventurers_cache', []):
                if adv["id"] == adv_id:
                    party_table.add_row(adv["name"], adv["class_name"], adv["race"], str(
                        adv["level"]), "⚔️ En mazmorra")
                    break

        self.timer_active = True
        self.set_timer_ui_state("running")

        cat = result["category"]

        if result["mode"] == "timer":
            self.is_countdown = True
            self.session_duration_mins = result["duration"]
            self.time_seconds = result["duration"] * 60
            log.write_line(
                f"\n[Misión: {cat}] El reloj inicia. ¡Que la suerte os acompañe!")
        else:
            self.is_countdown = False
            self.time_seconds = 0
            log.write_line(
                f"\n[Misión: {cat}] Cronómetro iniciado hacia lo desconocido.")

        self.clock_ticker.resume()

    # --- FLUJO DE CIERRE Y BOTÍN ---
    def handle_session_end(self, success: bool):
        log = self.query_one("#event_log", Log)

        if self.is_countdown:
            total_sec = getattr(self, 'session_duration_mins', 25) * 60
            elapsed = total_sec - self.time_seconds
        else:
            elapsed = self.time_seconds

        if success:
            log.write_line("¡Mazmorra completada con éxito!")
        else:
            log.write_line(
                "Has tocado el cuerno de retirada. La party huye.")

        log.write_line("Consolidando resultados con la Bóveda del Gremio...")

        session_id = getattr(self, 'current_session_id', None)
        if session_id:
            self.submit_session_completion(session_id, elapsed)

    @work(thread=True)
    def submit_session_completion(self, session_id: int, survived_seconds: int) -> None:
        """Paso Final: Envía los segundos vividos para calcular el botín oficial."""
        payload = {"session_id": session_id,
                   "survived_seconds": survived_seconds}
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}session/complete/", json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(self.show_loot_summary, data)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error del Motor RPG: {resp.status_code}", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Fallo crítico al reclamar botín.", severity="error")

    def show_loot_summary(self, data: dict) -> None:
        log = self.query_one("#event_log", Log)

        # Imprime los reportes de post-sesión (Diezmo, Tienda, XP)
        for event_msg in data.get("log", []):
            log.write_line(f"📜 {event_msg}")

        # Muestra la ventana de victoria
        engine_details = data.get("engine_details", {})
        self.app.push_screen(LootSummaryModal(engine_details))

        self.sync_guild_status()
        self.time_seconds = 25 * 60
        self.is_countdown = True

# --- FUNCIONES DE GESTIÓN DE AVENTUREROS EN EL GREMIO ---
    def action_delete_adventurer(self) -> None:
        """Elimina al aventurero seleccionado en la tabla."""
        if self.query_one(TabbedContent).active != "tab_guild":
            return

        table = self.query_one("#all_adventurers_table", DataTable)
        try:
            # Obtiene el ID del aventurero desde la llave de la fila
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            adv_id = row_key.value
            self.request_deletion(adv_id)
        except Exception:
            self.app.notify(
                "Selecciona un aventurero de la tabla primero.", severity="warning")

    @work(thread=True)
    def request_deletion(self, adv_id: str) -> None:
        """Llamada asíncrona para borrar el registro en Django."""
        try:
            resp = httpx.delete(
                f"{API_POSADA_BASE}adventurer/delete/{adv_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                self.sync_guild_status()  # Refrescar tabla
            else:
                self.app.call_from_thread(
                    self.app.notify, "No se pudo eliminar al aventurero.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Fallo de conexión con el servidor.", severity="error")

    def action_new_adventurer(self) -> None:
        """Permite crear un nuevo aventurero manualmente si el gremio está vacío."""
        if self.query_one(TabbedContent).active != "tab_guild":
            return

        # Revisa si hay aventureros en el caché
        adventurers = getattr(self, 'adventurers_cache', [])
        if not adventurers:
            self.app.push_screen(CharacterCreationModal(),
                                 self.submit_new_character)
        else:
            self.app.notify(
                "Solo puedes reclutar un nuevo Avatar si el Gremio está vacío.", severity="warning")

    # --- TABERNA ---
    @work(thread=True)
    def refresh_tavern_api(self):
        """Pide al servidor que genere 3 reclutas nuevos."""
        try:
            resp = httpx.get(f"{API_POSADA_BASE}tavern/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.render_tavern, resp.json().get("recruits", []))
        except Exception:
            pass

    def render_tavern(self, recruits):
        self.tavern_cache = recruits
        table = self.query_one("#tavern_table", DataTable)
        table.clear()
        for idx, r in enumerate(recruits):
            s = r["stats"]
            stats_str = f"F:{s['str']} D:{s['dex']} C:{s['con']} I:{s['int']} S:{s['wis']} Ca:{s['cha']} Lu:{s['luk']}"
            table.add_row(r["name"], r["adv_class_display"],
                          r["race_display"], stats_str, key=str(idx))

    def action_refresh_tavern(self) -> None:
        if self.query_one(TabbedContent).active == "tab_tavern":
            self.query_one("#event_log", Log).write_line(
                "🍺 Has pagado unas rondas de cerveza. Nuevos reclutas se acercan a la mesa.")
            self.refresh_tavern_api()

    def action_recruit(self) -> None:
        if self.query_one(TabbedContent).active != "tab_tavern":
            return
        table = self.query_one("#tavern_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            recruit_data = self.tavern_cache[int(row_key.value)]
            self.submit_new_character(recruit_data)
        except Exception:
            self.app.notify(
                "Selecciona a un aventurero de la Taberna primero.", severity="warning")

    # --- TABLÓN DE MISIONES Y GRÁFICOS ---
    @work(thread=True)
    def fetch_missions_data(self):
        """Obtiene hábitos y TODOS los gráficos."""
        try:
            # Hábitos
            r_habits = httpx.get(f"{API_POSADA_BASE}habits/", timeout=5.0)
            if r_habits.status_code == 200:
                data = r_habits.json()
                self.app.call_from_thread(
                    self.render_habits, data.get("habits", []))
                for penalty in data.get("penalties_applied", []):
                    self.app.call_from_thread(
                        self.app.notify, penalty, severity="warning")

            # Gráficos
            r_charts = httpx.get(f"{API_POSADA_BASE}charts/", timeout=5.0)
            if r_charts.status_code == 200:
                charts_data = r_charts.json().get("charts", [])
                self.app.call_from_thread(
                    self.update_charts_cache, charts_data)
        except Exception:
            pass

    def update_charts_cache(self, charts_data):
        self.charts_cache = charts_data
        if not hasattr(self, 'current_chart_index'):
            self.current_chart_index = 0
        self.render_plot()

    def render_plot(self):
        """Dibuja el gráfico activo usando Plotext."""
        if not hasattr(self, 'charts_cache') or not self.charts_cache:
            return

        # Seguridad de índice
        if self.current_chart_index >= len(self.charts_cache):
            self.current_chart_index = 0

        chart_data = self.charts_cache[self.current_chart_index]

        # Actualizar Título del Carrusel
        total = len(self.charts_cache)
        curr = self.current_chart_index + 1
        lbl = self.query_one("#chart_title_label", Label)
        lbl.update(f"◀ [{curr}/{total}] {chart_data['title']} ▶")

        plot_widget = self.query_one("#productivity_plot", PlotextPlot)
        plt = plot_widget.plt
        plt.clear_figure()

        x = chart_data.get("x_data", [])
        y = chart_data.get("y_data", [])

        plt.theme("dark")
        if x and y:
            # Usa plot para líneas continuas en vez de bar
            plt.plot(x, y, marker="braille", color="cyan")
        else:
            plt.title("Presiona 'a' para añadir el primer dato.")

        # Metadatos del gráfico
        plt.title(
            f"Meta: Día {chart_data['goal_x']} | {chart_data['polarity']}")
        plt.xlabel(chart_data['x_label'])
        plt.ylabel(chart_data['y_label'])

        plot_widget.refresh()

    def action_prev_chart(self) -> None:
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if hasattr(self, 'charts_cache') and self.charts_cache:
            self.current_chart_index = (
                self.current_chart_index - 1) % len(self.charts_cache)
            self.render_plot()

    def action_next_chart(self) -> None:
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if hasattr(self, 'charts_cache') and self.charts_cache:
            self.current_chart_index = (
                self.current_chart_index + 1) % len(self.charts_cache)
            self.render_plot()

    # --- ACCIONES DE CREACIÓN DE GRÁFICOS Y DATOS ---
    def action_new_chart(self) -> None:
        """Abre el modal para crear un gráfico si estás en la pestaña de Misiones."""
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        self.app.push_screen(NewChartModal(), self.submit_new_chart)

    @work(thread=True)
    def submit_new_chart(self, result: dict | None) -> None:
        if result is None:
            return
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}charts/create/", json=result, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                # Al recargar, envía el carrusel al último gráfico creado
                self.current_chart_index = -1
                self.app.call_from_thread(self.fetch_missions_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al crear el gráfico.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "El Gremio no responde.", severity="error")

    def action_add_chart_data(self) -> None:
        """Abre el modal para añadir coordenadas (X,Y) al gráfico actual."""
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if not hasattr(self, 'charts_cache') or not self.charts_cache:
            self.app.notify(
                "No hay gráficos activos. Crea uno primero (n).", severity="warning")
            return
        self.app.push_screen(AddChartDataModal(), self.submit_chart_data)

    @work(thread=True)
    def submit_chart_data(self, result: dict | None) -> None:
        if result is None:
            return

        current_chart = self.charts_cache[self.current_chart_index]
        payload = {
            "chart_id": current_chart["id"],
            "x_value": result["x"],
            "y_value": result["y"]
        }

        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}charts/add_point/", json=payload, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_missions_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al guardar la coordenada.", severity="error")
        except Exception:
            pass

    def action_delete_chart(self) -> None:
        """Elimina el gráfico que se está viendo actualmente."""
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if not hasattr(self, 'charts_cache') or not self.charts_cache:
            self.app.notify("No hay gráficos para borrar.", severity="warning")
            return

        current_chart = self.charts_cache[self.current_chart_index]
        self.request_chart_deletion(current_chart["id"])

    @work(thread=True)
    def request_chart_deletion(self, chart_id: int) -> None:
        try:
            resp = httpx.delete(
                f"{API_POSADA_BASE}charts/delete/{chart_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "Gráfico destruido en la Bóveda.", severity="success")
                self.current_chart_index = 0  # Volvemos al primer gráfico por seguridad
                self.app.call_from_thread(self.fetch_missions_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, "No se pudo borrar el gráfico.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Fallo de conexión.", severity="error")

    def render_habits(self, habits):
        self.habits_cache = habits
        table = self.query_one("#missions_table", DataTable)
        table.clear()
        for h in habits:
            # Usa Rich para darle color a la palabra Completado
            status = "[bold green]Completado[/]" if h["completed_today"] else "[gray]Pendiente[/]"

            # Construye el texto visual combinando la racha y el estado
            racha = h.get("current_streak", 0)
            estado_visual = f"🔥 Racha: {racha} | {status}"

            table.add_row(h["name"], h["difficulty"],
                          estado_visual, key=str(h["id"]))

    def action_add_habit(self) -> None:
        if self.query_one(TabbedContent).active == "tab_missions":
            self.app.push_screen(NewHabitModal(), self.submit_new_habit)

    @work(thread=True)
    def submit_new_habit(self, result: dict | None) -> None:
        if result is None:
            return
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}habits/create/", json=result, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.fetch_missions_data)
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Fallo al crear hábito.", severity="error")

    def action_complete_habit(self) -> None:
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        table = self.query_one("#missions_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            self.request_habit_completion(row_key.value)
        except Exception:
            self.app.notify("Selecciona un hábito primero.",
                            severity="warning")

    @work(thread=True)
    def request_habit_completion(self, habit_id: str) -> None:
        try:
            resp = httpx.post(f"{API_POSADA_BASE}habits/complete/",
                              json={"habit_id": habit_id}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_missions_data)
                # Refrescar fatiga y XP en el gremio
                self.app.call_from_thread(self.sync_guild_status)
            else:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="warning")
        except Exception:
            pass

    def action_delete_habit(self) -> None:
        """Captura el ID del hábito y llama al hilo de borrado."""
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        table = self.query_one("#missions_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            self.request_habit_deletion(row_key.value)
        except Exception:
            self.app.notify(
                "Selecciona un hábito de la tabla primero.", severity="warning")

    @work(thread=True)
    def request_habit_deletion(self, habit_id: str) -> None:
        """Pide a Django que destruya el hábito."""
        try:
            resp = httpx.delete(
                f"{API_POSADA_BASE}habits/delete/{habit_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_missions_data)
            else:
                self.app.call_from_thread(
                    self.app.notify, "No se pudo borrar el hábito.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Error de conexión con la base de datos.", severity="error")

    def action_undo_habit(self) -> None:
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        table = self.query_one("#missions_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            resp = httpx.post(f"{API_POSADA_BASE}habits/undo/",
                              json={"habit_id": row_key.value})
            if resp.status_code == 200:
                self.app.notify(resp.json().get("message"), severity="warning")
                self.fetch_missions_data()
                self.sync_guild_status()
            else:
                self.app.notify(resp.json().get("message"), severity="error")
        except Exception:
            pass

    def action_claim_chart(self) -> None:
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if not hasattr(self, 'charts_cache') or not self.charts_cache:
            return

        current_chart = self.charts_cache[self.current_chart_index]
        try:
            resp = httpx.post(f"{API_POSADA_BASE}charts/claim/",
                              json={"chart_id": current_chart["id"]}, timeout=5.0)
            if resp.status_code == 200:
                self.app.notify(resp.json().get("message"), severity="success")
                self.fetch_missions_data()
                self.sync_guild_status()
            else:
                self.app.notify(resp.json().get("message"), severity="warning")
        except Exception:
            pass
