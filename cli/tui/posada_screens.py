from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Button, Label, TabbedContent, TabPane, DataTable, RichLog, Input, RadioSet, RadioButton, SelectionList, Select, TextArea
from textual.containers import Vertical, Horizontal, Grid, VerticalScroll
from textual.reactive import reactive
from textual.binding import Binding
from textual import work
import httpx
import datetime as _dt
import calendar as _cal
from textual_plotext import PlotextPlot

API_POSADA_BASE = "http://127.0.0.1:8009/posada/api/"

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

# --- MODAL DE RENOMBRAR AVENTURERO ---


class RenameAdventurerModal(ModalScreen[str | None]):
    """Modal para cambiar el nombre de un aventurero."""

    CSS = """
    #rename_dialog { width: 50; height: auto; padding: 1 2; border: heavy $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .form_buttons { height: 3; align: center middle; margin-top: 1; }
    .form_buttons Button { margin: 0 1; }
    """

    def __init__(self, current_name: str, **kwargs):
        super().__init__(**kwargs)
        self.current_name = current_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rename_dialog"):
            yield Label("Renombrar Aventurero", classes="modal_title")
            yield Input(value=self.current_name, placeholder="Nuevo nombre", id="input_new_name")
            with Horizontal(classes="form_buttons"):
                yield Button("Confirmar", variant="success", id="btn_confirm_rename")
                yield Button("Cancelar", variant="error", id="btn_cancel_rename")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_rename":
            self.dismiss(None)
        elif event.button.id == "btn_confirm_rename":
            new_name = self.query_one("#input_new_name", Input).value.strip()
            if new_name:
                self.dismiss(new_name)
            else:
                self.app.notify("El nombre no puede estar vacío.", severity="warning")

# --- MODAL DE RENOMBRAR AVENTURERO ---


