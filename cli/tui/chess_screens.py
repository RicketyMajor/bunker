import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Static, Tree, ProgressBar, Input
from textual.containers import Vertical, Grid, Horizontal
from textual import work
from .constants import API_CHESS_ROOMS, API_CHESS_NOTES, API_CHESS_PARSE, API_CHESS_DIRS, API_CHESS_EVALUATE, API_CHESS_VALIDATE
from .modals import ImportPGNModal, ChessNoteModal, ChessDirModal, ConfirmModal


def render_fen(fen: str) -> str:
    """Dibuja un tablero de alta fidelidad con proporciones geométricas perfectas."""
    # Piezas blancas ajustadas a un tono beige/hueso (#E8D2A6) para máximo contraste
    solid_pieces = {
        'r': ('♜', '#000000'), 'n': ('♞', '#000000'), 'b': ('♝', '#000000'), 'q': ('♛', '#000000'), 'k': ('♚', '#000000'), 'p': ('♟', '#000000'),
        'R': ('♜', '#E8D2A6'), 'N': ('♞', '#E8D2A6'), 'B': ('♝', '#E8D2A6'), 'Q': ('♛', '#E8D2A6'), 'K': ('♚', '#E8D2A6'), 'P': ('♟', '#E8D2A6')
    }
    light_bg = "on #EBECD0"
    dark_bg = "on #779556"

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
                line2 += f"[{color} {bg}]   {char}   [/]"
            else:
                line2 += f"[{bg}]       [/]"
            line3 += f"[{bg}]       [/]"

        out += line1 + "\n" + line2 + "\n" + line3 + "\n"

    out += "      [bold #A0A0A0]a      b      c      d      e      f      g      h[/]\n"
    return out


