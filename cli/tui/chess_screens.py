import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Static, Tree, Input
from textual.containers import Vertical, Grid, Horizontal
from textual import work
from textual.binding import Binding
from .constants import API_CHESS_ROOMS, API_CHESS_NOTES, API_CHESS_PARSE, API_CHESS_DIRS, API_CHESS_EVALUATE, API_CHESS_VALIDATE, API_CHESS_VARIATIONS
from .modals import ImportPGNModal, ChessNoteModal, ChessDirModal, ConfirmModal, CreateGameModal


def render_eval_bar(percentage: float, height: int = 26) -> str:
    """Dibuja una barra de evaluación vertical estilo chess.com usando bloques sólidos.

    Args:
        percentage: 0-100, donde 100 = blancas ganan totalmente, 0 = negras ganan.
        height: altura de la barra en líneas de texto.
    """
    percentage = max(0.0, min(100.0, percentage))
    white_lines = round(height * percentage / 100.0)
    black_lines = height - white_lines

    bar = "█"  # Bloque sólido que llena el ancho completo

    lines = []
    for i in range(height):
        if i < black_lines:
            lines.append(f"[#1A1A1A]{bar * 3}[/]")
        else:
            lines.append(f"[#E0E0E0]{bar * 3}[/]")

    return "\n".join(lines)


def render_fen(fen: str) -> str:
    """Dibuja un tablero de alta fidelidad con proporciones geométricas perfectas."""
    # TRUCO: Volvemos a las piezas rellenas para ambos bandos.
    # Para que las piezas blancas (#FFFFFF) no se camuflen en las casillas claras,
    # el truco está en oscurecer la paleta del tablero. Al usar un tono medio/oscuro
    # para las casillas "claras", el blanco puro resalta con un contraste espectacular.
    solid_pieces = {
        'r': ('♜', '#000000'), 'n': ('♞', '#000000'), 'b': ('♝', '#000000'),
        'q': ('♛', '#000000'), 'k': ('♚', '#000000'), 'p': ('♟', '#000000'),
        'R': ('♜', '#FFFFFF'), 'N': ('♞', '#FFFFFF'), 'B': ('♝', '#FFFFFF'),
        'Q': ('♛', '#FFFFFF'), 'K': ('♚', '#FFFFFF'), 'P': ('♟', '#FFFFFF')
    }
    light_bg = "on #999B7C"  # Verde crema oscuro (antes #EBECD0)
    dark_bg = "on #52663A"   # Verde bosque oscuro (antes #779556)

    rows = fen.split()[0].split('/')
    out = "\n"

    for r_idx, row in enumerate(rows):
        rank = 8 - r_idx
        squares = []
        for char in row:
            if char.isdigit():
                squares.extend([None] * int(char))
            else:
                squares.append(char)

        line1 = "   "
        line2 = f"[bold #A0A0A0]{rank}[/]  "
        line3 = "   "

        for c_idx, piece in enumerate(squares):
            bg = light_bg if (r_idx + c_idx) % 2 == 0 else dark_bg
            line1 += f"[{bg}]       [/]"
            if piece:
                char, color = solid_pieces[piece]
                line2 += f"[bold {color} {bg}]   {char}   [/]"
            else:
                line2 += f"[{bg}]       [/]"
            line3 += f"[{bg}]       [/]"

        out += line1 + "\n" + line2 + "\n" + line3 + "\n"

    out += "      [bold #A0A0A0]a      b      c      d      e      f      g      h[/]\n"
    return out


