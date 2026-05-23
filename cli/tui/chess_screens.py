# cli/tui/chess_screens.py

import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Label, Static
from textual.containers import Vertical, Grid
from textual.binding import Binding
from textual import work

from .constants import API_CHESS_ROOMS, API_CHESS_NOTES, API_CHESS_PARSE
from .modals import ImportPGNModal, ChessNoteModal


def render_fen(fen: str) -> str:
    """Convierte un string FEN en un tablero Unicode coloreado."""
    pieces = {
        'r': '[red]♜[/]', 'n': '[red]♞[/]', 'b': '[red]♝[/]', 'q': '[red]♛[/]', 'k': '[red]♚[/]', 'p': '[red]♟[/]',
        'R': '[white]♜[/]', 'N': '[white]♞[/]', 'B': '[white]♝[/]', 'Q': '[white]♛[/]', 'K': '[white]♚[/]', 'P': '[white]♟[/]'
    }

    rows = fen.split()[0].split('/')
    board_str = "   [dim]a b c d e f g h[/dim]\n"
    board_str += "  [dim]┌─────────────────┐[/dim]\n"

    for i, row in enumerate(rows):
        rank = 8 - i
        line = f"[dim]{rank} │[/dim]"
        for char in row:
            if char.isdigit():
                line += " [dim]·[/dim]" * int(char)
            else:
                line += " " + pieces[char]
        line += f" [dim]│ {rank}[/dim]"
        board_str += line + "\n"

    board_str += "  [dim]└─────────────────┘[/dim]\n"
    board_str += "   [dim]a b c d e f g h[/dim]"

    return board_str


class ChessMainScreen(Screen):
    """Laboratorio Táctico de Ajedrez."""

    BINDINGS = [
        ("escape, q", "go_back", "Volver al Launcher"),
        ("a", "action_add_pgn", "Importar PGN"),
        ("n", "action_edit_note", "Anotar Jugada"),
    ]

    CSS = """
    #chess_root {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: 2fr 1fr;
        padding: 1 2;
        grid-gutter: 1 2;
    }
    
    #board_panel { row-span: 2; border: heavy $success; background: $surface; align: center middle; }
    #moves_panel { border: heavy $warning; background: $surface; height: 100%; }
    #notes_panel { border: heavy $primary; background: $surface; height: 100%; padding: 0 1; }
    
    #board_view { text-align: center; content-align: center middle; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="chess_root"):
            with Vertical(id="board_panel"):
                yield Static("Inicializando motor táctico...", id="board_view")
            with Vertical(id="moves_panel"):
                yield DataTable(id="moves_table")
            with Vertical(id="notes_panel"):
                yield Markdown("### Apuntes Teóricos\n\nPresiona **A** para importar un PGN.", id="notes_view")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "BUNKER"
        self.sub_title = "Laboratorio de Ajedrez"

        # Estado interno de la partida activa
        self.current_room_id = None
        self.current_moves = []
        self.current_notes = {}  # Mapeo ply -> {"id": x, "text": "..."}
        self.current_ply = 0

        table = self.query_one("#moves_table", DataTable)
        table.cursor_type = "cell"  # Cursor por celda para máxima precisión al navegar
        table.zebra_stripes = True
        table.add_columns("Turno", "Blancas", "Negras")

        self.update_board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")

    def update_board(self, fen: str) -> None:
        self.query_one("#board_view", Static).update(render_fen(fen))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    # --- IMPORTACIÓN Y PARSEO ---
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
                        self.app.notify, "Error guardando la estancia.", severity="error")
            else:
                self.app.call_from_thread(
                    self.app.notify, "PGN corrupto o inválido.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error de red: {e}", severity="error")

    def load_game_into_ui(self, room_id: int, moves: list) -> None:
        self.current_room_id = room_id
        self.current_moves = moves
        self.current_notes = {}
        self.current_ply = 0

        table = self.query_one("#moves_table", DataTable)
        table.clear()

        # moves[0] es pos inicial, moves[1] es mov blancas 1
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

    # --- REACTIVIDAD DEL TECLADO ---
    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Cambia el tablero mágicamente al moverte por las celdas."""
        if not self.current_moves:
            return

        coord = event.coordinate
        row_idx = coord.row
        col_idx = coord.column

        # Calcular el 'ply' exacto basado en la celda (col 1=blancas, col 2=negras)
        # Si está en la col 0 (el número de turno) asumimos que mira el movimiento blanco
        ply = (row_idx * 2) + 1 if col_idx <= 1 else (row_idx * 2) + 2

        # Evitar OutOfIndex si nos paramos en la columna negra de una partida que acabó en turno blanco
        if ply < len(self.current_moves):
            self.current_ply = ply
        else:
            self.current_ply = len(self.current_moves) - 1

        fen = self.current_moves[self.current_ply]["fen"]
        self.update_board(fen)
        self.refresh_notes_panel()

    # --- ANOTACIONES ---
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
            self.app.call_from_thread(
                self.app.notify, "Error fetching notes.", severity="error")

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
                # Update (PATCH)
                resp = httpx.patch(
                    f"{API_CHESS_NOTES}{existing_note['id']}/", json={"text": text}, timeout=5.0)
            else:
                # Create (POST)
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
                self.fetch_notes()  # Recarga para obtener los IDs
            else:
                self.app.call_from_thread(
                    self.app.notify, "Error guardando la nota.", severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")
