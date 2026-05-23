import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Static
from textual.containers import Vertical, Grid
from textual import work

from .constants import API_CHESS_ROOMS, API_CHESS_NOTES, API_CHESS_PARSE
from .modals import ImportPGNModal, ChessNoteModal


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

        # Ampliamos a 3 líneas de alto y 7 caracteres de ancho por casilla
        # Esto evita que la terminal aplaste el tablero por las métricas de la fuente.
        line1 = "   "
        line2 = f"[bold #A0A0A0]{rank}[/]  "
        line3 = "   "

        for c_idx, piece in enumerate(squares):
            bg = light_bg if (r_idx + c_idx) % 2 == 0 else dark_bg

            # Línea superior (vacía)
            line1 += f"[{bg}]       [/]"

            # Línea central (con la pieza perfectamente centrada)
            if piece:
                char, color = solid_pieces[piece]
                line2 += f"[{color} {bg}]   {char}   [/]"
            else:
                line2 += f"[{bg}]       [/]"

            # Línea inferior (vacía)
            line3 += f"[{bg}]       [/]"

        out += line1 + "\n" + line2 + "\n" + line3 + "\n"

    # Coordenadas inferiores calculadas geométricamente (6 espacios de separación)
    out += "      [bold #A0A0A0]a      b      c      d      e      f      g      h[/]\n"
    return out


class ChessMainScreen(Screen):
    """Laboratorio Táctico de Ajedrez."""

    # ¡CORRECCIÓN CRÍTICA! Se retira el prefijo "action_" de los atajos
    BINDINGS = [
        ("escape, q", "go_back", "Volver al Launcher"),
        ("a", "add_pgn", "Importar PGN"),
        ("n", "edit_note", "Anotar Jugada"),
    ]

    CSS = """
    #chess_root {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1.5fr 1fr;
        grid-rows: 2fr 1fr;
        padding: 1 2;
        grid-gutter: 1 2;
    }
    
    #board_panel { 
        row-span: 2; 
        border: heavy $success; 
        background: $surface; 
        align: center middle; 
        content-align: center middle;
    }
    
    #board_view {
        text-align: left; /* Mantiene la integridad del bloque 3x7 */
        width: auto;
    }
    
    #moves_panel { border: heavy $warning; background: $surface; height: 100%; }
    #notes_panel { border: heavy $primary; background: $surface; height: 100%; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="chess_root"):
            with Vertical(id="board_panel"):
                # Cargamos la posición inicial al iniciar el panel
                yield Static(render_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"), id="board_view")
            with Vertical(id="moves_panel"):
                yield DataTable(id="moves_table")
            with Vertical(id="notes_panel"):
                yield Markdown("### Apuntes Teóricos\n\nPresiona **A** para importar un PGN.", id="notes_view")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "BUNKER"
        self.sub_title = "Laboratorio de Ajedrez"

        self.current_room_id = None
        self.current_moves = []
        self.current_notes = {}
        self.current_ply = 0

        table = self.query_one("#moves_table", DataTable)
        table.cursor_type = "cell"
        table.zebra_stripes = True
        table.add_columns("Turno", "Blancas", "Negras")

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_add_pgn(self) -> None:
        def handle_pgn(payload: dict | None) -> None:
            if payload and payload.get("pgn"):
                self.app.notify(
                    "Analizando PGN y sincronizando con la BD...", title="Oráculo")
                self.process_pgn(payload)
        self.app.push_screen(ImportPGNModal(), handle_pgn)

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
                    "pgn_data": payload["pgn"]
                }, timeout=5.0)

                if room_resp.status_code == 201:
                    room_data = room_resp.json()
                    self.app.call_from_thread(
                        self.load_game_into_ui, room_data["id"], moves)
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

        self.app.notify("Estancia táctica lista para estudio.",
                        title="Laboratorio")
        table.focus()
        self.fetch_notes()

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        if not self.current_moves:
            return

        coord = event.coordinate
        row_idx = coord.row
        col_idx = coord.column

        ply = (row_idx * 2) + 1 if col_idx <= 1 else (row_idx * 2) + 2

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

        def save_note(text: str | None) -> None:
            if text is not None:
                self.process_save_note(text)
        self.app.push_screen(ChessNoteModal(), save_note)

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