class ChessMainScreen(Screen):
    """Laboratorio Táctico de Ajedrez."""

    BINDINGS = [
        Binding("escape, q", "go_back", "Volver", show=False),
        Binding("c", "create_game", "Nueva Partida"),
        Binding("d", "add_dir", "Carpeta"),
        Binding("a", "add_pgn", "Importar PGN"),
        Binding("n", "edit_note", "Anotar"),
        Binding("delete, x", "delete_note", "Borrar Nota"),
        Binding("backspace", "delete_node", "Borrar Árbol"),
        Binding("z", "undo_move", "Deshacer"),
        Binding("e", "evaluate_pos", "Oráculo"),
        Binding("v", "show_variations", "Variantes"),
        Binding("b", "back_to_mainline", "Principal"),
    ]

    CSS = """
    #chess_root {
        layout: grid;
        grid-size: 3 2;
        grid-columns: 1fr 1.5fr 1fr;
        grid-rows: 2fr 1fr;
        padding: 1 2;
        grid-gutter: 1 2;
    }
    
    #tree_panel { row-span: 2; border: heavy $accent; background: $surface; height: 100%; padding: 0; margin: 0; }
    
    /* Panel Central Rediseñado */
    #center_panel {
        row-span: 2;
        height: 100%;
        layout: vertical;
    }
    
    #board_container {
        height: 1fr;
        border: heavy $success;
        background: $surface;
        align: center middle;
        content-align: center middle;
        layout: horizontal;
    }
    
    #eval_bar {
        width: 3;
        height: 26;
        margin-right: 1;
        padding: 0;
        border: none;
        overflow: hidden;
    }
    
    #board_view { text-align: left; width: auto; }
    
    #oracle_panel {
        height: 3;
        border: solid $secondary;
        background: $surface-darken-1;
        content-align: center middle;
        color: $text-muted;
    }
    
    #manual_move_input {
        dock: bottom;
        margin-top: 1;
        border: solid $primary;
    }
    
    #moves_panel { border: heavy $warning; background: $surface; height: 100%; }
    #notes_panel { border: heavy $primary; background: $surface; height: 100%; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:

        yield Header(show_clock=True)

        with Grid(id="chess_root"):
            with Vertical(id="tree_panel"):
                yield Tree("Archivos Tácticos", id="chess_tree")

            # EL NUEVO NÚCLEO CENTRAL
            with Vertical(id="center_panel"):
                with Horizontal(id="board_container"):
                    # Barra de Evaluación Vertical (Custom)
                    yield Static(render_eval_bar(50.0), id="eval_bar")
                    # Tablero Geométrico
                    yield Static(render_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"), id="board_view")

                # Panel del Oráculo (Stockfish)
                yield Static("Oráculo inactivo. Presiona 'E' para evaluar posición.", id="oracle_panel")

            with Vertical(id="moves_panel"):
                yield DataTable(id="moves_table")
                # Barra para crear estudios (Input Manual)
                yield Input(placeholder="Ingresa jugada (Ej: e4, Nf3)...", id="manual_move_input")

            with Vertical(id="notes_panel"):
                yield Markdown("### Apuntes Teóricos\n\nPresiona **A** para importar un PGN, o **D** para crear una carpeta.", id="notes_view")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "BUNKER"
        self.sub_title = "Laboratorio de Ajedrez"

        self.current_room_id = None
        self.current_moves = []
        self.current_notes = {}
        self.current_ply = 0
        self.raw_dirs = []

        # --- Estado de Variaciones ---
        self.variations = {}          # {parent_ply: [{"id": ..., "moves_san": [...], ...}, ...]}
        self.active_variation = None  # Dict de la variación activa (o None = línea principal)
        self.active_var_moves = []    # Jugadas expandidas de la variación activa
        self.active_var_ply = 0       # Ply dentro de la variación activa

        table = self.query_one("#moves_table", DataTable)
        table.cursor_type = "cell"
        table.zebra_stripes = True
        table.add_columns("Turno", "Blancas", "Negras")

        # Cargamos el árbol apenas entramos
        self.fetch_library()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    # --- ÁRBOL DE DIRECTORIOS (ESTILO NVIMTREE) ---
    @work(thread=True)
    def fetch_library(self) -> None:
        try:
            dirs_resp = httpx.get(API_CHESS_DIRS, timeout=5.0)
            rooms_resp = httpx.get(API_CHESS_ROOMS, timeout=5.0)
            if dirs_resp.status_code == 200 and rooms_resp.status_code == 200:
                self.app.call_from_thread(
                    self.build_tree, dirs_resp.json(), rooms_resp.json())
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error cargando árbol: {e}", severity="error")

    def build_tree(self, dirs: list, rooms: list) -> None:
        tree = self.query_one("#chess_tree", Tree)
        tree.clear()
        tree.root.expand()

        self.raw_dirs = dirs
        nodes = {None: tree.root}

        dirs_sorted = sorted(dirs, key=lambda x: x['parent'] or 0)
        for d in dirs_sorted:
            parent_node = nodes.get(d['parent'], tree.root)
            node = parent_node.add(
                f"📁 [bold]{d['name']}[/]", data={"type": "dir", "id": d['id']})
            nodes[d['id']] = node

        for r in rooms:
            parent_node = nodes.get(r['directory'], tree.root)
            parent_node.add(f"♟️ {r['title']}", data={
                            "type": "room", "id": r['id'], "pgn": r['pgn_data']})

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return

        if data.get("type") == "room":
            self.app.notify("Desplegando tablero...", title="Cargando")
            self.process_load_room(data["id"], data["pgn"])
        elif data.get("type") == "dir":
            event.node.toggle()

    @work(thread=True)
    def process_load_room(self, room_id: int, pgn_data: str) -> None:
        try:
            parse_resp = httpx.post(API_CHESS_PARSE, json={
                                    "pgn": pgn_data}, timeout=10.0)
            if parse_resp.status_code == 200:
                moves = parse_resp.json().get("moves", [])
                self.app.call_from_thread(
                    self.load_game_into_ui, room_id, moves)
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al reconstruir la partida.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    def action_create_game(self) -> None:
        def handle_create(payload: dict | None) -> None:
            if payload and payload.get("title"):
                self.app.notify(
                    "Creando partida táctica...", title="Laboratorio")
                self.process_create_game(payload)
        self.app.push_screen(CreateGameModal(self.raw_dirs), handle_create)

    @work(thread=True)
    def process_create_game(self, payload: dict) -> None:
        try:
            room_resp = httpx.post(API_CHESS_ROOMS, json={
                "title": payload["title"],
                "directory": payload.get("directory"),
                "pgn_data": ""
            }, timeout=5.0)

            if room_resp.status_code == 201:
                room_data = room_resp.json()
                # Posición inicial para la interfaz
                moves = [{
                    "ply": 0,
                    "san": "Posición Inicial",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
                    "turn": "white"
                }]
                self.app.call_from_thread(
                    self.load_game_into_ui, room_data["id"], moves)
                self.app.call_from_thread(self.fetch_library)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Rechazo de BD: {room_resp.text}", severity="error", timeout=8)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    def action_add_dir(self) -> None:
        def handle_dir(payload: dict | None) -> None:
            if payload:
                self.process_save_dir(payload)
        self.app.push_screen(ChessDirModal(self.raw_dirs), handle_dir)

    @work(thread=True)
    def process_save_dir(self, payload: dict) -> None:
        try:
            resp = httpx.post(API_CHESS_DIRS, json=payload, timeout=5.0)
            if resp.status_code == 201:
                self.app.call_from_thread(
                    self.app.notify, "Directorio creado.", title="Éxito")
                self.fetch_library()
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error creando directorio.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def action_add_pgn(self) -> None:
        def handle_pgn(payload: dict | None) -> None:
            if payload and payload.get("pgn"):
                self.app.notify(
                    "Analizando PGN y sincronizando con la BD...", title="Oráculo")
                self.process_pgn(payload)
        self.app.push_screen(ImportPGNModal(self.raw_dirs), handle_pgn)

    @work(thread=True)
    def process_pgn(self, payload: dict) -> None:
        try:
            parse_resp = httpx.post(API_CHESS_PARSE, json={
                                    "pgn": payload["pgn"]}, timeout=10.0)
            if parse_resp.status_code == 200:
                parse_data = parse_resp.json()
                moves = parse_data.get("moves", [])

                room_resp = httpx.post(API_CHESS_ROOMS, json={
                    "title": payload["title"] or "Partida sin título",
                    "directory": payload.get("directory"),
                    "pgn_data": payload["pgn"]
                }, timeout=5.0)

                if room_resp.status_code == 201:
                    room_data = room_resp.json()
                    self.app.call_from_thread(
                        self.load_game_into_ui, room_data["id"], moves)
                    self.app.call_from_thread(self.fetch_library)
                else:
                    self.app.call_from_thread(
                        self.app.notify, f"Rechazo de BD: {room_resp.text}", severity="error", timeout=8)
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error de Parseo: {parse_resp.text}", severity="error", timeout=8)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red crítico: {e}", severity="error")

    def load_game_into_ui(self, room_id: int, moves: list) -> None:
        self.current_room_id = room_id
        self.current_moves = moves
        self.current_notes = {}
        self.current_ply = 0

        # Reset variaciones
        self.variations = {}
        self.active_variation = None
        self.active_var_moves = []
        self.active_var_ply = 0

        self.refresh_moves_table()

        table = self.query_one("#moves_table", DataTable)
        table.focus()
        self.fetch_notes()
        self.fetch_variations()
        if self.current_moves:
            self.query_one("#board_view", Static).update(
                render_fen(self.current_moves[0]["fen"]))

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        if not self.current_moves:
            return

        coord = event.coordinate
        ply = (coord.row * 2) + 1 if coord.column <= 1 else (coord.row * 2) + 2

        if self.active_variation:
            # Navegamos dentro de la variación
            moves = self.active_var_moves
            if ply < len(moves):
                self.active_var_ply = ply
            else:
                self.active_var_ply = len(moves) - 1
            fen = moves[self.active_var_ply]["fen"]
        else:
            # Navegamos la línea principal
            if ply < len(self.current_moves):
                self.current_ply = ply
            else:
                self.current_ply = len(self.current_moves) - 1
            fen = self.current_moves[self.current_ply]["fen"]

        self.query_one("#board_view", Static).update(render_fen(fen))
        self.refresh_notes_panel()

    @work(thread=True)
    def fetch_notes(self) -> None:
        if not self.current_room_id:
            return
        try:
            resp = httpx.get(
                f"{API_CHESS_ROOMS}{self.current_room_id}/", timeout=5.0)
            if resp.status_code == 200:
                notes_list = resp.json().get("notes", [])
                # Clave compuesta: (ply_number, variation_id) para distinguir notas de variación
                notes_dict = {}
                for n in notes_list:
                    key = (n["ply_number"], n.get("variation"))
                    notes_dict[key] = {"id": n["id"], "text": n["text"]}
                self.app.call_from_thread(self.update_notes_dict, notes_dict)
        except Exception:
            pass

    def update_notes_dict(self, notes_dict: dict) -> None:
        self.current_notes = notes_dict
        self.refresh_notes_panel()

    def _get_note_key(self) -> tuple:
        """Devuelve la clave de nota para la posición actual (ply, variation_id)."""
        var_id = self.active_variation.get("id") if self.active_variation else None
        ply = self.active_var_ply if self.active_variation else self.current_ply
        return (ply, var_id)

    def refresh_notes_panel(self) -> None:
        md = self.query_one("#notes_view", Markdown)
        if not self.current_moves:
            return

        key = self._get_note_key()
        note_data = self.current_notes.get(key, {})
        note_text = note_data.get("text", "*Sin apuntes para esta posición.*")

        if self.active_variation and self.active_var_moves:
            current_san = self.active_var_moves[self.active_var_ply].get("san", "?")
            header = f"### ⑂ Variación — Jugada: `{current_san}`"
        else:
            current_san = self.current_moves[self.current_ply].get("san", "Inicial")
            header = f"### Análisis de Jugada: `{current_san}`"

        content = f"{header}\n\n{note_text}"
        md.update(content)

    def action_edit_note(self) -> None:
        ply = self.active_var_ply if self.active_variation else self.current_ply
        if not self.current_room_id or ply == 0:
            self.app.notify(
                "Selecciona una jugada blanca o negra en la tabla.", severity="warning")
            return

        key = self._get_note_key()
        existing_text = self.current_notes.get(key, {}).get("text", "")

        def save_note(text: str | None) -> None:
            if text is not None:
                self.process_save_note(text)
        self.app.push_screen(ChessNoteModal(existing_text), save_note)

    @work(thread=True)
    def process_save_note(self, text: str) -> None:
        try:
            key = self._get_note_key()
            ply = key[0]
            var_id = key[1]
            existing_note = self.current_notes.get(key)

            if existing_note and "id" in existing_note:
                resp = httpx.patch(
                    f"{API_CHESS_NOTES}{existing_note['id']}/", json={"text": text}, timeout=5.0)
            else:
                # Determinar el SAN de la jugada actual
                if self.active_variation and self.active_var_moves:
                    move_san = self.active_var_moves[self.active_var_ply].get("san", "")
                else:
                    move_san = self.current_moves[self.current_ply].get("san", "")

                payload = {
                    "room": self.current_room_id,
                    "ply_number": ply,
                    "move_san": move_san,
                    "text": text,
                    "variation": var_id
                }
                resp = httpx.post(API_CHESS_NOTES, json=payload, timeout=5.0)

            if resp.status_code in [200, 201]:
                self.app.call_from_thread(
                    self.app.notify, "Nota táctica archivada.", title="Éxito")
                self.fetch_notes()
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error DB Notas: {resp.text}", severity="error", timeout=8)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

# --- SISTEMA DE ELIMINACIÓN ---
    def action_delete_node(self) -> None:
        tree = self.query_one("#chess_tree", Tree)
        node = tree.cursor_node
        if not node or not node.data:
            return

        def check_del(confirm: bool) -> None:
            if confirm:
                self.process_delete_node(node.data)

        tipo = "carpeta" if node.data['type'] == 'dir' else "partida"
        self.app.push_screen(ConfirmModal(
            f"¿Destruir irreversiblemente esta {tipo}?"), check_del)

    @work(thread=True)
    def process_delete_node(self, data: dict) -> None:
        try:
            endpoint = API_CHESS_DIRS if data['type'] == 'dir' else API_CHESS_ROOMS
            resp = httpx.delete(f"{endpoint}{data['id']}/", timeout=5.0)
            if resp.status_code == 204:
                self.app.call_from_thread(
                    self.app.notify, "Elemento destruido.", title="Éxito")
                self.app.call_from_thread(self.fetch_library)
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al eliminar.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def action_delete_note(self) -> None:
        if not self.current_moves or self.current_ply not in self.current_notes:
            return

        def check_del(confirm: bool) -> None:
            if confirm:
                self.process_delete_note(
                    self.current_notes[self.current_ply]["id"])

        self.app.push_screen(ConfirmModal(
            "¿Eliminar los apuntes de esta jugada?"), check_del)

    @work(thread=True)
    def process_delete_note(self, note_id: int) -> None:
        try:
            resp = httpx.delete(f"{API_CHESS_NOTES}{note_id}/", timeout=5.0)
            if resp.status_code == 204:
                self.app.call_from_thread(
                    self.app.notify, "Nota eliminada.", title="Éxito")
                self.fetch_notes()
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error al eliminar nota.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    # --- MODO ESTUDIO (INPUT MANUAL) ---
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Captura cuando presionas Enter en la barra de comandos de ajedrez."""
        if event.control.id == "manual_move_input":
            san_move = event.value.strip()
            if san_move:
                self.process_manual_move(san_move)
                event.control.value = ""  # Limpia la barra tras enviar

    @work(thread=True)
    def process_manual_move(self, san_move: str) -> None:
        # Determinamos el FEN actual según contexto (variación o línea principal)
        if self.active_variation and self.active_var_moves:
            current_fen = self.active_var_moves[self.active_var_ply]["fen"]
        elif self.current_moves:
            current_fen = self.current_moves[self.current_ply]["fen"]
        else:
            current_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

        try:
            resp = httpx.post(API_CHESS_VALIDATE, json={
                              "fen": current_fen, "san": san_move}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.apply_manual_move, resp.json(), san_move)
            else:
                err = resp.json().get("error", "Movimiento inválido")
                self.app.call_from_thread(
                    self.app.notify, f"Ilegal: {err}", severity="warning")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def apply_manual_move(self, data: dict, san_move: str) -> None:
        # --- Si estamos dentro de una variación activa, extendemos esa variación ---
        if self.active_variation:
            self.active_variation["moves_san"].append(san_move)
            new_ply = self.active_var_ply + 1
            self.active_var_moves.append({
                "ply": new_ply, "san": san_move,
                "fen": data["new_fen"], "turn": data["turn"]
            })
            self.active_var_ply = new_ply
            self.query_one("#board_view", Static).update(render_fen(data["new_fen"]))
            self.refresh_moves_table()
            self.save_variation_to_db(self.active_variation)
            return

        # --- Línea principal: detectar si es un FORK ---
        next_ply = self.current_ply + 1
        if next_ply < len(self.current_moves):
            existing_san = self.current_moves[next_ply]["san"]
            if san_move != existing_san:
                # ¡FORK! Crear una nueva bifurcación
                self.create_variation(self.current_ply, san_move, data)
                return

        # --- Jugada normal al final de la línea ---
        new_ply = self.current_ply + 1
        if new_ply < len(self.current_moves):
            self.current_moves = self.current_moves[:new_ply]

        move_entry = {
            "ply": new_ply, "san": data["san"],
            "fen": data["new_fen"], "turn": data["turn"]
        }
        if not self.current_moves:
            self.current_moves.append(
                {"ply": 0, "san": "Inicial", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", "turn": "white"})

        self.current_moves.append(move_entry)
        self.current_ply = new_ply
        self.query_one("#board_view", Static).update(render_fen(data["new_fen"]))
        self.refresh_moves_table()
        self.save_mainline_to_db()

    @work(thread=True)
    def save_mainline_to_db(self) -> None:
        if not self.current_room_id or not self.current_moves:
            return
        
        # Obtenemos todas las jugadas SAN (excluyendo la inicial)
        moves_san = [m["san"] for m in self.current_moves[1:]]
        
        try:
            resp = httpx.patch(f"{API_CHESS_ROOMS}{self.current_room_id}/update_mainline/", json={
                "moves_san": moves_san
            }, timeout=5.0)
            if resp.status_code != 200:
                self.app.call_from_thread(
                    self.app.notify, f"Error DB Principal: {resp.text}", severity="warning")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error red (guardado): {e}", severity="error")

    def action_undo_move(self) -> None:
        """Deshace el último movimiento de la línea activa si estamos en la punta."""
        if self.active_variation:
            if self.active_var_ply == len(self.active_var_moves) - 1 and self.active_var_ply > 1:
                # Borramos la última jugada de la variación
                self.active_var_moves.pop()
                self.active_variation["moves_san"].pop()
                self.active_var_ply -= 1
                self.query_one("#board_view", Static).update(render_fen(self.active_var_moves[-1]["fen"]))
                self.refresh_moves_table()
                self.save_variation_to_db(self.active_variation)
                self.app.notify("Jugada deshecha (Variación).", severity="information")
            else:
                self.app.notify("Solo puedes deshacer la última jugada de la rama activa.", severity="warning")
        else:
            if self.current_ply == len(self.current_moves) - 1 and self.current_ply > 0:
                self.current_moves.pop()
                self.current_ply -= 1
                self.query_one("#board_view", Static).update(render_fen(self.current_moves[-1]["fen"]))
                self.refresh_moves_table()
                self.save_mainline_to_db()
                self.app.notify("Jugada deshecha (Principal).", severity="information")
            else:
                self.app.notify("Solo puedes deshacer la última jugada de la línea.", severity="warning")

    def create_variation(self, parent_ply: int, san_move: str, data: dict) -> None:
        """Crea una bifurcación desde parent_ply con la nueva jugada."""
        new_var = {
            "id": None,  # Se asignará tras guardarse en la BD
            "room": self.current_room_id,
            "parent_ply": parent_ply,
            "parent_variation": None,
            "moves_san": [san_move]
        }

        # Agregar al diccionario local
        if parent_ply not in self.variations:
            self.variations[parent_ply] = []
        self.variations[parent_ply].append(new_var)

        # Entrar automáticamente en la variación recién creada
        self.active_variation = new_var
        self.active_var_moves = [
            self.current_moves[parent_ply],  # Posición de partida (ply del padre)
            {"ply": 1, "san": san_move, "fen": data["new_fen"], "turn": data["turn"]}
        ]
        self.active_var_ply = 1

        self.query_one("#board_view", Static).update(render_fen(data["new_fen"]))
        self.refresh_moves_table()
        self.save_variation_to_db(new_var)
        self.app.notify(f"⑂ Bifurcación creada: {san_move}", title="Fork")

    @work(thread=True)
    def save_variation_to_db(self, var_data: dict) -> None:
        """Persiste o actualiza una variación en la base de datos."""
        try:
            if var_data.get("id"):
                resp = httpx.patch(
                    f"{API_CHESS_VARIATIONS}{var_data['id']}/",
                    json={"moves_san": var_data["moves_san"]}, timeout=5.0)
            else:
                resp = httpx.post(API_CHESS_VARIATIONS, json={
                    "room": var_data["room"],
                    "parent_ply": var_data["parent_ply"],
                    "parent_variation": var_data.get("parent_variation"),
                    "moves_san": var_data["moves_san"]
                }, timeout=5.0)
                if resp.status_code == 201:
                    var_data["id"] = resp.json()["id"]
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error guardando variación: {e}", severity="error")

    @work(thread=True)
    def fetch_variations(self) -> None:
        """Carga todas las variaciones de la partida actual."""
        if not self.current_room_id:
            return
        try:
            resp = httpx.get(f"{API_CHESS_ROOMS}{self.current_room_id}/", timeout=5.0)
            if resp.status_code == 200:
                vars_list = resp.json().get("variations", [])
                var_dict = {}
                for v in vars_list:
                    pp = v["parent_ply"]
                    if pp not in var_dict:
                        var_dict[pp] = []
                    var_dict[pp].append(v)
                self.app.call_from_thread(self.update_variations_dict, var_dict)
        except Exception:
            pass

    def update_variations_dict(self, var_dict: dict) -> None:
        self.variations = var_dict
        self.refresh_moves_table()

    def action_show_variations(self) -> None:
        """Muestra las bifurcaciones disponibles en el ply actual."""
        if not self.current_moves:
            return

        ply = self.current_ply
        forks = self.variations.get(ply, [])

        if not forks:
            self.app.notify("No hay bifurcaciones en esta jugada.", severity="warning")
            return

        # Mostrar un selector de variaciones
        fork_labels = [f"{i+1}. {v['moves_san'][0]} ({'..'.join(v['moves_san'][:3])})"
                       for i, v in enumerate(forks)]
        self.app.notify(
            f"Variaciones en ply {ply}: {', '.join(fork_labels)}. "
            f"Usa el input para seleccionar (ej: v1, v2...)", title="⑂ Forks")
        self.enter_variation(forks[0])  # Auto-entra en la primera

    def enter_variation(self, var_data: dict) -> None:
        """Entra en modo variación, reconstruyendo las posiciones FEN."""
        self.active_variation = var_data
        parent_ply = var_data["parent_ply"]

        # Reconstruimos las posiciones de la variación usando python-chess en el cliente
        import chess
        base_fen = self.current_moves[parent_ply]["fen"]
        board = chess.Board(base_fen)

        self.active_var_moves = [
            {"ply": 0, "san": f"(desde ply {parent_ply})", "fen": base_fen,
             "turn": "white" if board.turn == chess.WHITE else "black"}
        ]

        for i, san in enumerate(var_data["moves_san"]):
            try:
                move = board.parse_san(san)
                board.push(move)
                self.active_var_moves.append({
                    "ply": i + 1, "san": san, "fen": board.fen(),
                    "turn": "white" if board.turn == chess.WHITE else "black"
                })
            except Exception:
                break

        self.active_var_ply = min(1, len(self.active_var_moves) - 1)
        if self.active_var_ply > 0:
            self.query_one("#board_view", Static).update(
                render_fen(self.active_var_moves[self.active_var_ply]["fen"]))
        self.refresh_moves_table()
        self.app.notify("Dentro de bifurcación. Presiona 'B' para volver.", title="⑂")

    def action_back_to_mainline(self) -> None:
        """Sale de la variación activa y vuelve a la línea principal."""
        if not self.active_variation:
            self.app.notify("Ya estás en la línea principal.", severity="warning")
            return
        self.active_variation = None
        self.active_var_moves = []
        self.active_var_ply = 0
        self.query_one("#board_view", Static).update(
            render_fen(self.current_moves[self.current_ply]["fen"]))
        self.refresh_moves_table()
        self.app.notify("Volviste a la línea principal.", title="♟")

    def refresh_moves_table(self) -> None:
        table = self.query_one("#moves_table", DataTable)
        table.clear()

        # Decidimos qué lista de movimientos renderizar
        if self.active_variation:
            moves = self.active_var_moves
            prefix = "⑂ "
        else:
            moves = self.current_moves
            prefix = ""

        turn_number = 1
        for i in range(1, len(moves), 2):
            white_san = moves[i]["san"]
            black_san = moves[i+1]["san"] if i + 1 < len(moves) else ""

            # Añadir indicador de fork si la jugada tiene variaciones
            if not self.active_variation:
                if i in self.variations:
                    white_san = f"⑂ {white_san}"
                if (i + 1) in self.variations:
                    black_san = f"⑂ {black_san}"

            table.add_row(str(turn_number), f"{prefix}{white_san}" if turn_number == 1 and self.active_variation else white_san,
                          black_san, key=str(turn_number))
            turn_number += 1

        # Desplaza el cursor automáticamente
        active_ply = self.active_var_ply if self.active_variation else self.current_ply
        if active_ply > 0:
            row = (active_ply - 1) // 2
            col = 1 if active_ply % 2 != 0 else 2
            try:
                table.move_cursor(row=row, column=col)
            except Exception:
                pass

    # --- ORÁCULO DE STOCKFISH ---

    def action_evaluate_pos(self) -> None:
        """Se activa al presionar la E."""
        if not self.current_moves:
            return

        # Extraemos el FEN actual, el inicial, y todo el historial de jugadas (SAN)
        fen = self.current_moves[self.current_ply]["fen"]
        initial_fen = self.current_moves[0]["fen"]
        history = [m["san"] for m in self.current_moves[1:self.current_ply+1]]

        self.query_one("#oracle_panel", Static).update(
            "⏳ [italic text-muted]Oráculo calculando árboles de variantes (contexto completo)...[/]")
        self.process_evaluation(fen, initial_fen, history)

    @work(thread=True)
    def process_evaluation(self, fen: str, initial_fen: str, history: list) -> None:
        try:
            resp = httpx.post(API_CHESS_EVALUATE, json={
                              "fen": fen,
                              "initial_fen": initial_fen,
                              "history": history,
                              "depth": 15}, timeout=15.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.update_oracle_ui, resp.json())
            else:
                self.app.call_from_thread(self.query_one(
                    "#oracle_panel", Static).update, f"Error del Oráculo.")
        except Exception as e:
            self.app.call_from_thread(self.query_one(
                "#oracle_panel", Static).update, f"Fallo de comunicación: {e}")

    def update_oracle_ui(self, data: dict) -> None:
        eval_info = data.get("eval", {})
        best_move = data.get("best_move", "Ninguno")

        panel = self.query_one("#oracle_panel", Static)
        bar = self.query_one("#eval_bar", Static)

        if eval_info.get("type") == "mate":
            mate_in = eval_info.get("value", 0)
            color = "Blancas" if mate_in > 0 else "Negras"
            text = f"[bold red]MATE INMINENTE[/]: {color} en {abs(mate_in)} | Sugerencia: [bold]{best_move}[/]"
            percentage = 100.0 if mate_in > 0 else 0.0
        else:
            cp = eval_info.get("value", 0)
            score = cp / 100.0
            sign = "+" if score > 0 else ""

            text = f"[bold cyan]Análisis (Stockfish):[/] {sign}{score:.2f} | Mejor jugada: [bold]{best_move}[/]"

            # Matemática para la barra térmica: -5 a +5 puntos (500 centipeones) llenan o vacían la barra
            percentage = 50.0 + (score * 10.0)
            percentage = max(0.0, min(100.0, percentage))

        bar.update(render_eval_bar(percentage))
        panel.update(text)