class ConfirmResetModal(ModalScreen[bool]):
    """Modal de confirmación para reiniciar el Gremio."""

    CSS = """
    #confirm_reset_dialog { width: 60; height: auto; padding: 1 2; border: heavy $error; background: $surface; }
    .modal_title { text-style: bold; color: $error; text-align: center; margin-bottom: 1; width: 100%; }
    .warning_text { color: $warning; text-align: center; margin-bottom: 1; }
    .form_buttons { height: 3; align: center middle; margin-top: 1; }
    .form_buttons Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_reset_dialog"):
            yield Label("⚠️ ADVERTENCIA DE REINICIO ⚠️", classes="modal_title")
            yield Label("¿Estás absolutamente seguro de que deseas borrar todos los Aventureros, el Cofre y las Mejoras? El Gremio volverá a Nivel 1. Esta acción NO se puede deshacer.", classes="warning_text")
            yield Label("Escribe 'CONFIRMAR' para proceder:")
            yield Input(placeholder="Escribe CONFIRMAR", id="input_confirm_reset")
            with Horizontal(classes="form_buttons"):
                yield Button("¡Borrar Todo!", variant="error", id="btn_confirm_reset")
                yield Button("Cancelar", variant="success", id="btn_cancel_reset")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_reset":
            self.dismiss(False)
        elif event.button.id == "btn_confirm_reset":
            val = self.query_one("#input_confirm_reset", Input).value.strip()
            if val == "CONFIRMAR":
                self.dismiss(True)
            else:
                self.app.notify("Debes escribir 'CONFIRMAR' exactamente para proceder.", severity="error")

# --- MODAL DE DETALLES DEL AVENTURERO ---


class AdventurerDetailsModal(ModalScreen[None]):
    """Ficha de personaje interactiva con scroll, lore de objetos y grimorio."""

    CSS = """
    /* Cambiamos height de 40 a 90% para que nunca desborde tu monitor */
    #adv_details_dialog { width: 85; height: 90%; padding: 1 2; border: double $primary; background: $surface; }
    .title_bar { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; }
    
    .stats_grid { grid-size: 2; grid-columns: 1fr 1fr; border: solid $accent; padding: 1; margin-bottom: 1; height: auto; }
    .skills_grid { grid-size: 3; grid-columns: 1fr 1fr 1fr; border: solid $success; padding: 1; margin-bottom: 1; height: auto; }
    .wealth_grid { grid-size: 3; grid-columns: 1fr 1fr 1fr; border: solid $warning; padding: 1; margin-bottom: 1; height: auto; }
    .section_title { color: $success; text-style: bold; margin-top: 1; margin-bottom: 1; }
    
    #equipment_table { height: 10; border: solid $success; margin-bottom: 1; }
    #item_description { width: 100%; height: auto; min-height: 4; border: dashed $accent; padding: 1; color: $text-muted; margin-bottom: 1; background: $panel; }
    #grimoire_table { height: 1fr; border: solid $primary; margin-bottom: 1; }
    
    /* Obliga al contenedor de pestañas a respetar el límite de la ventana */
    TabbedContent { height: 1fr; margin-bottom: 1; }
    
    /* Anclamos los botones al fondo para que nunca desaparezcan */
    .btn_row { dock: bottom; height: 3; align: center middle; }
    .btn_row Button { margin: 0 1; }
    #btn_unequip { width: 100%; margin-bottom: 1; }
    """

    def __init__(self, adv_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.adv_data = adv_data

    def compose(self) -> ComposeResult:
        a = self.adv_data
        with Vertical(id="adv_details_dialog"):
            yield Label("", id="lbl_title_bar", classes="title_bar")

            with TabbedContent():
                # --- PESTAÑA 1: HOJA DE PERSONAJE (Scroll con todo lo físico) ---
                with TabPane("Hoja de Personaje", id="tab_stats"):
                    with VerticalScroll():
                        yield Label("", id="lbl_top_info")

                        yield Label("Atributos Base:", classes="section_title")
                        yield Grid(id="grid_stats", classes="stats_grid")

                        yield Label("Talentos y Competencias (D&D):", classes="section_title")
                        yield Grid(id="grid_skills", classes="skills_grid")

                        yield Label("Efectividad en Combate:", classes="section_title")
                        yield Grid(id="grid_combat", classes="stats_grid")

                        yield Label("Equipamiento Actual (Selecciona para Inspeccionar):", classes="section_title")
                        yield DataTable(id="equipment_table", cursor_type="row")
                        yield Label("Selecciona un objeto de la tabla para analizarlo.", id="item_description")
                        yield Button("Desequipar Objeto Seleccionado", variant="warning", id="btn_unequip")

                        yield Label("Tesoro Personal:", classes="section_title")
                        yield Grid(id="grid_wealth", classes="wealth_grid")

                # --- PESTAÑA 2: GRIMORIO ---
                with TabPane("Grimorio Arcano/Marcial", id="tab_grimoire"):
                    with VerticalScroll():
                        yield Label("Habilidades Memorizadas:", classes="section_title")
                        yield DataTable(id="grimoire_table", cursor_type="row")

            # --- BOTONES SIEMPRE VISIBLES EN LA RAÍZ DEL MODAL ---
            with Horizontal(classes="btn_row"):
                yield Button("Abrir Mochila", variant="success", id="btn_open_backpack")
                yield Button("Renombrar", variant="warning", id="btn_rename_adv")
                yield Button("Consolidar Riqueza", variant="primary", id="btn_consolidate_adv")
                yield Button("Cerrar Ficha", variant="error", id="btn_close_details")

    def on_mount(self):
        # 1. Poblar Tabla de Equipo
        table = self.query_one("#equipment_table", DataTable)
        table.add_columns("Ranura", "Objeto Equipado")

        # 2. Poblar Tabla del Grimorio
        grim_table = self.query_one("#grimoire_table", DataTable)
        grim_table.add_columns("Habilidad", "Tipo / Gasto", "Nivel Req.")

        self.populate_tables()
        self.update_ui()

    def update_ui(self):
        a = self.adv_data
        self.query_one("#lbl_title_bar", Label).update(f"📜 FICHA: {a.get('name')} | {a.get('reputation_title', 'Novato')} | {a.get('class_name')} | {a.get('race')}")
        self.query_one("#lbl_top_info", Label).update(f"❤️ HP: {a.get('hp')} | Nivel {a.get('level')} ({a.get('xp')} XP) | 🛡️ Superadas: {a.get('sessions_survived', 0)} | 💀 Bajas: {a.get('monsters_killed', 0)}")

        # Update stats
        g_stats = self.query_one("#grid_stats", Grid)
        g_stats.remove_children()
        g_stats.mount(
            Label(f"Fuerza: {a.get('str')}"), Label(f"Inteligencia: {a.get('int')}"),
            Label(f"Destreza: {a.get('dex')}"), Label(f"Sabiduría: {a.get('wis')}"),
            Label(f"Constitución: {a.get('con')}"), Label(f"Carisma: {a.get('cha')}"),
            Label(f"Suerte: {a.get('luk')}")
        )

        # Update skills
        g_skills = self.query_one("#grid_skills", Grid)
        g_skills.remove_children()
        skill_labels = []
        for skill_name, skill_val in a.get('rpg_skills', {}).items():
            color = "bold green" if skill_val > 0 else ("bold red" if skill_val < 0 else "white")
            skill_labels.append(Label(f"{skill_name}: [{color}]{skill_val:+d}[/]"))
        if skill_labels:
            g_skills.mount(*skill_labels)

        # Update combat
        g_combat = self.query_one("#grid_combat", Grid)
        g_combat.remove_children()
        g_combat.mount(
            Label(f"⚔️ Daño Total: {a.get('combat_damage')}"),
            Label(f"🛡️ Armadura Total: {a.get('combat_armor')}")
        )

        # Update wealth
        g_wealth = self.query_one("#grid_wealth", Grid)
        g_wealth.remove_children()
        w = a.get('wealth', {})
        g_wealth.mount(
            Label(f"Marco: {w.get('marco', 0)}"), Label(f"Real: {w.get('real', 0)}"),
            Label(f"Talento: {w.get('talento', 0)}"), Label(f"Sueldo: {w.get('sueldo', 0)}"),
            Label(f"P. Plata: {w.get('silver_penny', 0)}"), Label(f"Iota: {w.get('iota', 0)}"),
            Label(f"P. Cobre: {w.get('copper_penny', 0)}"), Label(f"Drabín: {w.get('drabin', 0)}"),
            Label(f"Ardite: {w.get('ardite', 0)}"), Label(f"P. Hierro: {w.get('iron_penny', 0)}"),
            Label(f"1/2 P. Hierro: {w.get('iron_half_penny', 0)}")
        )

    def populate_tables(self):
        table = self.query_one("#equipment_table", DataTable)
        table.clear()

        eq = self.adv_data.get("equipment", {})
        slots = [
            ("Mano Principal", "equip_main_hand"), ("Mano Secundaria", "equip_off_hand"),
            ("Cabeza", "equip_head"), ("Torso", "equip_torso"), ("Manos", "equip_hands"),
            ("Piernas", "equip_legs"), ("Pies", "equip_feet"), ("Collar", "equip_necklace"),
            ("Anillo 1", "equip_ring_1"), ("Anillo 2", "equip_ring_2"),
            ("Brazalete", "equip_bracelet"), ("Aretes", "equip_earring")
        ]
        for name, key in slots:
            if eq:
                item_info = eq.get(
                    key, {"name": "Vacío", "desc": "Ranura vacía."})
                table.add_row(name, item_info["name"], key=key)
            else:
                # Fallback de seguridad
                item_str = self.adv_data.get(key, "Vacío")
                table.add_row(name, item_str, key=key)

        grim_table = self.query_one("#grimoire_table", DataTable)
        grim_table.clear()
        for skill in self.adv_data.get("grimoire", []):
            grim_table.add_row(
                skill["name"], skill["type"], str(skill["req_level"]))

    @work(thread=True)
    def fetch_my_data_and_refresh(self):
        try:
            resp = httpx.get(f"{API_POSADA_BASE}status/", timeout=5.0)
            if resp.status_code == 200:
                advs = resp.json().get("adventurers", [])
                my_data = next((a for a in advs if a["id"] == self.adv_data["id"]), None)
                if my_data:
                    self.adv_data = my_data
                    self.app.call_from_thread(self.populate_tables)
                    self.app.call_from_thread(self.update_ui)
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Captura el evento del cursor para el Panel de Lore."""
        if event.data_table.id == "equipment_table":
            row_key = event.row_key.value
            eq = self.adv_data.get("equipment", {})
            if eq:
                item_info = eq.get(
                    row_key, {"desc": "Ningún objeto equipado."})
                self.query_one("#item_description", Label).update(
                    item_info["desc"])
            else:
                self.query_one("#item_description", Label).update(
                    "Objeto sin descripción.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_details":
            self.dismiss(None)
        elif event.button.id == "btn_open_backpack":
            self.app.push_screen(InventoryModal(
                "adv", self.adv_data["id"], f"Mochila de {self.adv_data['name']}"), lambda _: self.fetch_my_data_and_refresh())
        elif event.button.id == "btn_unequip":
            table = self.query_one("#equipment_table", DataTable)
            try:
                row_key = table.coordinate_to_cell_key(
                    table.cursor_coordinate).row_key
                self.request_unequip(row_key.value)
            except Exception:
                self.app.notify(
                    "Selecciona un objeto para desequipar.", severity="warning")
        elif event.button.id == "btn_rename_adv":
            self.app.push_screen(
                RenameAdventurerModal(self.adv_data["name"]),
                self.handle_rename_result)
        elif event.button.id == "btn_consolidate_adv":
            self.request_consolidate()

    @work(thread=True)
    def request_consolidate(self):
        resp = httpx.post(f"{API_POSADA_BASE}adventurer/{self.adv_data['id']}/consolidate/")
        if resp.status_code == 200:
            self.app.call_from_thread(
                self.app.notify, resp.json().get("message"), severity="success")
            self.fetch_my_data_and_refresh()
        else:
            self.app.call_from_thread(
                self.app.notify, "Error al consolidar la riqueza.", severity="error")

    def handle_rename_result(self, new_name: str | None) -> None:
        if new_name is not None:
            self.request_rename(new_name)

    @work(thread=True)
    def request_rename(self, new_name: str):
        resp = httpx.patch(
            f"{API_POSADA_BASE}adventurer/{self.adv_data['id']}/rename/", json={"name": new_name})
        if resp.status_code == 200:
            self.app.call_from_thread(
                self.app.notify, resp.json().get("message"), severity="success")
            self.fetch_my_data_and_refresh()
        else:
            self.app.call_from_thread(
                self.app.notify, "Error al renombrar el aventurero.", severity="error")

    @work(thread=True)
    def request_unequip(self, slot_type: str):
        resp = httpx.post(
            f"{API_POSADA_BASE}adventurer/{self.adv_data['id']}/unequip/", json={"slot_type": slot_type})
        if resp.status_code == 200:
            self.app.call_from_thread(
                self.app.notify, resp.json().get("message"), severity="success")
            self.fetch_my_data_and_refresh()
        else:
            self.app.call_from_thread(
                self.app.notify, resp.json().get("error"), severity="error")


# --- MODAL DE GESTIÓN DE INVENTARIO ---

class InventoryModal(ModalScreen[None]):
    """Visor de mochilas y cofre del gremio."""

    CSS = """
    #inv_dialog { width: 100; height: 35; padding: 1 2; border: heavy $accent; background: $surface; }
    .inv_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    #inventory_table { height: 1fr; border: solid $success; margin-bottom: 1; }
    #item_description_inv { width: 100%; height: auto; min-height: 4; border: dashed $accent; padding: 1; color: $text-muted; margin-bottom: 1; background: $panel; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    #select_adv { width: 20; margin-right: 1; }
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
            yield DataTable(id="inventory_table", cursor_type="row")
            yield Label("Selecciona un objeto de la tabla para analizarlo.", id="item_description_inv")

            with Horizontal(classes="btn_row"):
                if self.target_type == "adv":
                    # Textos corregidos para que se vean bien
                    yield Button("Equipar", id="btn_equip", variant="success")
                    yield Button("Enviar al Cofre", id="btn_to_guild", variant="primary")
                    yield Button("Vender Chatarra", id="btn_sell", variant="warning")
                else:
                    yield Button("Vender Chatarra", id="btn_sell", variant="warning")
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

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "inventory_table":
            try:
                row_key = event.row_key.value
                slot_id = int(row_key)
                slot_data = next((s for s in self.slots_cache if s["slot_id"] == slot_id), None)
                if slot_data:
                    self.query_one("#item_description_inv", Label).update(slot_data.get("desc", "Sin descripción."))
            except Exception:
                pass

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
        elif event.button.id == "btn_equip":
            self.send_action("equip", slot_id)

    @work(thread=True)
    def send_action(self, action, slot_id, adv_id=None):
        payload = {"action": action, "slot_id": slot_id, "adv_id": adv_id}
        resp = httpx.post(f"{API_POSADA_BASE}inventory/action/", json=payload)
        if resp.status_code == 200:
            self.app.call_from_thread(
                self.app.notify, resp.json().get("message"), severity="success")
            self.app.call_from_thread(self.fetch_inventory)
        else:
            self.app.call_from_thread(
                self.app.notify, resp.json().get("error"), severity="error")


class GuildUpgradesModal(ModalScreen[None]):
    """Ventana para gastar las ganancias en mejoras de la base."""

    CSS = """
    #upgrades_dialog { width: 85; height: 35; padding: 1 2; border: heavy $warning; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    #upgrades_table { height: 1fr; border: solid $primary; margin-bottom: 1; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="upgrades_dialog"):
            yield Label("🔨 Mejoras de Infraestructura del Gremio", classes="modal_title")
            yield DataTable(id="upgrades_table", cursor_type="row")
            with Horizontal(classes="btn_row"):
                yield Button("Comprar Seleccionada", id="btn_buy_upgrade", variant="success")
                yield Button("Cerrar Tienda", id="btn_close_upgrades", variant="error")

    def on_mount(self):
        table = self.query_one("#upgrades_table", DataTable)
        table.add_columns("Mejora", "Descripción",
                          "Costo", "Req. Nivel", "Estado")
        self.fetch_upgrades()

    @work(thread=True)
    def fetch_upgrades(self):
        try:
            resp = httpx.get(f"{API_POSADA_BASE}guild/upgrades/", timeout=5.0)
            if resp.status_code == 200:
                self.upgrades_cache = resp.json().get("upgrades", [])
                self.app.call_from_thread(self.refresh_table)
        except Exception:
            pass

    def refresh_table(self):
        table = self.query_one("#upgrades_table", DataTable)
        table.clear()
        for u in getattr(self, 'upgrades_cache', []):
            # Colorear estado visual
            st = u['status']
            color = "green" if st == "Adquirido" else (
                "red" if st == "Bloqueado" else "yellow")
            status_fmt = f"[bold {color}]{st}[/]"
            cost_fmt = f"{u['cost_amount']} {u['cost_coin']}"

            table.add_row(u['name'], u['description'], cost_fmt, str(
                u['req_level']), status_fmt, key=u['key'])

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_close_upgrades":
            self.dismiss(None)
        elif event.button.id == "btn_buy_upgrade":
            table = self.query_one("#upgrades_table", DataTable)
            try:
                row_key = table.coordinate_to_cell_key(
                    table.cursor_coordinate).row_key
                self.request_purchase(row_key.value)
            except Exception:
                self.app.notify(
                    "Selecciona una mejora primero.", severity="warning")

    @work(thread=True)
    def request_purchase(self, upgrade_key: str):
        try:
            resp = httpx.post(f"{API_POSADA_BASE}guild/upgrades/buy/",
                              json={"key": upgrade_key}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_upgrades)
            else:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("error"), severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Fallo de conexión.", severity="error")

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
            yield Label("Tipo de Tarea:")
            yield Select((("Buen Hábito", "GOOD"), ("Mal Hábito", "BAD")), id="habit_type", value="GOOD")
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
            is_bad = self.query_one("#habit_type", Select).value == "BAD"
            if name:
                self.dismiss({"name": name, "difficulty": diff,
                             "valid_days": days, "is_bad_habit": is_bad})
            else:
                self.app.notify(
                    "El hábito necesita un nombre.", severity="error")

# --- MODAL DE NUEVO GRÁFICO ---


class NewChartModal(ModalScreen[dict]):
    CSS = """
    #new_chart_dialog { width: 60; height: auto; padding: 1 2; border: solid $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    .grid_inputs { grid-size: 2; grid-columns: 1fr 1fr; grid-rows: auto; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="new_chart_dialog"):
            yield Label("Crear Nuevo Tracker", classes="modal_title")
            yield Input(placeholder="Título (Ej: Horas de Deep Work)", id="chart_title")

            with Grid(classes="grid_inputs"):
                yield Input(placeholder="Eje X Label", id="chart_x_label", value="Día")
                yield Input(placeholder="Eje Y Label", id="chart_y_label", value="Horas")
                yield Input(placeholder="X Mínimo (Ej: 1)", id="chart_x_min", value="1")
                yield Input(placeholder="X Máximo/Meta (Ej: 30)", id="chart_goal_x", value="30")
                yield Input(placeholder="Y Mínimo (Ej: 0)", id="chart_y_min", value="0")
                yield Input(placeholder="Y Máximo (Ej: 6)", id="chart_y_max", value="6")

            yield Label("Polaridad del Gráfico:")
            yield Select((("Positivo (Subir es bueno)", "POS"), ("Negativo (Bajar es bueno)", "NEG")), id="chart_polarity", value="POS")

            with Horizontal(classes="btn_row"):
                yield Button("Crear", variant="success", id="btn_save_chart")
                yield Button("Cancelar", variant="error", id="btn_cancel_chart")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_chart":
            self.dismiss(None)
        elif event.button.id == "btn_save_chart":
            try:
                self.dismiss({
                    "title": self.query_one("#chart_title", Input).value,
                    "y_label": self.query_one("#chart_y_label", Input).value,
                    "x_label": self.query_one("#chart_x_label", Input).value,
                    "x_min": float(self.query_one("#chart_x_min", Input).value),
                    "goal_x": int(self.query_one("#chart_goal_x", Input).value),
                    "y_min": float(self.query_one("#chart_y_min", Input).value),
                    "y_max": float(self.query_one("#chart_y_max", Input).value),
                    "polarity": self.query_one("#chart_polarity", Select).value
                })
            except ValueError:
                self.app.notify(
                    "Asegúrate de que los rangos numéricos sean válidos.", severity="error")

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
            yield Input(placeholder="Valor Eje X (Ej: 14)", id="input_x", type="integer")
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
                self.dismiss({"x": int(x_val), "y": float(y_val)})
            except ValueError:
                self.app.notify(
                    "X debe ser entero, Y puede ser decimal (Ej: 2.5).", severity="error")


class ChartDetailsModal(ModalScreen[None]):
    """Modal que muestra el progreso detallado del gráfico: puntos cubiertos y faltantes."""

    CSS = """
    #chart_details_dialog { width: 65; height: auto; max-height: 80%; padding: 1 2; border: double $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .detail_section { margin-top: 1; text-style: bold; color: $success; }
    .detail_content { margin-bottom: 1; }
    .progress_bar { color: $accent; text-style: bold; }
    .missing_list { color: $error; }
    .covered_list { color: $success; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, chart_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.chart_data = chart_data

    def compose(self) -> ComposeResult:
        c = self.chart_data
        covered = c.get("covered_count", 0)
        total = c.get("total_expected", 0)
        missing = c.get("missing_points", [])
        pct = (covered / total * 100) if total > 0 else 0

        # Barra visual de progreso
        filled = int(pct / 5)  # 20 bloques
        bar = "█" * filled + "░" * (20 - filled)

        with Vertical(id="chart_details_dialog"):
            yield Label(f"📊 Inspección: {c['title']}", classes="modal_title")

            yield Label("Configuración:", classes="detail_section")
            yield Label(f"  Eje X: {c['x_label']} — Rango [{int(c['x_min'])} → {c['goal_x']}]", classes="detail_content")
            yield Label(f"  Eje Y: {c['y_label']} — Rango [{c['y_min']} → {c['y_max']}]", classes="detail_content")
            yield Label(f"  Polaridad: {c['polarity']}", classes="detail_content")

            yield Label("Progreso:", classes="detail_section")
            yield Label(f"  [{bar}] {covered}/{total} ({pct:.0f}%)", classes="progress_bar")

            if missing:
                if len(missing) <= 30:
                    missing_str = ", ".join(str(m) for m in missing)
                else:
                    missing_str = ", ".join(str(m) for m in missing[:30]) + f" ... (+{len(missing)-30} más)"
                yield Label("Puntos Faltantes:", classes="detail_section")
                yield Label(f"  {missing_str}", classes="missing_list")
            else:
                yield Label("¡COMPLETO! Todos los puntos cubiertos. Reclama tu recompensa (R).", classes="covered_list")

            # Mostrar puntos ingresados
            x_data = c.get("x_data", [])
            y_data = c.get("y_data", [])
            if x_data:
                yield Label("Puntos Ingresados:", classes="detail_section")
                with VerticalScroll():
                    entries = [f"  X={int(x)} → Y={y}" for x, y in zip(x_data, y_data)]
                    yield Label("\n".join(entries[-50:]), classes="detail_content")  # Últimos 50

            with Horizontal(classes="btn_row"):
                yield Button("Cerrar", variant="primary", id="btn_close_details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_details":
            self.dismiss(None)


class ChartRewardModal(ModalScreen[None]):
    """Modal que muestra la recompensa obtenida al completar un gráfico."""

    CSS = """
    #chart_reward_dialog { width: 55; height: auto; padding: 1 2; border: heavy $warning; background: $surface; }
    .reward_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .reward_text { margin-bottom: 1; text-align: center; }
    .reward_grade { text-style: bold; text-align: center; margin-bottom: 1; }
    #btn_claim_reward { width: 100%; margin-top: 1; }
    """

    def __init__(self, reward_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.reward_data = reward_data

    def compose(self) -> ComposeResult:
        r = self.reward_data
        grade = r.get("grade", "C")
        grade_colors = {"S": "bold yellow", "A": "bold magenta", "B": "bold cyan", "C": "white"}
        color = grade_colors.get(grade, "white")

        with Vertical(id="chart_reward_dialog"):
            yield Label("🏆 ¡MISIÓN DE TRACKING COMPLETADA!", classes="reward_title")
            yield Label(f"[{color}]Rango Obtenido: {grade}[/] ({r.get('rendimiento', 0)}% del área)", classes="reward_grade")
            yield Label(f"+{r.get('prestige_reward', 0)} Prestigio", classes="reward_text")
            yield Label(f"+{r.get('coin_amount', 0)} {r.get('coin_type', '')}", classes="reward_text")
            yield Button("Reclamar y Continuar", variant="success", id="btn_claim_reward")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_claim_reward":
            self.dismiss(None)


class WriteJournalModal(ModalScreen[str]):
    CSS = """
    #write_journal_dialog { width: 70; height: 25; padding: 1 2; border: solid $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    #journal_textarea { height: 1fr; margin-bottom: 1; border: round $success;}
    .btn_row { height: 3; align: center middle; }
    .btn_row Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="write_journal_dialog"):
            yield Label("✒️ Nuevo Pensamiento", classes="modal_title")
            yield TextArea(id="journal_textarea")
            with Horizontal(classes="btn_row"):
                yield Button("Sellar Página", variant="success", id="btn_save_journal")
                yield Button("Descartar", variant="error", id="btn_cancel_journal")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_journal":
            self.dismiss(None)
        elif event.button.id == "btn_save_journal":
            text = self.query_one("#journal_textarea", TextArea).text
            if text.strip():
                self.dismiss(text)
            else:
                self.app.notify("La página está en blanco.", severity="error")

# --- MODALES KANBAN Y CALENDARIO ---

# --- UTILIDADES DE FECHA ---

MONTH_NAMES = [
    ("Enero", 1), ("Febrero", 2), ("Marzo", 3), ("Abril", 4),
    ("Mayo", 5), ("Junio", 6), ("Julio", 7), ("Agosto", 8),
    ("Septiembre", 9), ("Octubre", 10), ("Noviembre", 11), ("Diciembre", 12),
]


def _build_year_options():
    """Retorna opciones de año: año actual y el siguiente."""
    y = _dt.date.today().year
    return [(str(y), y), (str(y + 1), y + 1)]


def _build_day_options(month: int = None, year: int = None):
    """Retorna opciones de día (1-28/29/30/31) según el mes y año."""
    if month and year:
        max_day = _cal.monthrange(year, month)[1]
    else:
        max_day = 31
    return [(str(d), d) for d in range(1, max_day + 1)]


def _assemble_date(year_sel, month_sel, day_sel) -> str:
    """Ensambla una fecha ISO desde los tres Select widgets."""
    try:
        y = int(year_sel)
        m = int(month_sel)
        d = int(day_sel)
        return _dt.date(y, m, d).isoformat()
    except (ValueError, TypeError):
        return ""


class NewKanbanTaskModal(ModalScreen[dict]):
    CSS = """
    #new_task_dialog { width: 55; height: auto; padding: 1 2; border: solid $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    .date_row { height: 4; }
    .date_row Select { width: 1fr; margin: 0 1; }
    .date_label { margin-top: 1; text-style: bold; color: $accent; }
    """
    def compose(self) -> ComposeResult:
        today = _dt.date.today()
        with Vertical(id="new_task_dialog"):
            yield Label("Nueva Tarea", classes="modal_title")
            yield Input(placeholder="Título de la tarea", id="task_title")
            yield Label("Prioridad:")
            yield Select((("📜 Rango D (Baja)", "LOW"), ("⚔️ Rango C (Media)", "MED"), ("🛡️ Rango B (Alta)", "HGH"), ("👑 Rango S (Crítica)", "CRT")), id="task_priority", value="MED")
            yield Input(placeholder="Descripción (Opcional)", id="task_desc")
            yield Label("Fecha Límite (Opcional):", classes="date_label")
            with Horizontal(classes="date_row"):
                yield Select(_build_year_options(), id="task_due_year", value=today.year, prompt="Año")
                yield Select(MONTH_NAMES, id="task_due_month", value=today.month, prompt="Mes")
                yield Select(_build_day_options(today.month, today.year), id="task_due_day", value=today.day, prompt="Día")
            with Horizontal(classes="btn_row"):
                yield Button("Crear", variant="success", id="btn_save_task")
                yield Button("Sin Fecha", variant="warning", id="btn_save_task_no_date")
                yield Button("Cancelar", variant="error", id="btn_cancel_task")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Actualiza los días disponibles al cambiar mes o año."""
        if event.select.id in ("task_due_month", "task_due_year"):
            try:
                year = int(self.query_one("#task_due_year", Select).value)
                month = int(self.query_one("#task_due_month", Select).value)
                day_select = self.query_one("#task_due_day", Select)
                current_day = day_select.value
                new_options = _build_day_options(month, year)
                day_select.set_options(new_options)
                max_day = new_options[-1][1]
                if isinstance(current_day, int) and current_day <= max_day:
                    day_select.value = current_day
                else:
                    day_select.value = max_day
            except (ValueError, TypeError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_task":
            self.dismiss(None)
        elif event.button.id in ("btn_save_task", "btn_save_task_no_date"):
            title = self.query_one("#task_title", Input).value
            if not title:
                self.app.notify("La tarea necesita un título.", severity="error")
                return
            due_date = ""
            if event.button.id == "btn_save_task":
                due_date = _assemble_date(
                    self.query_one("#task_due_year", Select).value,
                    self.query_one("#task_due_month", Select).value,
                    self.query_one("#task_due_day", Select).value,
                )
            self.dismiss({
                "title": title,
                "priority": self.query_one("#task_priority", Select).value,
                "description": self.query_one("#task_desc", Input).value,
                "due_date": due_date
            })


class NewKanbanColumnModal(ModalScreen[dict]):
    CSS = """
    #new_col_dialog { width: 40; height: auto; padding: 1 2; border: solid $success; background: $surface; }
    .modal_title { text-style: bold; color: $success; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="new_col_dialog"):
            yield Label("Nueva Columna Kanban", classes="modal_title")
            yield Input(placeholder="Título de columna", id="col_title")
            yield Label("Color:")
            yield Select((("Blanco", "white"), ("Cyan", "cyan"), ("Amarillo", "yellow"), ("Verde", "green"), ("Rojo", "red"), ("Magenta", "magenta")), id="col_color", value="white")
            with Horizontal(classes="btn_row"):
                yield Button("Crear", variant="success", id="btn_save_col")
                yield Button("Cancelar", variant="error", id="btn_cancel_col")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_col":
            self.dismiss(None)
        elif event.button.id == "btn_save_col":
            title = self.query_one("#col_title", Input).value
            if not title:
                self.app.notify("La columna necesita un título.", severity="error")
                return
            self.dismiss({
                "title": title,
                "color": self.query_one("#col_color", Select).value
            })


class NewCalendarEventModal(ModalScreen[dict]):
    CSS = """
    #new_event_dialog { width: 55; height: auto; padding: 1 2; border: solid $primary; background: $surface; }
    .modal_title { text-style: bold; color: $primary; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    .date_row { height: 4; }
    .date_row Select { width: 1fr; margin: 0 1; }
    .date_label { margin-top: 1; text-style: bold; color: $accent; }
    """
    def compose(self) -> ComposeResult:
        today = _dt.date.today()
        with Vertical(id="new_event_dialog"):
            yield Label("Anotar en el Calendario", classes="modal_title")
            yield Label("Fecha del Evento:", classes="date_label")
            with Horizontal(classes="date_row"):
                yield Select(_build_year_options(), id="event_year", value=today.year, prompt="Año")
                yield Select(MONTH_NAMES, id="event_month", value=today.month, prompt="Mes")
                yield Select(_build_day_options(today.month, today.year), id="event_day", value=today.day, prompt="Día")
            yield Input(placeholder="Evento o Nota", id="event_title")
            yield Input(placeholder="Detalles (Opcional)", id="event_desc")
            with Horizontal():
                yield Label("¿Importante? ")
                yield Select((("No", "False"), ("Sí", "True")), id="event_important", value="False")
            with Horizontal(classes="btn_row"):
                yield Button("Anotar", variant="success", id="btn_save_event")
                yield Button("Cancelar", variant="error", id="btn_cancel_event")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Actualiza los días disponibles al cambiar mes o año."""
        if event.select.id in ("event_month", "event_year"):
            try:
                year = int(self.query_one("#event_year", Select).value)
                month = int(self.query_one("#event_month", Select).value)
                day_select = self.query_one("#event_day", Select)
                current_day = day_select.value
                new_options = _build_day_options(month, year)
                day_select.set_options(new_options)
                max_day = new_options[-1][1]
                if isinstance(current_day, int) and current_day <= max_day:
                    day_select.value = current_day
                else:
                    day_select.value = max_day
            except (ValueError, TypeError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_event":
            self.dismiss(None)
        elif event.button.id == "btn_save_event":
            date_str = _assemble_date(
                self.query_one("#event_year", Select).value,
                self.query_one("#event_month", Select).value,
                self.query_one("#event_day", Select).value,
            )
            title = self.query_one("#event_title", Input).value
            if not date_str or not title:
                self.app.notify("Fecha y Título son obligatorios.", severity="error")
                return
            self.dismiss({
                "date": date_str,
                "title": title,
                "description": self.query_one("#event_desc", Input).value,
                "is_important": self.query_one("#event_important", Select).value == "True"
            })

class EditKanbanTaskModal(ModalScreen[dict]):
    CSS = """
    #edit_task_dialog { width: 55; height: auto; padding: 1 2; border: solid $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    .date_row { height: 4; }
    .date_row Select { width: 1fr; margin: 0 1; }
    .date_label { margin-top: 1; text-style: bold; color: $accent; }
    """
    def __init__(self, task_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_data = task_data

    def compose(self) -> ComposeResult:
        t_due = self.task_data.get('due_date')
        if t_due:
            from datetime import date as dt_date
            try:
                today = dt_date.fromisoformat(t_due)
            except:
                today = _dt.date.today()
        else:
            today = _dt.date.today()
            
        with Vertical(id="edit_task_dialog"):
            yield Label("Editar Tarea", classes="modal_title")
            yield Input(value=self.task_data.get('title', ''), placeholder="Título de la tarea", id="task_title")
            yield Label("Prioridad:")
            yield Select((("Baja", "LOW"), ("Media", "MED"), ("Alta", "HGH"), ("Crítica", "CRT")), id="task_priority", value=self.task_data.get('priority_code', 'MED'))
            yield Input(value=self.task_data.get('description', ''), placeholder="Descripción (Opcional)", id="task_desc")
            yield Label("Fecha Límite (Opcional):", classes="date_label")
            with Horizontal(classes="date_row"):
                yield Select(_build_year_options(), id="task_due_year", value=today.year, prompt="Año")
                yield Select(MONTH_NAMES, id="task_due_month", value=today.month, prompt="Mes")
                yield Select(_build_day_options(today.month, today.year), id="task_due_day", value=today.day, prompt="Día")
            with Horizontal(classes="btn_row"):
                yield Button("Guardar", variant="success", id="btn_save_task")
                yield Button("Sin Fecha", variant="warning", id="btn_save_task_no_date")
                yield Button("Cancelar", variant="error", id="btn_cancel_task")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("task_due_month", "task_due_year"):
            try:
                year = int(self.query_one("#task_due_year", Select).value)
                month = int(self.query_one("#task_due_month", Select).value)
                day_select = self.query_one("#task_due_day", Select)
                current_day = day_select.value
                new_options = _build_day_options(month, year)
                day_select.set_options(new_options)
                max_day = new_options[-1][1]
                if isinstance(current_day, int) and current_day <= max_day:
                    day_select.value = current_day
                else:
                    day_select.value = max_day
            except (ValueError, TypeError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_task":
            self.dismiss(None)
        elif event.button.id == "btn_save_task_no_date":
            title = self.query_one("#task_title", Input).value
            if not title:
                self.app.notify("El título es obligatorio.", severity="error")
                return
            self.dismiss({
                "task_id": self.task_data['id'],
                "title": title,
                "description": self.query_one("#task_desc", Input).value,
                "priority": self.query_one("#task_priority", Select).value,
                "due_date": None
            })
        elif event.button.id == "btn_save_task":
            date_str = _assemble_date(
                self.query_one("#task_due_year", Select).value,
                self.query_one("#task_due_month", Select).value,
                self.query_one("#task_due_day", Select).value,
            )
            title = self.query_one("#task_title", Input).value
            if not title:
                self.app.notify("El título es obligatorio.", severity="error")
                return
            self.dismiss({
                "task_id": self.task_data['id'],
                "title": title,
                "description": self.query_one("#task_desc", Input).value,
                "priority": self.query_one("#task_priority", Select).value,
                "due_date": date_str
            })

class EditCalendarEventModal(ModalScreen[dict]):
    CSS = """
    #edit_event_dialog { width: 55; height: auto; padding: 1 2; border: solid $primary; background: $surface; }
    .modal_title { text-style: bold; color: $primary; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    .date_row { height: 4; }
    .date_row Select { width: 1fr; margin: 0 1; }
    .date_label { margin-top: 1; text-style: bold; color: $accent; }
    """
    def __init__(self, event_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_data = event_data

    def compose(self) -> ComposeResult:
        from datetime import date as dt_date
        try:
            today = dt_date.fromisoformat(self.event_data.get('date', ''))
        except:
            today = _dt.date.today()
            
        with Vertical(id="edit_event_dialog"):
            yield Label("Editar Evento", classes="modal_title")
            yield Label("Fecha del Evento:", classes="date_label")
            with Horizontal(classes="date_row"):
                yield Select(_build_year_options(), id="event_year", value=today.year, prompt="Año")
                yield Select(MONTH_NAMES, id="event_month", value=today.month, prompt="Mes")
                yield Select(_build_day_options(today.month, today.year), id="event_day", value=today.day, prompt="Día")
            yield Input(value=self.event_data.get('title', ''), placeholder="Evento o Nota", id="event_title")
            yield Input(value=self.event_data.get('description', ''), placeholder="Detalles (Opcional)", id="event_desc")
            with Horizontal():
                yield Label("¿Importante? ")
                is_imp = "True" if self.event_data.get('is_important') else "False"
                yield Select((("No", "False"), ("Sí", "True")), id="event_important", value=is_imp)
            with Horizontal(classes="btn_row"):
                yield Button("Guardar", variant="success", id="btn_save_event")
                yield Button("Cancelar", variant="error", id="btn_cancel_event")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("event_month", "event_year"):
            try:
                year = int(self.query_one("#event_year", Select).value)
                month = int(self.query_one("#event_month", Select).value)
                day_select = self.query_one("#event_day", Select)
                current_day = day_select.value
                new_options = _build_day_options(month, year)
                day_select.set_options(new_options)
                max_day = new_options[-1][1]
                if isinstance(current_day, int) and current_day <= max_day:
                    day_select.value = current_day
                else:
                    day_select.value = max_day
            except (ValueError, TypeError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel_event":
            self.dismiss(None)
        elif event.button.id == "btn_save_event":
            date_str = _assemble_date(
                self.query_one("#event_year", Select).value,
                self.query_one("#event_month", Select).value,
                self.query_one("#event_day", Select).value,
            )
            title = self.query_one("#event_title", Input).value
            if not date_str or not title:
                self.app.notify("Fecha y Título son obligatorios.", severity="error")
                return
            self.dismiss({
                "event_id": self.event_data['id'],
                "date": date_str,
                "title": title,
                "description": self.query_one("#event_desc", Input).value,
                "is_important": self.query_one("#event_important", Select).value == "True"
            })

# --- MODALES DE DETALLE ---

class DeleteConfirmationModal(ModalScreen[bool]):
    CSS = """
    #del_confirm_dialog { width: 45; height: auto; padding: 1 2; border: solid $error; background: $surface; }
    .modal_title { text-style: bold; color: $error; text-align: center; margin-bottom: 1; width: 100%; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    .btn_row Button { margin: 0 1; }
    """
    def __init__(self, message: str = "¿Eliminar aventurero permanentemente?", name: str | None = None, id: str | None = None, classes: str | None = None):
        super().__init__(name=name, id=id, classes=classes)
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="del_confirm_dialog"):
            yield Label(self.message, classes="modal_title")
            with Horizontal(classes="btn_row"):
                yield Button("Sí, eliminar", variant="error", id="btn_confirm_del")
                yield Button("Cancelar", variant="primary", id="btn_cancel_del")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm_del":
            self.dismiss(True)
        elif event.button.id == "btn_cancel_del":
            self.dismiss(False)


class HabitDetailsModal(ModalScreen[None]):
    """Panel de detalle de un hábito diario."""

    CSS = """
    #habit_details_dialog { width: 60; height: auto; padding: 1 2; border: double $success; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .detail_section { margin-top: 1; text-style: bold; color: $success; }
    .detail_content { margin-bottom: 1; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    """

    DAY_NAMES = {"0": "Lun", "1": "Mar", "2": "Mié", "3": "Jue", "4": "Vie", "5": "Sáb", "6": "Dom"}

    def __init__(self, habit_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.habit_data = habit_data

    def compose(self) -> ComposeResult:
        h = self.habit_data
        habit_type = "[bold red]Mal Hábito (Evitar)[/]" if h.get("is_bad_habit") else "[bold green]Buen Hábito[/]"
        diff = h.get("difficulty", "?")
        diff_code = h.get("difficulty_code", "C")
        diff_colors = {"S": "bold yellow", "A": "bold magenta", "B": "bold cyan", "C": "white"}
        diff_color = diff_colors.get(diff_code, "white")

        # Parse valid days
        valid_str = h.get("valid_days", "0,1,2,3,4,5,6")
        day_labels = [self.DAY_NAMES.get(d.strip(), "?") for d in valid_str.split(",") if d.strip()]
        days_display = ", ".join(day_labels) if day_labels else "Todos los días"

        streak = h.get("current_streak", 0)
        completed = h.get("completed_today", False)
        status_str = "[bold green]✔ Completado hoy[/]" if completed else "[gray]✘ Pendiente[/]"
        if h.get("is_bad_habit"):
            status_str = "[bold red]⚠ Recaída hoy[/]" if completed else "[bold green]🛡️ Evitado hoy[/]"

        last_completed = h.get("last_completed_date", None) or "Nunca"
        created = h.get("created_at", None) or "Desconocido"

        with Vertical(id="habit_details_dialog"):
            yield Label(f"📋 Detalle de Hábito", classes="modal_title")

            yield Label("Nombre:", classes="detail_section")
            yield Label(f"  {h.get('name', '?')}", classes="detail_content")

            yield Label("Tipo:", classes="detail_section")
            yield Label(f"  {habit_type}", classes="detail_content")

            yield Label("Dificultad:", classes="detail_section")
            yield Label(f"  [{diff_color}]{diff}[/]", classes="detail_content")

            yield Label("Días Válidos:", classes="detail_section")
            yield Label(f"  {days_display}", classes="detail_content")

            yield Label("Estado Hoy:", classes="detail_section")
            yield Label(f"  {status_str}", classes="detail_content")

            yield Label("Racha Actual:", classes="detail_section")
            yield Label(f"  🔥 {streak} día(s) consecutivos", classes="detail_content")

            yield Label("Última Interacción:", classes="detail_section")
            yield Label(f"  {last_completed}", classes="detail_content")

            yield Label("Creado:", classes="detail_section")
            yield Label(f"  {created}", classes="detail_content")

            with Horizontal(classes="btn_row"):
                yield Button("Cerrar", variant="primary", id="btn_close_details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_details":
            self.dismiss(None)


class KanbanTaskDetailsModal(ModalScreen[None]):
    """Panel de detalle de una tarea Kanban."""

    CSS = """
    #task_details_dialog { width: 60; height: auto; padding: 1 2; border: double $accent; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .detail_section { margin-top: 1; text-style: bold; color: $success; }
    .detail_content { margin-bottom: 1; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, task_data: dict, column_name: str = "?", **kwargs):
        super().__init__(**kwargs)
        self.task_data = task_data
        self.column_name = column_name

    def compose(self) -> ComposeResult:
        t = self.task_data
        priority_colors = {"CRT": "bold red", "HGH": "bold yellow", "MED": "bold cyan", "LOW": "white"}
        p_code = t.get("priority_code", "MED")
        p_color = priority_colors.get(p_code, "white")

        due = t.get("due_date", None) or "Sin fecha límite"
        desc = t.get("description", "") or "Sin descripción."

        with Vertical(id="task_details_dialog"):
            yield Label(f"📌 Detalle de Tarea", classes="modal_title")

            yield Label("Título:", classes="detail_section")
            yield Label(f"  {t.get('title', '?')}", classes="detail_content")

            yield Label("Descripción:", classes="detail_section")
            yield Label(f"  {desc}", classes="detail_content")

            yield Label("Rango de Misión:", classes="detail_section")
            yield Label(f"  [{p_color}]{t.get('quest_rank', t.get('priority', '?'))}[/]", classes="detail_content")

            yield Label("Columna Actual:", classes="detail_section")
            yield Label(f"  {self.column_name}", classes="detail_content")

            yield Label("Fecha Límite:", classes="detail_section")
            yield Label(f"  {due}", classes="detail_content")

            yield Label("Prestigio al Completar:", classes="detail_section")
            yield Label(f"  +{t.get('prestige_reward', 0)} Prestigio", classes="detail_content")

            with Horizontal(classes="btn_row"):
                yield Button("Cerrar", variant="primary", id="btn_close_details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_details":
            self.dismiss(None)


class CalendarEventDetailsModal(ModalScreen[None]):
    """Panel de detalle de un evento del calendario."""

    CSS = """
    #event_details_dialog { width: 60; height: auto; padding: 1 2; border: double $primary; background: $surface; }
    .modal_title { text-style: bold; color: $warning; text-align: center; margin-bottom: 1; width: 100%; }
    .detail_section { margin-top: 1; text-style: bold; color: $success; }
    .detail_content { margin-bottom: 1; }
    .btn_row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, event_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.event_data = event_data

    def compose(self) -> ComposeResult:
        e = self.event_data
        importance = "[bold yellow]★ Importante[/]" if e.get("is_important") else "Normal"
        desc = e.get("description", "") or "Sin detalles adicionales."

        with Vertical(id="event_details_dialog"):
            yield Label(f"📅 Detalle de Evento", classes="modal_title")

            yield Label("Título:", classes="detail_section")
            yield Label(f"  {e.get('title', '?')}", classes="detail_content")

            yield Label("Fecha:", classes="detail_section")
            yield Label(f"  {e.get('date', '?')}", classes="detail_content")

            yield Label("Descripción:", classes="detail_section")
            yield Label(f"  {desc}", classes="detail_content")

            yield Label("Importancia:", classes="detail_section")
            yield Label(f"  {importance}", classes="detail_content")

            with Horizontal(classes="btn_row"):
                yield Button("Cerrar", variant="primary", id="btn_close_details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_details":
            self.dismiss(None)


class BestiaryCodexModal(ModalScreen[None]):
    """Modal para mostrar el Bestiario de Monstruos descubiertos."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="bestiary_codex_dialog", classes="modal_dialog"):
            yield Label("📖 CÓDICE DE BESTIARIO", id="lbl_bestiary_title", classes="title_bar")
            
            with Horizontal(id="bestiary_layout"):
                # Lista de monstruos descubiertos
                with Vertical(id="bestiary_list_container"):
                    yield DataTable(id="bestiary_table", cursor_type="row")
                
                # Panel de detalles
                with Vertical(id="bestiary_details_container"):
                    yield Label("Selecciona una criatura para ver sus detalles.", id="lbl_bestiary_instructions")
                    with VerticalScroll(id="bestiary_scroll_details"):
                        yield Label("", id="lbl_monster_name", classes="section_title")
                        yield Label("", id="lbl_monster_stats")
            
            with Horizontal(classes="btn_row"):
                yield Button("Cerrar Códice", variant="error", id="btn_close_bestiary")

    def on_mount(self) -> None:
        table = self.query_one("#bestiary_table", DataTable)
        table.add_columns("Monstruo", "Bajas", "Cat.")
        self.load_bestiary()

    def load_bestiary(self) -> None:
        import requests
        try:
            resp = requests.get("http://localhost:8009/api/bestiary/")
            if resp.status_code == 200:
                self.bestiary_data = resp.json().get("bestiary", [])
                table = self.query_one("#bestiary_table", DataTable)
                table.clear()
                for i, entry in enumerate(self.bestiary_data):
                    table.add_row(entry["name"], str(entry["times_killed"]), entry["category"], key=str(i))
        except Exception:
            self.notify("Error cargando el bestiario.", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = int(event.row_key.value)
        entry = self.bestiary_data[idx]
        
        self.query_one("#lbl_bestiary_instructions", Label).display = False
        self.query_one("#lbl_monster_name", Label).update(f"[bold red]{entry['name']}[/bold red] ({entry['category']})")
        
        stats = entry["stats"]
        details = (
            f"[bold cyan]Primer Avistamiento:[/bold cyan] {entry['first_seen']}\n"
            f"[bold cyan]Último Combate:[/bold cyan] {entry['last_seen']}\n\n"
            f"[bold yellow]Estadísticas Estimadas:[/bold yellow]\n"
            f"❤️ HP: {stats['hp']}\n"
            f"⚔️ Daño: {stats['damage']}\n"
            f"💪 STR: {stats['str']} | 🏃 DEX: {stats['dex']} | 🧠 INT: {stats['int']}"
        )
        self.query_one("#lbl_monster_stats", Label).update(details)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close_bestiary":
            self.dismiss()


# --- PESTAÑAS ---


class TimerTab(TabPane):
    can_focus = True
    BINDINGS = [("c", "setup_timer", "Configurar"), ("p", "pause_timer",
                                                     "Pausar/Seguir"), ("s", "stop_timer", "Detener")]


class GuildTab(TabPane):
    can_focus = True
    BINDINGS = [("d", "show_details", "Detalles"), ("x", "delete_adventurer", "Eliminar"), 
                ("n", "new_adventurer", "Nuevo Avatar"), ("c", "open_guild_chest", "Abrir Cofre"),
                ("b", "open_bestiary", "Bestiario")]


class TavernTab(TabPane):
    can_focus = True
    BINDINGS = [("r", "recruit", "Reclutar"),
                ("f", "refresh_tavern", "Invitar Rondas")]


class MissionsTab(TabPane):
    can_focus = True
    BINDINGS = [
        ("m", "complete_habit", "Marcar"),
        ("+", "add_habit", "+ Hábito"),
        ("-", "delete_habit", "- Hábito"),
        ("u", "undo_habit", "Deshacer"),
        ("<", "prev_chart", "◀ Gráfico"),
        (">", "next_chart", "Gráfico ▶"),
        ("a", "add_chart_data", "Dato"),
        ("n", "new_chart", "Nuevo Gráf."),
        ("D", "delete_chart", "Borrar Gráf."),
        ("R", "claim_chart", "Reclamar"),
        ("i", "inspect_chart", "Inspeccionar Gráf."),
        ("I", "inspect_habit", "Detalle Hábito"),
    ]

class KanbanTab(TabPane):
    can_focus = True
    BINDINGS = [
        ("t", "new_task", "Nueva Tarea"),
        ("left", "move_left", "Mover a Izq"),
        ("right", "move_right", "Mover a Der"),
        ("c", "new_col", "Nueva Columna"),
        ("e", "new_calendar_event", "Nuevo Evento"),
        ("E", "handle_e", "Editar Tarea/Evento"),
        ("x", "handle_x", "Borrar Tarea/Evento"),
        ("i", "inspect_kanban", "Detalle"),
    ]

class JournalTab(TabPane):
    can_focus = True
    BINDINGS = [
        ("w", "write_journal", "Escribir Diario"),
    ]

class ChroniclesTab(TabPane):
    can_focus = True
    BINDINGS = []

# --- PANTALLA PRINCIPAL ---


class PosadaMainScreen(Screen):
    """Pantalla principal para el sistema de Deep Work y RPG."""

    time_seconds = reactive(25 * 60)
    timer_active = reactive(False)
    is_countdown = reactive(True)

    BINDINGS = [
        # Globales (funcionales pero ocultos del footer)
        Binding("escape", "app.pop_screen", "Salir Posada", show=False),
        Binding("q", "app.quit", "Salir Bunker", show=False),
        Binding("1", "switch_tab('tab_timer')", "Enfoque", show=False),
        Binding("2", "switch_tab('tab_guild')", "Gremio", show=False),
        Binding("3", "switch_tab('tab_tavern')", "Taberna", show=False),
        Binding("4", "switch_tab('tab_missions')", "Rutinas", show=False),
        Binding("5", "switch_tab('tab_kanban')", "Kanban", show=False),
        Binding("6", "switch_tab('tab_journal')", "Diario", show=False),
        Binding("7", "switch_tab('tab_chronicles')", "Crónicas", show=False),

        # Controles Ocultos Directos
        Binding("p", "pause_timer", "Pausar", show=False),
        Binding("s", "stop_timer", "Detener", show=False),
        Binding("d", "show_details", "Detalles", show=False),
        Binding("x", "handle_x", "Eliminar", show=False),
        Binding("backspace", "handle_x", "Borrar", show=False),
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
        Binding("R", "claim_chart", "Reclamar Gráfico", show=False),
        Binding("b", "open_bestiary", "Abrir Bestiario", show=False),
        Binding("i", "handle_i", "Inspeccionar", show=False),
        Binding("I", "inspect_habit", "Detalle Hábito", show=False),
        Binding("t", "new_kanban_task", "Nueva Tarea", show=False),
        Binding("delete", "handle_x", "Borrar Tarea/Evento", show=False),
        Binding("e", "new_calendar_event", "Nuevo Evento", show=False),
        Binding("E", "handle_e", "Editar Tarea/Evento", show=False),
        Binding("w", "write_journal", "Escribir Diario", show=False),
        
        # Conflict Resolution Bindings
        Binding("n", "handle_n", "Nuevo", show=False),
        Binding("c", "handle_c", "Config/Columna", show=False),
        Binding("shift+left", "handle_left", "Izquierda (Shift)", show=False),
        Binding("shift+right", "handle_right", "Derecha (Shift)", show=False),
        Binding("left", "handle_left", "Izquierda", show=False),
        Binding("right", "handle_right", "Derecha", show=False),
    ]

    CSS = """
    #posada_root { padding: 1 2; }
    
    #focus_layout { height: 1fr; margin-top: 1; } 
    #focus_top_row { height: 15; margin-bottom: 1; }
    
    .party_panel { border: round $success; padding: 1; width: 45%; height: 100%; margin-right: 2; }
    .timer_panel { border: heavy $accent; align: center middle; width: 50%; height: 100%; padding: 1; }
    .mud_log_panel { border: solid #888888; padding: 0 1; background: #0c0c0c; height: 1fr; }
    
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
    RichLog {
        text-opacity: 0.9;
    }
    .log-damage {
        color: $error;
        text-style: bold;
    }
    
    #journal_book { height: 1fr; border: double #8b5a2b; background: #1a110b; margin-bottom: 1; }
    .journal_page { width: 50%; height: 100%; padding: 1 3; }
    .page_left { border-right: dashed #5c3a21; }
    .page_date { text-style: italic; color: #d4af37; margin-bottom: 1; border-bottom: solid #5c3a21; width: 100%; text-align: center; }
    .page_content { height: 1fr; color: #e6d8ad; }
    #journal_controls { height: 3; align: center middle; }
    #journal_controls Button { margin: 0 2; }
    
    .kanban_table { width: 1fr; height: 1fr; margin: 0 1; border: round $accent; }
    #kanban_columns_container { height: 60%; margin-bottom: 1; }
    .calendar_table { height: 1fr; margin: 0 1; }
    
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="posada_root"):
            with TabbedContent(initial="tab_timer"):

                with TimerTab("Sala de Enfoque", id="tab_timer"):
                    with Vertical(id="focus_layout"):
                        
                        # Fila Superior: Reloj a la izquierda, Grupo a la derecha
                        with Horizontal(id="focus_top_row"):
                            with Vertical(classes="timer_panel"):
                                yield Label(get_ascii_time("25:00"), id="timer_display")
                                with Horizontal(classes="timer_buttons"):
                                    yield Button("Configurar y Partir", id="btn_setup_timer", variant="success")
                                    yield Button("Pausar", id="btn_pause_timer", variant="warning")
                                    yield Button("Continuar", id="btn_resume_timer", variant="success")
                                    yield Button("Detener / Huir", id="btn_stop_timer", variant="error")

                            with Vertical(classes="party_panel"):
                                yield Label("Grupo Activo (Max 5)")
                                yield DataTable(id="active_party_table")

                        # Fila Inferior: Registro de Eventos (ocupando el resto de la pantalla)
                        with Vertical(classes="mud_log_panel"):
                            yield Label("📜 Registro de Eventos")
                            yield RichLog(id="event_log", markup=True, highlight=True)

                with GuildTab("El Gremio", id="tab_guild"):
                    with Vertical(classes="guild_stats"):
                        yield Label("Cargando...", id="lbl_guild_level")
                        yield Label("Cargando bóveda...", id="lbl_guild_vault")
                        yield Button("Consolidar Riqueza", id="btn_consolidate", classes="btn_consolidate", variant="warning")
                        yield Button("Mejoras de Infraestructura", id="btn_open_upgrades", classes="btn_consolidate", variant="success")
                        yield Button("Cofre del Gremio", id="btn_open_chest", classes="btn_consolidate", variant="primary")
                        yield Button("¡Reiniciar Gremio (Peligro)!", id="btn_reset_guild", classes="btn_consolidate", variant="error")
                    yield Label("Todos los Aventureros Reclutados:")
                    yield DataTable(id="all_adventurers_table")

                with TavernTab("La Taberna", id="tab_tavern"):
                    with Vertical():
                        yield Label("Aventureros buscando un Gremio (Nivel 1):", classes="section_title")
                        yield DataTable(id="tavern_table")
                        with Horizontal(classes="timer_buttons"):
                            yield Button("Reclutar Seleccionado (r)", id="btn_recruit", variant="success")
                            yield Button("Invitar Rondas (f)", id="btn_refresh_tavern", variant="primary")
                    
                    with Vertical(id="exchange_section", classes="hidden"):
                        yield Label("🏛️ Casa de Cambio de Vintas", classes="section_title")
                        with Horizontal(classes="timer_buttons"):
                            yield Button("Cambiar 5 Plata a 16 Sueldos", id="btn_exchange_to_sueldo", variant="warning")
                            yield Button("Cambiar 16 Sueldos a 5 Plata", id="btn_exchange_to_silver", variant="primary")

                with MissionsTab("Rutinas del Gremio", id="tab_missions"):
                    with Horizontal():
                        # Los Hábitos
                        with Vertical(id="habits_col", classes="half_width"):
                            yield Label("Buenos Hábitos (+ Añadir | m Marcar)")
                            yield DataTable(id="good_habits_table")
                            yield Label("Malos Hábitos (+ Añadir | m Marcar)")
                            yield DataTable(id="bad_habits_table")

                        # Gráfico Analítico
                        with Vertical(id="stats_col", classes="half_width"):
                            yield Label("Cargando gráficos...", id="chart_title_label", classes="section_title")
                            yield PlotextPlot(id="productivity_plot")

                with KanbanTab("Encargos del Gremio", id="tab_kanban"):
                    with Vertical():
                        yield Label("Kanban (Cargando...)", id="lbl_kanban_title", classes="section_title")
                        with Horizontal(id="kanban_columns_container"):
                            yield DataTable(id="kanban_col_0", classes="kanban_table")
                            yield DataTable(id="kanban_col_1", classes="kanban_table")
                            yield DataTable(id="kanban_col_2", classes="kanban_table")
                            yield DataTable(id="kanban_col_3", classes="kanban_table")
                        yield Label("Calendario de Eventos (e Nuevo | E Editar | x/Supr Borrar)", id="lbl_calendar_title", classes="section_title")
                        yield DataTable(id="calendar_table", classes="calendar_table")

                with JournalTab("Diario de Viaje", id="tab_journal"):
                    with Horizontal(id="journal_book"):
                        with Vertical(classes="journal_page page_left"):
                            yield Label("", id="page_left_date", classes="page_date")
                            yield Label("", id="page_left_content", classes="page_content")
                        with Vertical(classes="journal_page"):
                            yield Label("", id="page_right_date", classes="page_date")
                            yield Label("", id="page_right_content", classes="page_content")
                    with Horizontal(id="journal_controls"):
                        yield Button("◀ Anterior", id="btn_journal_prev", variant="primary")
                        yield Button("✒️ Escribir (w)", id="btn_journal_write", variant="success")
                        yield Button("Siguiente ▶", id="btn_journal_next", variant="primary")

                with ChroniclesTab("📜 Crónicas", id="tab_chronicles"):
                    with Horizontal(id="chronicles_layout"):
                        with Vertical(id="chronicles_list_panel"):
                            yield Label("📜 Sesiones de Deep Work Registradas", classes="section_title")
                            yield DataTable(id="chronicles_table", cursor_type="row")
                        with Vertical(id="chronicles_reader_panel"):
                            yield Label("Selecciona una sesión para revivir su crónica.", id="lbl_chronicles_hint")
                            yield RichLog(id="chronicles_log", highlight=True, markup=True)

        yield Label("", id="tab_controls")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#active_party_table", DataTable).add_columns(
            "Nombre", "Clase", "Raza", "Nivel", "Estado")
        table_adv = self.query_one("#all_adventurers_table", DataTable)
        table_adv.add_columns("Nombre", "Clase", "Nivel",
                              "XP", "Riqueza", "Equipamiento", "Estado")
        for table_id in ["#good_habits_table", "#bad_habits_table"]:
            self.query_one(table_id, DataTable).add_columns(
                "Misión", "Recompensa Base", "Estado"
            )
            self.query_one(table_id, DataTable).cursor_type = "row"

        self.query_one("#event_log", RichLog).write(
            "La taberna está silenciosa. Esperando órdenes del Maestro...")
        self.clock_ticker = self.set_interval(1, self.tick_timer, pause=True)

        self.query_one("#tavern_table", DataTable).add_columns(
            "Nombre", "Clase", "Raza", "Nivel", "Costo", "Equipamiento", "Stats Base")
        self.refresh_tavern_api()  # Llena la taberna al entrar

        # Sincroniza la interfaz con la base de datos
        self.sync_guild_status()
        self.fetch_missions_data()
        self.fetch_journal()
        self.fetch_kanban_data()
        self.fetch_calendar_data()
        self.set_timer_ui_state("idle")
        self.query_one("#tab_timer").focus()
        self.query_one("#tab_controls", Label).update(
            "Sala de Enfoque -> [c] Configurar Expedición  |  [p] Pausar / Seguir  |  [s] Detener / Huir")

        self.title = "BUNKER"
        self.sub_title = "Módulo de la Posada"

    # --- LLAMADAS A LA API ---
    @work(thread=True)
    def sync_guild_status(self) -> None:
        try:
            resp = httpx.get(f"{API_POSADA_BASE}status/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.render_guild_status, resp.json())
        except Exception:
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

    @work(thread=True)
    def request_exchange(self, direction: str) -> None:
        try:
            resp = httpx.post(f"{API_POSADA_BASE}guild/exchange/", json={"direction": direction}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="success")
                self.sync_guild_status()
            else:
                msg = resp.json().get("error", "Error en cambio de divisas") if resp.status_code == 400 else "Error del servidor"
                self.app.call_from_thread(self.app.notify, msg, severity="error")
        except Exception:
            self.app.call_from_thread(self.app.notify, "La Casa de Cambio está cerrada.", severity="error")

    def handle_reset_guild(self, confirmed: bool) -> None:
        if confirmed:
            self._do_reset_guild()

    @work(thread=True)
    def _do_reset_guild(self) -> None:
        try:
            resp = httpx.post(f"{API_POSADA_BASE}guild/reset/", timeout=10.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="warning")
                self.sync_guild_status()
                # Optional: refresh other tabs
                if hasattr(self, 'fetch_missions_data'):
                    self.fetch_missions_data()
                if hasattr(self, 'fetch_kanban_data'):
                    self.fetch_kanban_data()
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al reiniciar el gremio.", severity="error")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "El servidor no responde.", severity="error")

    def render_guild_status(self, data: dict) -> None:
        guild = data.get("guild", {})
        adventurers = data.get("adventurers", [])
        self.adventurers_cache = adventurers

        # --- MOSTRAR BARRA DE PRESTIGIO ---
        lvl = guild.get('prestige_level', 1)
        prest = guild.get('prestige', 0)
        meta = guild.get('prestige_meta', 100)

        # Color rojo si está en deuda, verde si está bien
        color_p = "bold red" if prest < 0 else "bold green"

        max_adv = guild.get('max_adventurers', 1)
        curr_adv = guild.get('current_adventurers', len(adventurers))
        self.query_one("#lbl_guild_level", Label).update(
            f"Nivel de Gremio: {lvl} | Prestigio: [{color_p}]{prest} / {meta}[/] | Aventureros: {curr_adv}/{max_adv}"
        )

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
                adv.get("name", "Unknown"),
                adv.get("adv_class", "BBN"),
                str(adv.get("level", 1)),
                f"{adv.get('current_hp', 0)}/{adv.get('max_hp', 0)}",
                status,
                resumen_equipo,
                key=str(adv.get("id"))
            )

        # Configurar visibilidad de Casa de Cambio
        unlocked = guild.get('unlocked_upgrades', [])
        exchange_sec = self.query_one("#exchange_section", Vertical)
        if "casa_de_cambio" in unlocked:
            exchange_sec.remove_class("hidden")
        else:
            exchange_sec.add_class("hidden")

        # SI EL GREMIO ESTÁ VACÍO, FUERZA LA CREACIÓN DEL AVATAR
        if not adventurers:
            self.app.push_screen(CharacterCreationModal(),
                                 self.submit_new_character)

    def submit_new_character(self, result: dict | None) -> None:
        """Callback de push_screen: recibe el resultado del modal y lanza el worker HTTP."""
        if result is None:
            return
        self._do_create_character(result)

    @work(thread=True)
    def _do_create_character(self, result: dict) -> None:
        """Worker HTTP que envía el nuevo personaje a Django y recarga la interfaz."""
        try:
            resp = httpx.post(
                f"{API_POSADA_BASE}adventurer/create/", json=result, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, "¡Avatar creado! Bienvenido a La Posada.", severity="success")
                self.app.call_from_thread(self.sync_guild_status)
            else:
                # Intenta parsear el JSON de error; si el servidor devolvió HTML (500), usa un mensaje genérico
                try:
                    error_msg = resp.json().get("message", "Error al crear el personaje.")
                except Exception:
                    error_msg = f"Error del servidor (HTTP {resp.status_code})."
                self.app.call_from_thread(
                    self.app.notify, error_msg, severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Fallo de conexión al crear personaje: {e}", severity="error")

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
                m, s = divmod(elapsed, 60)
                state = event.get('state', 'EXPLORING')
                event_type = event.get('type', 'flavor')
                
                if event_type in ['loot', 'item_loot'] or state == 'EXPLORING':
                    prefix = "[bold cyan] 🗺️ EXPLORANDO [/bold cyan] "
                elif state == 'COMBAT':
                    prefix = "[bold red] ⚔️ COMBATE [/bold red] "
                elif state == 'CAMPFIRE':
                    prefix = "[bold yellow] 🏕️ CAMPAMENTO [/bold yellow] "
                else:
                    prefix = "[bold cyan] 🗺️ EXPLORANDO [/bold cyan] "
                    
                message = f"[white]{event['message']}[/white]"
                
                formatted_time = f"[dim][{m:02d}:{s:02d}][/dim]"
                
                self.query_one("#event_log", RichLog).write(
                    f"{formatted_time} {prefix}{message}"
                )

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
            self.query_one("#event_log", RichLog).write(
                "La expedición se detiene. Los monstruos acechan...")

    def action_resume_timer(self) -> None:
        if self.query_one(TabbedContent).active != "tab_timer":
            return
        if not self.timer_active and self.time_seconds > 0:
            self.clock_ticker.resume()
            self.timer_active = True
            self.set_timer_ui_state("running")
            self.query_one("#event_log", RichLog).write(
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
        elif event.button.id == "btn_reset_guild":
            self.app.push_screen(ConfirmResetModal(), self.handle_reset_guild)
        elif event.button.id == "btn_recruit":
            self.action_recruit()
        elif event.button.id == "btn_refresh_tavern":
            self.action_refresh_tavern()
        elif event.button.id == "btn_journal_prev":
            self.action_prev_journal_page()
        elif event.button.id == "btn_journal_next":
            self.action_next_journal_page()
        elif event.button.id == "btn_journal_write":
            self.action_write_journal()
        elif event.button.id == "btn_open_upgrades":
            # Abre el modal y al cerrarlo sincroniza la bóveda del Gremio
            self.app.push_screen(GuildUpgradesModal(),
                                 lambda _: self.sync_guild_status())
        elif event.button.id == "btn_open_chest":
            self.action_open_guild_chest()
        elif event.button.id == "btn_exchange_to_sueldo":
            self.request_exchange("to_sueldo")
        elif event.button.id == "btn_exchange_to_silver":
            self.request_exchange("to_silver")

    def action_delete_adventurer(self) -> None:
        if self.query_one(TabbedContent).active != "tab_guild":
            return
        table = self.query_one("#guild_table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
            self.app.push_screen(DeleteConfirmationModal(
                "¿Despedir Aventurero?"), lambda confirm: self.execute_delete_adv(confirm, row_key.value))
        except Exception:
            self.app.notify(
                "Selecciona un aventurero de la tabla primero.", severity="warning")

    def action_open_guild_chest(self) -> None:
        if self.query_one(TabbedContent).active != "tab_guild":
            return
        self.app.push_screen(InventoryModal("guild", 1, "Cofre del Gremio (Items y Recursos)"), lambda _: self.sync_guild_status())

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
            self.app.push_screen(AdventurerDetailsModal(adv_data), lambda _: self.sync_guild_status())
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
                "El Gremio -> [d] Detalles y Equipo | [c] Abrir Cofre | [x] Despedir | [n] Avatar Inicial")
        elif pane_id == "tab_tavern":
            lbl.update(
                "La Taberna -> [r] Reclutar Seleccionado  |  [f] Pagar Rondas de Cerveza (Refrescar)")
        elif pane_id == "tab_missions":
            lbl.update(
                "Misiones -> [m] Marcar | [u] Deshacer | [-] Borrar | [I] Detalle | [<][>] Carrusel | [a] Dato | [i] Inspeccionar | [R] Reclamar")
        elif pane_id == "tab_journal":
            lbl.update(
                "Diario de Viaje -> [w] Escribir Pensamiento  |  [◀] Página Anterior  |  [▶] Página Siguiente")
        elif pane_id == "tab_kanban":
            lbl.update(
                "Kanban -> [t] Tarea | [c] Columna | [e] Nuevo Evento | [E] Editar | [x/Supr] Borrar | [i] Detalle")
        elif pane_id == "tab_chronicles":
            lbl.update(
                "Crónicas -> Selecciona una sesión pasada para releer su narrativa.")
            self.action_load_chronicles()

    def action_switch_tab(self, tab_id: str) -> None:
        """Permite navegar súper rápido entre pestañas presionando 1, 2, 3 o 4."""
        self.query_one(TabbedContent).active = tab_id

    # --- FLUJO DE INICIO MUD (PRE-CÁLCULO) ---
    def prepare_session(self, result: dict | None) -> None:
        """Paso 1: Recibe configuración y pide el guion al backend."""
        if result is None:
            return

        log = self.query_one("#event_log", RichLog)
        log.clear()
        log.write("Consultando al Oráculo del Gremio...")

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

        log = self.query_one("#event_log", RichLog)
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
            log.write(
                f"\n[Misión: {cat}] El reloj inicia. ¡Que la suerte os acompañe!")
        else:
            self.is_countdown = False
            self.time_seconds = 0
            log.write(
                f"\n[Misión: {cat}] Cronómetro iniciado hacia lo desconocido.")

        self.clock_ticker.resume()

    # --- FLUJO DE CIERRE Y BOTÍN ---
    def handle_session_end(self, success: bool):
        log = self.query_one("#event_log", RichLog)

        if self.is_countdown:
            total_sec = getattr(self, 'session_duration_mins', 25) * 60
            elapsed = total_sec - self.time_seconds
        else:
            elapsed = self.time_seconds

        if success:
            log.write("¡Mazmorra completada con éxito!")
        else:
            log.write(
                "Has tocado el cuerno de retirada. La party huye.")

        log.write("Consolidando resultados con la Bóveda del Gremio...")

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
        log = self.query_one("#event_log", RichLog)

        # Imprime los reportes de post-sesión (Diezmo, Tienda, XP)
        for event_msg in data.get("log", []):
            log.write(f"📜 {event_msg}")

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

            def check_deletion(confirm: bool | None):
                if confirm:
                    self.request_deletion(adv_id)

            self.app.push_screen(DeleteConfirmationModal(), check_deletion)
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
            cost_str = f"{r.get('cost_in_sueldos', 0)} Sueldos"
            eq_str = r.get("equipment_desc", "Ninguno")
            lvl_str = str(r.get("level", 1))
            table.add_row(r["name"], r["adv_class_display"],
                          r["race_display"], lvl_str, cost_str, eq_str, stats_str, key=str(idx))

    def action_refresh_tavern(self) -> None:
        if self.query_one(TabbedContent).active == "tab_tavern":
            self.query_one("#event_log", RichLog).write(
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

        # Actualizar Título del Carrusel con progreso
        total = len(self.charts_cache)
        curr = self.current_chart_index + 1
        covered = chart_data.get('covered_count', 0)
        expected = chart_data.get('total_expected', 0)
        progress_str = f" [{covered}/{expected}]" if expected > 0 else ""
        complete_flag = " ✅" if chart_data.get('is_complete') else ""
        lbl = self.query_one("#chart_title_label", Label)
        lbl.update(f"◀ [{curr}/{total}] {chart_data['title']}{progress_str}{complete_flag} ▶")

        plot_widget = self.query_one("#productivity_plot", PlotextPlot)
        plt = plot_widget.plt
        plt.clear_figure()

        x = chart_data.get("x_data", [])
        y = chart_data.get("y_data", [])

        plt.theme("dark")

        # --- APLICAR LÍMITES ABSOLUTOS ---
        x_min = chart_data.get('x_min', 1.0)
        goal_x = chart_data.get('goal_x', 30)
        plt.xlim(x_min, goal_x)
        plt.ylim(chart_data.get('y_min', 0.0), chart_data.get('y_max', 10.0))

        # --- XTICKS ENTEROS (elimina decimales como 23.5) ---
        x_start = int(x_min)
        x_end = int(goal_x)
        x_range = x_end - x_start + 1
        if x_range <= 15:
            plt.xticks(list(range(x_start, x_end + 1)))
        else:
            # Para rangos grandes, mostrar cada N ticks
            step = max(1, x_range // 15)
            plt.xticks(list(range(x_start, x_end + 1, step)))

        if x and y:
            plt.plot(x, y, marker="braille", color="cyan")
        else:
            plt.title("Presiona 'a' para añadir el primer dato.")

        title_text = f"Meta: {chart_data['x_label']} {goal_x} | {chart_data['polarity']}"
        if chart_data.get('is_complete'):
            title_text += " | ¡LISTO! (R)"
        plt.title(title_text)
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
                data = resp.json()
                self.app.call_from_thread(
                    self.app.notify, data.get("message"), severity="success")

                # Si el gráfico quedó completo, auto-claim
                if data.get("chart_complete"):
                    self.app.call_from_thread(self._auto_claim_chart, current_chart["id"])
                else:
                    self.app.call_from_thread(self.fetch_missions_data)
            else:
                err = resp.json().get("error", "Error al guardar la coordenada.")
                self.app.call_from_thread(
                    self.app.notify, err, severity="error")
        except Exception:
            pass

    def _auto_claim_chart(self, chart_id: int) -> None:
        """Reclama automáticamente un gráfico completado y muestra modal de recompensa."""
        self._request_chart_claim(chart_id)

    @work(thread=True)
    def _request_chart_claim(self, chart_id: int) -> None:
        try:
            resp = httpx.post(f"{API_POSADA_BASE}charts/claim/",
                              json={"chart_id": chart_id}, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(
                    self.app.push_screen, ChartRewardModal(data))
                self.app.call_from_thread(self.fetch_missions_data)
                self.app.call_from_thread(self.sync_guild_status)
            else:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message", "Error"), severity="warning")
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

    def _get_selected_habit_id(self) -> str | None:
        """Helper para obtener el ID del hábito seleccionado en las tablas activas."""
        for table_id in ["#good_habits_table", "#bad_habits_table"]:
            try:
                table = self.query_one(table_id, DataTable)
                if table.has_focus:
                    row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                    return row_key.value
            except Exception:
                pass
        return None

    def render_habits(self, habits):
        self.habits_cache = habits
        good_table = self.query_one("#good_habits_table", DataTable)
        bad_table = self.query_one("#bad_habits_table", DataTable)
        good_table.clear()
        bad_table.clear()
        for h in habits:
            if h.get("is_bad_habit"):
                status = "[bold red]Recaída[/]" if h["completed_today"] else "[bold green]Evitado[/]"
                estado_visual = f"🛡️ Resistencia: {h.get('current_streak', 0):>3} | {status}"
                name_fmt = f"[red](Evitar)[/] {h['name']}"
                bad_table.add_row(name_fmt, h["difficulty"], estado_visual, key=str(h["id"]))
            else:
                status = "[bold green]Completado[/]" if h["completed_today"] else "[gray]Pendiente[/]"
                estado_visual = f"🔥 Racha: {h.get('current_streak', 0):>3} | {status}"
                name_fmt = h['name']
                good_table.add_row(name_fmt, h["difficulty"], estado_visual, key=str(h["id"]))

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
        habit_id = self._get_selected_habit_id()
        if habit_id:
            self.request_habit_completion(habit_id)
        else:
            self.app.notify("Selecciona un hábito primero.", severity="warning")

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
        habit_id = self._get_selected_habit_id()
        if habit_id:
            self.request_habit_deletion(habit_id)
        else:
            self.app.notify("Selecciona un hábito de la tabla primero.", severity="warning")

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
        habit_id = self._get_selected_habit_id()
        if habit_id:
            try:
                resp = httpx.post(f"{API_POSADA_BASE}habits/undo/",
                                  json={"habit_id": habit_id})
                if resp.status_code == 200:
                    self.app.notify(resp.json().get("message"), severity="warning")
                    self.fetch_missions_data()
                    self.sync_guild_status()
                else:
                    self.app.notify(resp.json().get("message"), severity="error")
            except Exception:
                pass
        else:
            self.app.notify("Selecciona un hábito primero.", severity="warning")

    def action_claim_chart(self) -> None:
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if not hasattr(self, 'charts_cache') or not self.charts_cache:
            return

        current_chart = self.charts_cache[self.current_chart_index]
        self._request_chart_claim(current_chart["id"])

    def action_inspect_chart(self) -> None:
        """Abre el modal de inspección del gráfico actual."""
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        if not hasattr(self, 'charts_cache') or not self.charts_cache:
            self.app.notify("No hay gráficos para inspeccionar.", severity="warning")
            return
        current_chart = self.charts_cache[self.current_chart_index]
        self.app.push_screen(ChartDetailsModal(current_chart))

    def action_inspect_habit(self) -> None:
        """Abre el panel de detalle del hábito seleccionado."""
        if self.query_one(TabbedContent).active != "tab_missions":
            return
        habit_id = self._get_selected_habit_id()
        if habit_id:
            try:
                habit_data = next(h for h in getattr(
                    self, 'habits_cache', []) if str(h['id']) == habit_id)
                self.app.push_screen(HabitDetailsModal(habit_data))
            except Exception:
                pass
        else:
            self.app.notify("Selecciona un hábito de la tabla primero.", severity="warning")

    def action_delete_kanban_task(self):
        if self.query_one(TabbedContent).active != "tab_kanban":
            return
        # Intentamos obtener la tarea o columna
        for i in range(4):
            try:
                table = self.query_one(f"#kanban_col_{i}", DataTable)
                if table.has_focus:
                    row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                    task_id = int(row_key.value.split("_")[0])
                    self.app.push_screen(DeleteConfirmationModal("¿Borrar esta tarea?"), lambda res: self.execute_delete_task(res, task_id))
                    return
            except Exception:
                pass
        
        # Check calendar
        try:
            table = self.query_one("#calendar_table", DataTable)
            if table.has_focus:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                event_id = int(row_key.value)
                self.app.push_screen(DeleteConfirmationModal("¿Borrar este evento?"), lambda res: self.execute_delete_event(res, event_id))
                return
        except Exception:
            pass

    def action_edit_kanban_task(self):
        if self.query_one(TabbedContent).active != "tab_kanban":
            return
        for i in range(4):
            try:
                table = self.query_one(f"#kanban_col_{i}", DataTable)
                if table.has_focus:
                    row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                    task_id = int(row_key.value.split("_")[0])
                    columns = getattr(self, 'kanban_data', {}).get("columns", [])
                    for col in columns:
                        for task in col.get("tasks", []):
                            if task["id"] == task_id:
                                self.app.push_screen(EditKanbanTaskModal(task), self.submit_kanban_edit)
                                return
            except Exception:
                pass

    @work(thread=True)
    def submit_kanban_edit(self, edit_data: dict | None):
        if edit_data:
            try:
                task_id = edit_data.pop("task_id")
                resp = httpx.put(f"{API_POSADA_BASE}kanban/task/edit/{task_id}/", json=edit_data, timeout=5.0)
                if resp.status_code == 200:
                    self.app.call_from_thread(self.fetch_kanban_data)
            except Exception:
                pass

    def action_inspect_kanban(self) -> None:
        """Abre el panel de detalle de la tarea Kanban seleccionada o del evento del calendario."""
        if self.query_one(TabbedContent).active != "tab_kanban":
            return

        # 1. Intentar con las tablas Kanban
        for i in range(4):
            try:
                table = self.query_one(f"#kanban_col_{i}", DataTable)
                if table.has_focus:
                    row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                    if row_key:
                        task_id = int(row_key.value.split("_")[0])
                        col_id = int(row_key.value.split("_col")[1])
                        # Buscar datos de la tarea y nombre de columna en el cache
                        columns = getattr(self, 'kanban_data', {}).get("columns", [])
                        for col in columns:
                            if col["id"] == col_id:
                                for task in col["tasks"]:
                                    if task["id"] == task_id:
                                        self.app.push_screen(
                                            KanbanTaskDetailsModal(task, column_name=col["title"]))
                                        return
                    return
            except Exception:
                continue

        # 2. Intentar con la tabla del calendario
        try:
            cal_table = self.query_one("#calendar_table", DataTable)
            if cal_table.has_focus:
                row_key = cal_table.coordinate_to_cell_key(cal_table.cursor_coordinate).row_key
                if row_key:
                    event_id = int(row_key.value)
                    # Buscar el evento en el caché renderizado
                    self._fetch_and_show_calendar_event(event_id)
                    return
        except Exception:
            pass

        self.app.notify(
            "Selecciona una tarea o evento de la tabla primero.", severity="warning")

    @work(thread=True)
    def _fetch_and_show_calendar_event(self, event_id: int):
        """Busca un evento específico del calendario para mostrar sus detalles."""
        import datetime
        now = datetime.datetime.now()
        try:
            resp = httpx.get(f"{API_POSADA_BASE}calendar/{now.year}/{now.month}/", timeout=5.0)
            if resp.status_code == 200:
                events = resp.json().get("events", [])
                event_data = next((e for e in events if e["id"] == event_id), None)
                if event_data:
                    self.app.call_from_thread(
                        self.app.push_screen, CalendarEventDetailsModal(event_data))
                else:
                    self.app.call_from_thread(
                        self.app.notify, "Evento no encontrado.", severity="warning")
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "Error al obtener detalles del evento.", severity="error")

    # --- DIARIO DE VIAJE ---
    @work(thread=True)
    def fetch_journal(self):
        try:
            resp = httpx.get(f"{API_POSADA_BASE}journal/", timeout=5.0)
            if resp.status_code == 200:
                self.journal_entries = resp.json().get("entries", [])
                self.app.call_from_thread(self.render_journal_init)
        except Exception:
            pass

    def render_journal_init(self):
        if not hasattr(self, 'journal_entries'):
            return
        total_pages = (len(self.journal_entries) + 1) // 2
        if total_pages == 0:
            total_pages = 1
        # Ir a la última página automáticamente
        self.current_journal_page = total_pages - 1
        self.render_journal()

    def render_journal(self):
        if not hasattr(self, 'journal_entries'):
            return
        entries = self.journal_entries
        idx = getattr(self, 'current_journal_page', 0) * 2

        # Página Izquierda
        if idx < len(entries):
            self.query_one("#page_left_date", Label).update(
                entries[idx]['timestamp'])
            self.query_one("#page_left_content", Label).update(
                entries[idx]['content'])
        else:
            self.query_one("#page_left_date", Label).update("Página en blanco")
            self.query_one("#page_left_content", Label).update(
                "El futuro aún no está escrito...")

        # Página Derecha
        if idx + 1 < len(entries):
            self.query_one("#page_right_date", Label).update(
                entries[idx+1]['timestamp'])
            self.query_one("#page_right_content", Label).update(
                entries[idx+1]['content'])
        else:
            self.query_one("#page_right_date", Label).update(
                "Página en blanco")
            self.query_one("#page_right_content", Label).update(
                "El futuro aún no está escrito...")

    def action_prev_journal_page(self):
        if self.query_one(TabbedContent).active != "tab_journal":
            return
        if getattr(self, 'current_journal_page', 0) > 0:
            self.current_journal_page -= 1
            self.render_journal()

    def action_next_journal_page(self):
        if self.query_one(TabbedContent).active != "tab_journal":
            return
        entries = getattr(self, 'journal_entries', [])
        total_pages = (len(entries) + 1) // 2
        if total_pages == 0:
            total_pages = 1
        if getattr(self, 'current_journal_page', 0) < total_pages - 1:
            self.current_journal_page += 1
            self.render_journal()

    def action_write_journal(self):
        if self.query_one(TabbedContent).active != "tab_journal":
            return
        self.app.push_screen(WriteJournalModal(), self.submit_journal_entry)

    @work(thread=True)
    def submit_journal_entry(self, text: str | None):
        if not text:
            return
        try:
            resp = httpx.post(f"{API_POSADA_BASE}journal/create/",
                              json={"content": text}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_journal)
                self.app.call_from_thread(self.sync_guild_status)
        except Exception:
            self.app.call_from_thread(
                self.app.notify, "El Gremio no responde.", severity="error")

    # --- MANEJADORES DE TECLAS COMPARTIDAS (CONFLICT RESOLUTION) ---
    def action_handle_n(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_guild": self.action_new_adventurer()
        elif active_tab == "tab_missions": self.action_new_chart()
        
    def action_handle_c(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_timer": self.action_setup_timer()
        elif active_tab == "tab_kanban": self.action_new_kanban_col()

    def action_open_bestiary(self) -> None:
        if self.active_tab == "tab_guild":
            self.app.push_screen(BestiaryCodexModal())

    def action_load_chronicles(self) -> None:
        """Carga las sesiones completadas desde la API y llena la tabla de crónicas."""
        import requests
        try:
            resp = requests.get("http://localhost:8009/posada/api/chronicles/")
            if resp.status_code == 200:
                self.chronicles_data = resp.json().get("chronicles", [])
                table = self.query_one("#chronicles_table", DataTable)
                table.clear(columns=True)
                table.add_columns("Fecha", "Categoría", "Duración", "Grupo")
                for i, s in enumerate(self.chronicles_data):
                    group = ", ".join(s["adventurers"][:3]) or "—"
                    table.add_row(
                        s["start_time"], 
                        s["category"], 
                        f"{s['duration_minutes']} min",
                        group,
                        key=str(i)
                    )
                self.query_one("#lbl_chronicles_hint", Label).update(
                    f"📜 {len(self.chronicles_data)} sesiones encontradas. Selecciona una para leer su crónica."
                )
        except Exception:
            self.notify("Error al cargar crónicas.", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler global para cuando se selecciona una fila en una DataTable."""
        table_id = event.data_table.id

        # --- Chronicles Table ---
        if table_id == "chronicles_table" and hasattr(self, 'chronicles_data'):
            idx = int(event.row_key.value)
            session = self.chronicles_data[idx]
            log_widget = self.query_one("#chronicles_log", RichLog)
            log_widget.clear()
            log_widget.write(f"[bold yellow]═══ {session['category']} | {session['start_time']} | {session['duration_minutes']} min ═══[/bold yellow]\n")
            log_widget.write(f"[dim]Grupo: {', '.join(session['adventurers']) or '—'}[/dim]\n")
            log_widget.write("─" * 60 + "\n")
            for entry in session["event_log"]:
                if isinstance(entry, str):
                    log_widget.write(entry)
                elif isinstance(entry, dict) and "message" in entry:
                    log_widget.write(entry["message"])
            self.query_one("#lbl_chronicles_hint", Label).display = False
            return

    # --------------------------------------------------------
    # MÉTODOS DE LA API (HTTP)

    def action_handle_x(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_guild": self.action_delete_adventurer()
        elif active_tab == "tab_kanban": self.action_delete_kanban_task()
        
    def action_handle_i(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_missions": self.action_inspect_chart()
        elif active_tab == "tab_kanban": self.action_inspect_kanban()

    def action_handle_e(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_kanban":
            self.action_edit_kanban_task()
            self.action_edit_calendar_event()

    def action_handle_left(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_kanban": self.action_move_kanban_left()
        elif active_tab == "tab_journal": self.action_prev_journal_page()
        
    def action_handle_right(self):
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab_kanban": self.action_move_kanban_right()
        elif active_tab == "tab_journal": self.action_next_journal_page()

    # --- KANBAN LOGIC ---
    @work(thread=True)
    def fetch_kanban_data(self):
        try:
            resp = httpx.get(f"{API_POSADA_BASE}kanban/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_kanban, resp.json())
        except Exception:
            pass

    def render_kanban(self, data: dict):
        self.kanban_data = data
        board_name = data.get("board_name", "Mi Tablero")
        self.query_one("#lbl_kanban_title", Label).update(f"Kanban: {board_name}")
        columns = data.get("columns", [])

        # Tenemos 4 DataTables estáticos
        for i in range(4):
            try:
                table = self.query_one(f"#kanban_col_{i}", DataTable)
                table.clear(columns=True)
                if i < len(columns):
                    table.display = True
                    col = columns[i]
                    table.add_column(f"[{col['color']}]{col['title']}[/]", width=40)
                    for task in col['tasks']:
                        quest_icon = task.get('quest_rank', '').split(' ')[0] if task.get('quest_rank') else ''
                        table.add_row(f"{quest_icon} [{task['priority_code']}] {task['title']}", key=f"{task['id']}_col{col['id']}")
                else:
                    table.display = False
            except Exception:
                pass

    def action_new_kanban_task(self):
        if self.query_one(TabbedContent).active != "tab_kanban":
            return
        self.app.push_screen(NewKanbanTaskModal(), self.submit_kanban_task)

    @work(thread=True)
    def submit_kanban_task(self, task_data: dict | None):
        if not task_data: return
        try:
            resp = httpx.post(f"{API_POSADA_BASE}kanban/task/create/", json=task_data, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_kanban_data)
        except Exception:
            pass

    def action_new_kanban_col(self):
        if self.query_one(TabbedContent).active != "tab_kanban":
            return
        self.app.push_screen(NewKanbanColumnModal(), self.submit_kanban_col)

    @work(thread=True)
    def submit_kanban_col(self, col_data: dict | None):
        if not col_data: return
        try:
            resp = httpx.post(f"{API_POSADA_BASE}kanban/column/create/", json=col_data, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_kanban_data)
        except Exception:
            pass

    def _get_focused_kanban_task(self):
        """Busca cuál tabla tiene foco y qué fila está seleccionada."""
        for i in range(4):
            try:
                table = self.query_one(f"#kanban_col_{i}", DataTable)
                if table.has_focus:
                    row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                    if row_key:
                        task_id = int(row_key.value.split("_")[0])
                        return task_id
            except Exception:
                continue
        return None

    @work(thread=True)
    def _move_task(self, task_id, direction):
        try:
            resp = httpx.post(f"{API_POSADA_BASE}kanban/task/move/", json={"task_id": task_id, "direction": direction}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_kanban_data)
                self.app.call_from_thread(self.sync_guild_status)
        except Exception:
            pass

    def action_move_kanban_left(self):
        if self.query_one(TabbedContent).active != "tab_kanban": return
        task_id = self._get_focused_kanban_task()
        if task_id: self._move_task(task_id, "left")

    def action_move_kanban_right(self):
        if self.query_one(TabbedContent).active != "tab_kanban": return
        task_id = self._get_focused_kanban_task()
        if task_id: self._move_task(task_id, "right")

    @work(thread=True)
    def action_delete_kanban_task(self):
        if self.query_one(TabbedContent).active != "tab_kanban": return
        task_id = self._get_focused_kanban_task()
        if task_id:
            try:
                resp = httpx.delete(f"{API_POSADA_BASE}kanban/task/delete/{task_id}/", timeout=5.0)
                if resp.status_code == 200:
                    self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="warning")
                    self.app.call_from_thread(self.fetch_kanban_data)
            except Exception:
                pass

    # --- CALENDAR LOGIC ---
    @work(thread=True)
    def fetch_calendar_data(self):
        import datetime
        now = datetime.datetime.now()
        try:
            resp = httpx.get(f"{API_POSADA_BASE}calendar/{now.year}/{now.month}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.render_calendar, resp.json())
        except Exception:
            pass

    def render_calendar(self, data: dict):
        self.calendar_data = data
        events = data.get("events", [])
        table = self.query_one("#calendar_table", DataTable)
        table.clear(columns=True)
        table.add_columns("📅 Fecha", "✨ Evento", "📝 Descripción", "Estado")
        
        from datetime import date as dt_date
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

        for e in sorted(events, key=lambda x: x['date']):
            try:
                d = dt_date.fromisoformat(e['date'])
                day_name = dias_semana[d.weekday()]
                fecha_str = f"[{e['color']}]{day_name} {d.day:02d}[/]"
            except:
                fecha_str = f"[{e['color']}]{e['date']}[/]"
                
            if e['is_important']:
                title_col = f"[bold yellow]⭐ {e['title']}[/bold yellow]"
            else:
                title_col = f"[white]🔹 {e['title']}[/white]"
                
            status = e.get('status', 'PENDING')
            if status == 'TODAY':
                status_str = "[bold magenta]⭐ Hoy[/bold magenta]"
            elif status == 'DONE':
                status_str = "[bold green]✅ Hecho[/bold green]"
            else:
                status_str = "[dim white]Pendiente[/dim white]"
                
            table.add_row(fecha_str, title_col, f"[dim]{e['description']}[/dim]", status_str, key=str(e['id']))

    def action_new_calendar_event(self):
        if self.query_one(TabbedContent).active != "tab_kanban": return
        self.app.push_screen(NewCalendarEventModal(), self.submit_calendar_event)

    @work(thread=True)
    def submit_calendar_event(self, event_data: dict | None):
        if not event_data: return
        try:
            resp = httpx.post(f"{API_POSADA_BASE}calendar/event/create/", json=event_data, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="success")
                self.app.call_from_thread(self.fetch_calendar_data)
                self.app.call_from_thread(self.sync_guild_status)
        except Exception:
            pass

    def action_edit_calendar_event(self):
        if self.query_one(TabbedContent).active != "tab_kanban": return
        try:
            table = self.query_one("#calendar_table", DataTable)
            if table.has_focus:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                event_id = int(row_key.value)
                # Find event data
                events = getattr(self, 'calendar_data', {}).get("events", [])
                for e in events:
                    if e["id"] == event_id:
                        self.app.push_screen(EditCalendarEventModal(e), self.submit_calendar_edit)
                        return
        except Exception:
            pass

    @work(thread=True)
    def submit_calendar_edit(self, edit_data: dict | None):
        if edit_data:
            try:
                event_id = edit_data.pop("event_id")
                resp = httpx.put(f"{API_POSADA_BASE}calendar/event/edit/{event_id}/", json=edit_data, timeout=5.0)
                if resp.status_code == 200:
                    self.app.call_from_thread(self.fetch_calendar_data)
            except Exception:
                pass

    @work(thread=True)
    def execute_delete_event(self, confirm: bool, event_id: int):
        if not confirm: return
        try:
            resp = httpx.delete(f"{API_POSADA_BASE}calendar/event/delete/{event_id}/", timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.app.notify, resp.json().get("message"), severity="warning")
                self.app.call_from_thread(self.fetch_calendar_data)
        except Exception:
            pass