class ChessMainScreen(Screen):
    """Laboratorio Táctico de Ajedrez."""

    BINDINGS = [
        ("escape, q", "go_back", "Volver al Launcher"),
        ("d", "add_dir", "Crear Carpeta"),
        ("a", "add_pgn", "Importar PGN"),
        ("n", "edit_note", "Anotar Jugada"),
        ("delete, x", "delete_note", "Eliminar Nota"),
        ("backspace", "delete_node", "Destruir Nodo (Árbol)"),
        ("e", "evaluate_pos", "Oráculo (IA)"),
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
        height: 90%;
        margin-right: 2;
        border: solid $warning;
        /* La barra térmica irá aquí */
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
                    # Barra de Evaluación Vertical
                    yield ProgressBar(total=100, show_eta=False, show_percentage=False, id="eval_bar")
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

        table = self.query_one("#moves_table", DataTable)
        table.clear()

        turn_number = 1
        for i in range(1, len(moves), 2):
            white_move = moves[i]["san"]
            black_move = moves[i+1]["san"] if i+1 < len(moves) else ""
            table.add_row(str(turn_number), white_move,
                          black_move, key=str(turn_number))
            turn_number += 1

        table.focus()
        self.fetch_notes()
        if self.current_moves:
            self.query_one("#board_view", Static).update(
                render_fen(self.current_moves[0]["fen"]))

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        if not self.current_moves:
            return

        coord = event.coordinate
        ply = (coord.row * 2) + 1 if coord.column <= 1 else (coord.row * 2) + 2

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
                notes_dict = {n["ply_number"]: {"id": n["id"],
                                                "text": n["text"]} for n in notes_list}
                self.app.call_from_thread(self.update_notes_dict, notes_dict)
        except Exception:
            pass

    def update_notes_dict(self, notes_dict: dict) -> None:
        self.current_notes = notes_dict
        self.refresh_notes_panel()

    def refresh_notes_panel(self) -> None:
        md = self.query_one("#notes_view", Markdown)
        if not self.current_moves:
            return

        note_data = self.current_notes.get(self.current_ply, {})
        note_text = note_data.get("text", "*Sin apuntes para esta posición.*")
        current_san = self.current_moves[self.current_ply].get(
            "san", "Inicial")

        content = f"### Análisis de Jugada: `{current_san}`\n\n{note_text}"
        md.update(content)

    def action_edit_note(self) -> None:
        if not self.current_room_id or self.current_ply == 0:
            self.app.notify(
                "Selecciona una jugada blanca o negra en la tabla.", severity="warning")
            return

        existing_text = self.current_notes.get(
            self.current_ply, {}).get("text", "")

        def save_note(text: str | None) -> None:
            if text is not None:
                self.process_save_note(text)
        self.app.push_screen(ChessNoteModal(existing_text), save_note)

    @work(thread=True)
    def process_save_note(self, text: str) -> None:
        try:
            existing_note = self.current_notes.get(self.current_ply)

            if existing_note and "id" in existing_note:
                resp = httpx.patch(
                    f"{API_CHESS_NOTES}{existing_note['id']}/", json={"text": text}, timeout=5.0)
            else:
                payload = {
                    "room": self.current_room_id,
                    "ply_number": self.current_ply,
                    "move_san": self.current_moves[self.current_ply].get("san", ""),
                    "text": text
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
        # Si el tablero está vacío, inicia desde la posición cero
        current_fen = self.current_moves[self.current_ply][
            "fen"] if self.current_moves else "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

        try:
            resp = httpx.post(API_CHESS_VALIDATE, json={
                              "fen": current_fen, "san": san_move}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(self.apply_manual_move, resp.json())
            else:
                err = resp.json().get("error", "Movimiento inválido")
                self.app.call_from_thread(
                    self.app.notify, f"Ilegal: {err}", severity="warning")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def apply_manual_move(self, data: dict) -> None:
        new_ply = self.current_ply + 1

        # Si se está escribiendo en medio de una partida, corta el futuro
        if new_ply < len(self.current_moves):
            self.current_moves = self.current_moves[:new_ply]

        move_entry = {
            "ply": new_ply,
            "san": data["san"],
            "fen": data["new_fen"],
            "turn": data["turn"]
        }

        # Si es la primera jugada del estudio, inserta también la inicial
        if not self.current_moves:
            self.current_moves.append(
                {"ply": 0, "san": "Inicial", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", "turn": "white"})

        self.current_moves.append(move_entry)
        self.current_ply = new_ply

        self.query_one("#board_view", Static).update(
            render_fen(data["new_fen"]))
        self.refresh_moves_table()

    def refresh_moves_table(self) -> None:
        table = self.query_one("#moves_table", DataTable)
        table.clear()
        turn_number = 1
        for i in range(1, len(self.current_moves), 2):
            white_move = self.current_moves[i]["san"]
            black_move = self.current_moves[i+1]["san"] if i + \
                1 < len(self.current_moves) else ""
            table.add_row(str(turn_number), white_move,
                          black_move, key=str(turn_number))
            turn_number += 1

        # Despla el cursor automáticamente a la jugada recién hecha
        if self.current_ply > 0:
            row = (self.current_ply - 1) // 2
            col = 1 if self.current_ply % 2 != 0 else 2
            table.move_cursor(row=row, column=col)

    # --- ORÁCULO DE STOCKFISH ---

    def action_evaluate_pos(self) -> None:
        """Se activa al presionar la E."""
        if not self.current_moves:
            return

        fen = self.current_moves[self.current_ply]["fen"]
        self.query_one("#oracle_panel", Static).update(
            "⏳ [italic text-muted]Oráculo calculando árboles de variantes...[/]")
        self.process_evaluation(fen)

    @work(thread=True)
    def process_evaluation(self, fen: str) -> None:
        try:
            resp = httpx.post(API_CHESS_EVALUATE, json={
                              "fen": fen, "depth": 15}, timeout=15.0)
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
        bar = self.query_one("#eval_bar", ProgressBar)

        if eval_info.get("type") == "mate":
            mate_in = eval_info.get("value", 0)
            color = "Blancas" if mate_in > 0 else "Negras"
            text = f"[bold red]MATE INMINENTE[/]: {color} en {abs(mate_in)} | Sugerencia: [bold]{best_move}[/]"
            bar.progress = 100 if mate_in > 0 else 0
        else:
            cp = eval_info.get("value", 0)
            score = cp / 100.0
            sign = "+" if score > 0 else ""

            text = f"[bold cyan]Análisis (Stockfish):[/] {sign}{score:.2f} | Mejor jugada: [bold]{best_move}[/]"

            # Matemática para la barra térmica: -5 a +5 puntos (500 centipeones) llenan o vacían la barra
            percentage = 50 + (score * 10)
            bar.progress = max(0, min(100, percentage))

        panel.update(text)
