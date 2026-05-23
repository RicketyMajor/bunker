import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Static, Tree
from textual.containers import Vertical, Grid
from textual import work

from .constants import API_CHESS_ROOMS, API_CHESS_NOTES, API_CHESS_PARSE, API_CHESS_DIRS
from .modals import ImportPGNModal, ChessNoteModal, ChessDirModal, ConfirmModal


def render_fen(fen: str) -> str:
    """Dibuja un tablero de alta fidelidad con proporciones geométricas perfectas."""
    solid_pieces = {
        'r': ('♜', '#000000'), 'n': ('♞', '#000000'), 'b': ('♝', '#000000'), 'q': ('♛', '#000000'), 'k': ('♚', '#000000'), 'p': ('♟', '#000000'),
        'R': ('♜', '#FFFFFF'), 'N': ('♞', '#FFFFFF'), 'B': ('♝', '#FFFFFF'), 'Q': ('♛', '#FFFFFF'), 'K': ('♚', '#FFFFFF'), 'P': ('♟', '#FFFFFF')
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
    
    #board_panel { 
        row-span: 2; 
        border: heavy $success; 
        background: $surface; 
        align: center middle; 
        content-align: center middle;
    }
    
    #board_view { text-align: left; width: auto; }
    
    #moves_panel { border: heavy $warning; background: $surface; height: 100%; }
    #notes_panel { border: heavy $primary; background: $surface; height: 100%; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="chess_root"):
            # Nuevo Panel Izquierdo: El Árbol
            with Vertical(id="tree_panel"):
                yield Tree("Archivos Tácticos", id="chess_tree")

            # Panel Central: Tablero
            with Vertical(id="board_panel"):
                yield Static(render_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"), id="board_view")

            # Panel Derecho Superior: Movimientos
            with Vertical(id="moves_panel"):
                yield DataTable(id="moves_table")

            # Panel Derecho Inferior: Notas
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
