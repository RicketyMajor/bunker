import httpx
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, DataTable, Static, Tree, Input
from textual.containers import Vertical, Grid, Horizontal
from textual import work
from textual.binding import Binding
from .constants import API_CHESS_ROOMS, API_CHESS_NOTES, API_CHESS_PARSE, API_CHESS_DIRS, API_CHESS_EVALUATE, API_CHESS_VALIDATE, API_CHESS_VARIATIONS, API_CHESS_FINISH_ANALYSIS
from .modals import ImportPGNModal, ChessNoteModal, ChessDirModal, ConfirmModal, CreateGameModal, CreateVariationModal, SelectVariationModal


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


def render_fen(fen: str, orientation: str = "white") -> str:
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
    if orientation == "black":
        rows = rows[::-1]

    out = "\n"

    for r_idx, row in enumerate(rows):
        rank = 8 - r_idx if orientation == "white" else r_idx + 1
        squares = []
        for char in row:
            if char.isdigit():
                squares.extend([None] * int(char))
            else:
                squares.append(char)
                
        if orientation == "black":
            squares = squares[::-1]

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

    letters = "a      b      c      d      e      f      g      h" if orientation == "white" else "h      g      f      e      d      c      b      a"
    out += f"      [bold #A0A0A0]{letters}[/]\n"
    return out


class ChessMainScreen(Screen):
    """Laboratorio Táctico de Ajedrez."""

    BINDINGS = [
        Binding("escape, q", "go_back", "Volver", show=False),
        Binding("c", "create_game", "Nueva"),
        Binding("d", "add_dir", "Carpeta"),
        Binding("a", "add_pgn", "PGN"),
        Binding("f", "fork_variation", "Variante"),
        Binding("n", "edit_note", "Nota"),
        Binding("z", "undo_move", "Deshacer"),
        Binding("e", "evaluate_pos", "Oráculo"),
        Binding("w", "finish_study", "Completar"),
        Binding("v", "show_variations", "Ver Vars"),
        Binding("b", "back_to_mainline", "Volver"),
        Binding("p", "solve_puzzle", "Puzzle Diario"),
        Binding("delete, x", "delete_note", "Borrar Nota", show=False),
        Binding("backspace", "delete_node", "Borrar Árbol", show=False),
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
    #repertoire_tree { display: none; }
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
                yield Tree("Repertorio Táctico", id="repertoire_tree")
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

    def _update_board_view(self, fen: str) -> None:
        orientation = getattr(self, "current_orientation", "white")
        self.query_one("#board_view", Static).update(render_fen(fen, orientation))

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
        self.raw_rooms = rooms
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
                "pgn_data": "",
                "orientation": payload.get("orientation", "white"),
                "room_type": payload.get("room_type", "game")
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
                
                # Para evitar el bug de orientación, insertamos la sala recién creada
                if not hasattr(self, "raw_rooms"):
                    self.raw_rooms = []
                self.raw_rooms.append(room_data)

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
        
        # Obtener orientación de la sala y el tipo de sala
        room_data = next((r for r in getattr(self, "raw_rooms", []) if r["id"] == room_id), {})
        self.current_orientation = room_data.get("orientation", "white")
        self.current_room_type = room_data.get("room_type", "game")

        self.current_moves = moves
        self.current_notes = {}
        self.current_ply = 0

        # Reset variaciones
        self.variations = {}
        self.active_variation = None
        self.active_var_moves = []
        self.active_var_ply = 0
        self.variation_stack = []  # Pila para navegar sub-variaciones

        self.refresh_moves_table()

        table = self.query_one("#moves_table", DataTable)
        tree = self.query_one("#repertoire_tree", Tree)
        
        if self.current_room_type == "repertoire":
            table.display = False
            tree.display = True
            tree.focus()
            self.build_repertoire_tree()
        else:
            table.display = True
            tree.display = False
            table.focus()
            
        self.fetch_notes()
        self.fetch_variations()

        if len(self.current_moves) > 1:
            # Empezar en la primera jugada real, no en la posición inicial
            self.current_ply = 1
            self._update_board_view(self.current_moves[1]["fen"])
        elif self.current_moves:
            self._update_board_view(self.current_moves[0]["fen"])

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        if not self.current_moves:
            return

        coord = event.coordinate

        if self.active_variation:
            start_ply = self.active_variation["parent_ply"]
            moves = self.active_var_moves
        else:
            start_ply = 0
            moves = self.current_moves

        # Calcular el turno real basado en la fila de la tabla
        turn_num = ((start_ply + 2) // 2) + coord.row
        
        # Columna 0 = "Turno", 1 = "Blancas", 2 = "Negras"
        col = max(1, coord.column)  # Tratar col 0 como col 1
        
        # Calcular ply global absoluto
        global_ply = (turn_num * 2) - 1 if col <= 1 else (turn_num * 2)

        # Convertir a ply local dentro de la lista actual (moves)
        local_ply = global_ply - start_ply
        
        # Limitar al tamaño del arreglo para evitar IndexError (ej. clics en celdas vacías)
        local_ply = max(0, min(local_ply, len(moves) - 1))

        if self.active_variation:
            self.active_var_ply = local_ply
        else:
            self.current_ply = local_ply

        fen = moves[local_ply]["fen"]
        self._update_board_view(fen)
        self.refresh_notes_panel()

    def build_repertoire_tree(self) -> None:
        """Construye el árbol de decisiones leyendo la línea principal y variaciones."""
        tree = self.query_one("#repertoire_tree", Tree)
        tree.clear()
        
        if not self.current_moves:
            tree.root.set_label("Vacío")
            return
            
        tree.root.set_label("⭐ Inicio")
        tree.root.data = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", "is_mainline": True, "local_ply": 0}
        
        import chess
        
        def add_variations(parent_node, parent_ply, base_fen, variation_id=None):
            # Buscar variaciones que nacen de este ply exacto
            forks = [v for forks_list in self.variations.values() for v in forks_list if v.get("parent_variation") == variation_id and v["parent_ply"] == parent_ply]
            
            for var in forks:
                board = chess.Board(base_fen)
                current_node = parent_node
                
                # Para evitar duplicados visuales en la raíz si es un fork directo de la línea principal
                var_label = f"⑂ Variación {var['id']}"
                var_root = current_node.add(f"[bold cyan]{var_label}[/]", data={"fen": base_fen, "is_mainline": False, "variation": var, "local_ply": 0})
                
                curr = var_root
                for i, san in enumerate(var["moves_san"]):
                    try:
                        board.push_san(san)
                        turn_prefix = f"{(parent_ply + i) // 2 + 1}." if board.turn == chess.BLACK else f"{(parent_ply + i) // 2 + 1}..."
                        label = f"{turn_prefix} {san}"
                        
                        curr = curr.add(label, data={"fen": board.fen(), "is_mainline": False, "variation": var, "local_ply": i + 1})
                        
                        # Recursividad: buscar sub-variaciones que nazcan en ESTE ply de ESTA variación
                        add_variations(curr, i + 1, board.fen(), var["id"])
                    except:
                        break

        # Construir Línea Principal
        curr_node = tree.root
        for i, move in enumerate(self.current_moves[1:], 1):
            turn_prefix = f"{(i+1) // 2}." if move["turn"] == "black" else f"{(i+1) // 2}..."
            label = f"[bold green]{turn_prefix} {move['san']}[/]"
            curr_node = curr_node.add(label, data={"fen": move["fen"], "is_mainline": True, "local_ply": i})
            
            # Buscar variaciones de nivel 1 que nazcan en este ply de la línea principal
            add_variations(curr_node, i, move["fen"], None)

        tree.root.expand_all()

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Al navegar por el Repertorio Táctico, actualiza el tablero y activa la variación correspondiente."""
        if event.control.id != "repertoire_tree":
            return
            
        data = event.node.data
        if not data:
            return
            
        fen = data.get("fen")
        if fen:
            self._update_board_view(fen)
            
        # Sincronizar estado interno para que funcionen notas, undo, y forks
        if data.get("is_mainline"):
            self.active_variation = None
            self.active_var_moves = []
            self.current_ply = data.get("local_ply", 0)
        elif "variation" in data:
            self.active_variation = data["variation"]
            self.active_var_ply = data.get("local_ply", 0)
            
            # Reconstruir active_var_moves si no está cargada
            if not self.active_var_moves or len(self.active_var_moves) - 1 < self.active_var_ply:
                # Esto es una optimización, idealmente usaríamos el código de enter_variation
                # Por ahora solo llamamos a enter_variation en background si queremos extenderlo
                pass
                
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

        breadcrumb = self._get_breadcrumb()

        if self.active_variation and self.active_var_moves:
            current_san = self.active_var_moves[self.active_var_ply].get("san", "?")
            header = f"### ⑂ Variación — Jugada: `{current_san}`"
        else:
            current_san = self.current_moves[self.current_ply].get("san", "Inicial")
            header = f"### Análisis de Jugada: `{current_san}`"

        content = f"{breadcrumb}\n\n{header}\n\n{note_text}"
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
            self._update_board_view(data["new_fen"])
            self.refresh_moves_table()
            if hasattr(self, "current_room_type") and self.current_room_type == "repertoire":
                self.build_repertoire_tree()
            self.save_variation_to_db(self.active_variation)
            return

        # --- Línea principal: agregar jugada al final ---
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
        self._update_board_view(data["new_fen"])
        self.refresh_moves_table()
        if hasattr(self, "current_room_type") and self.current_room_type == "repertoire":
            self.build_repertoire_tree()
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
                self._update_board_view(self.active_var_moves[-1]["fen"])
                self.refresh_moves_table()
                if hasattr(self, "current_room_type") and self.current_room_type == "repertoire":
                    self.build_repertoire_tree()
                self.save_variation_to_db(self.active_variation)
                self.app.notify("Jugada deshecha (Variación).", severity="information")
            else:
                self.app.notify("Solo puedes deshacer la última jugada de la rama activa.", severity="warning")
        else:
            if self.current_ply == len(self.current_moves) - 1 and self.current_ply > 0:
                self.current_moves.pop()
                self.current_ply -= 1
                self._update_board_view(self.current_moves[-1]["fen"])
                self.refresh_moves_table()
                if hasattr(self, "current_room_type") and self.current_room_type == "repertoire":
                    self.build_repertoire_tree()
                self.save_mainline_to_db()
                self.app.notify("Jugada deshecha (Principal).", severity="information")
            else:
                self.app.notify("Solo puedes deshacer la última jugada de la línea.", severity="warning")

    def action_fork_variation(self) -> None:
        """Acción explícita para crear una bifurcación (tecla F)."""
        if not self.current_moves and not self.active_variation:
            self.app.notify("Primero carga o crea una partida.", severity="warning")
            return

        if self.active_variation:
            ply = self.active_var_ply
            if ply == 0:
                self.app.notify("Selecciona una jugada para bifurcar.", severity="warning")
                return
            current_san = self.active_var_moves[ply].get("san", "?")
        else:
            ply = self.current_ply
            if ply == 0:
                self.app.notify("Selecciona una jugada para bifurcar.", severity="warning")
                return
            current_san = self.current_moves[ply].get("san", "?")

        def handle_fork(san_move: str | None) -> None:
            if san_move:
                self.process_fork(san_move)

        self.app.push_screen(CreateVariationModal(current_san, ply), handle_fork)

    @work(thread=True)
    def process_fork(self, san_move: str) -> None:
        """Valida la jugada alternativa y crea la variación."""
        if self.active_variation and self.active_var_moves:
            # Fork dentro de una variación existente
            parent_ply_in_var = self.active_var_ply
            base_fen = self.active_var_moves[parent_ply_in_var]["fen"]
        else:
            base_fen = self.current_moves[self.current_ply]["fen"]

        try:
            resp = httpx.post(API_CHESS_VALIDATE, json={
                "fen": base_fen, "san": san_move}, timeout=5.0)
            if resp.status_code == 200:
                self.app.call_from_thread(
                    self.apply_fork, resp.json(), san_move)
            else:
                err = resp.json().get("error", "Movimiento inválido")
                self.app.call_from_thread(
                    self.app.notify, f"Ilegal: {err}", severity="warning")
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error: {e}", severity="error")

    def apply_fork(self, data: dict, san_move: str) -> None:
        """Crea la bifurcación y entra en ella automáticamente."""
        if self.active_variation:
            # Sub-variación: fork dentro de una variación
            parent_ply = self.active_var_ply
            parent_var_id = self.active_variation.get("id")

            new_var = {
                "id": None,
                "room": self.current_room_id,
                "parent_ply": parent_ply,
                "parent_variation": parent_var_id,
                "moves_san": [san_move]
            }

            # Guardar estado actual en la pila antes de entrar
            self.variation_stack.append({
                "variation": self.active_variation,
                "var_moves": self.active_var_moves,
                "var_ply": self.active_var_ply
            })
        else:
            # Fork desde la línea principal
            parent_ply = self.current_ply

            new_var = {
                "id": None,
                "room": self.current_room_id,
                "parent_ply": parent_ply,
                "parent_variation": None,
                "moves_san": [san_move]
            }

            # Agregar al diccionario local de variaciones
            if parent_ply not in self.variations:
                self.variations[parent_ply] = []
            self.variations[parent_ply].append(new_var)

        # Entrar en la nueva variación
        import chess
        base_fen = data["new_fen"]
        # Usamos el FEN del padre para el ply 0
        if self.active_variation:
            parent_fen = self.active_var_moves[self.active_var_ply]["fen"]
        else:
            parent_fen = self.current_moves[self.current_ply]["fen"]

        self.active_variation = new_var
        self.active_var_moves = [
            {"ply": 0, "san": f"(fork)", "fen": parent_fen, "turn": data["turn"]},
            {"ply": 1, "san": san_move, "fen": data["new_fen"], "turn": data["turn"]}
        ]
        self.active_var_ply = 1

        self._update_board_view(data["new_fen"])
        self.refresh_moves_table()
        self.refresh_notes_panel()
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
        if hasattr(self, "current_room_type") and self.current_room_type == "repertoire":
            self.build_repertoire_tree()

    def action_show_variations(self) -> None:
        """Muestra las bifurcaciones disponibles en el ply actual con un selector."""
        if not self.current_moves:
            return

        ply = self.active_var_ply if self.active_variation else self.current_ply
        forks = self.variations.get(ply, [])

        if not forks:
            self.app.notify("No hay bifurcaciones en esta jugada.", severity="warning")
            return

        if len(forks) == 1:
            # Solo una variación, entrar directamente
            self.enter_variation(forks[0])
            return

        def handle_selection(idx: int | None) -> None:
            if idx is not None and 0 <= idx < len(forks):
                self.enter_variation(forks[idx])

        self.app.push_screen(SelectVariationModal(forks), handle_selection)

    def action_solve_puzzle(self) -> None:
        """Abre la interfaz del Puzzle Diario."""
        self.app.push_screen(PuzzleScreen())

    def enter_variation(self, var_data: dict) -> None:
        """Entra en modo variación, reconstruyendo las posiciones FEN."""
        # Guardar el contexto actual en la pila
        if self.active_variation:
            self.variation_stack.append({
                "variation": self.active_variation,
                "var_moves": self.active_var_moves,
                "var_ply": self.active_var_ply
            })

        self.active_variation = var_data
        parent_ply = var_data["parent_ply"]

        # Determinar el FEN base desde donde nace la variación
        import chess
        if self.variation_stack and self.variation_stack[-1]["var_moves"]:
            # Sub-variación: el FEN base está en la variación padre
            parent_moves = self.variation_stack[-1]["var_moves"]
            if parent_ply < len(parent_moves):
                base_fen = parent_moves[parent_ply]["fen"]
            else:
                base_fen = parent_moves[-1]["fen"]
        else:
            # Variación de nivel 1: FEN base desde la línea principal
            base_fen = self.current_moves[parent_ply]["fen"]

        board = chess.Board(base_fen)
        self.active_var_moves = [
            {"ply": 0, "san": "(fork)", "fen": base_fen,
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
            self._update_board_view(self.active_var_moves[self.active_var_ply]["fen"])
        self.refresh_moves_table()
        self.refresh_notes_panel()

        depth = len(self.variation_stack) + 1
        self.app.notify(
            f"Dentro de variación (nivel {depth}). Presiona 'B' para volver.", title="⑂")

    def action_back_to_mainline(self) -> None:
        """Sale de la variación activa. Si hay pila, retrocede un nivel."""
        if not self.active_variation:
            self.app.notify("Ya estás en la línea principal.", severity="warning")
            return

        if self.variation_stack:
            # Subir un nivel en la pila
            prev = self.variation_stack.pop()
            self.active_variation = prev["variation"]
            self.active_var_moves = prev["var_moves"]
            self.active_var_ply = prev["var_ply"]
            self._update_board_view(self.active_var_moves[self.active_var_ply]["fen"])
            depth = len(self.variation_stack) + 1
            self.app.notify(f"Volviste al nivel {depth} de variación.", title="⑂")
        else:
            # Volver a la línea principal
            self.active_variation = None
            self.active_var_moves = []
            self.active_var_ply = 0
            self._update_board_view(self.current_moves[self.current_ply]["fen"])
            self.app.notify("Volviste a la línea principal.", title="♟")

        self.refresh_moves_table()
        self.refresh_notes_panel()

    def _get_variation_depth(self) -> int:
        """Devuelve la profundidad actual en la pila de variaciones."""
        if not self.active_variation:
            return 0
        return len(self.variation_stack) + 1

    def _get_breadcrumb(self) -> str:
        """Genera un breadcrumb de navegación para saber dónde estamos."""
        parts = ["♟ Principal"]
        depth_colors = ["cyan", "magenta", "yellow", "green", "red"]

        for i, ctx in enumerate(self.variation_stack):
            var = ctx["variation"]
            first_san = var["moves_san"][0] if var.get("moves_san") else "?"
            color = depth_colors[i % len(depth_colors)]
            symbol = "⑂" * (i + 1)
            parts.append(f"[{color}]{symbol} Var({first_san})[/]")

        if self.active_variation:
            first_san = self.active_variation["moves_san"][0] if self.active_variation.get("moves_san") else "?"
            depth = len(self.variation_stack)
            color = depth_colors[depth % len(depth_colors)]
            symbol = "⑂" * (depth + 1)
            parts.append(f"[{color}]{symbol} Var({first_san})[/]")

        return " > ".join(parts)

    def refresh_moves_table(self) -> None:
        table = self.query_one("#moves_table", DataTable)
        table.clear()

        depth_colors = ["cyan", "magenta", "yellow", "green", "red"]

        # Decidimos qué lista de movimientos renderizar
        if self.active_variation:
            moves = self.active_var_moves
            depth = self._get_variation_depth()
            color = depth_colors[(depth - 1) % len(depth_colors)]
            prefix_symbol = "⑂" * depth
        else:
            moves = self.current_moves
            depth = 0
            color = ""
            prefix_symbol = ""

        if self.active_variation:
            parent_ply = self.active_variation["parent_ply"]
            start_ply = parent_ply
        else:
            start_ply = 0

        rows_data = {}
        for i in range(1, len(moves)):
            global_ply = start_ply + i
            turn_num = (global_ply + 1) // 2
            
            if turn_num not in rows_data:
                rows_data[turn_num] = {"white": "", "black": ""}
            
            san = moves[i]["san"]

            # Añadir indicador de fork con conteo
            if not self.active_variation:
                if i in self.variations:
                    count = len(self.variations[i])
                    san = f"[cyan]⑂{count}[/] {san}"

            # Prefijo de profundidad en la primera fila de la variación
            if i == 1 and self.active_variation:
                san = f"[{color}]{prefix_symbol}[/] {san}"

            if global_ply % 2 != 0:
                rows_data[turn_num]["white"] = san
            else:
                rows_data[turn_num]["black"] = san

        turn_list = sorted(rows_data.keys())
        for t_num in turn_list:
            table.add_row(str(t_num), rows_data[t_num]["white"], rows_data[t_num]["black"], key=str(t_num))

        # Desplaza el cursor automáticamente
        active_ply = self.active_var_ply if self.active_variation else self.current_ply
        if active_ply > 0:
            global_active_ply = start_ply + active_ply
            active_turn = (global_active_ply + 1) // 2
            if active_turn in turn_list:
                row_idx = turn_list.index(active_turn)
                col = 1 if global_active_ply % 2 != 0 else 2
                try:
                    table.move_cursor(row=row_idx, column=col)
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

    @work(thread=True)
    def action_finish_study(self) -> None:
        if not self.current_room_id:
            self.app.call_from_thread(
                self.app.notify, "Carga una partida primero para poder completarla.", severity="warning"
            )
            return

        try:
            url = API_CHESS_FINISH_ANALYSIS.format(self.current_room_id)
            resp = httpx.post(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                xp = data.get("xp_earned")
                prestige = data.get("prestige_earned")
                
                # Format the success message
                msg = f"¡Estudio Táctico Finalizado!\n+{xp} XP otorgada.\n+{prestige} Prestigio para el Gremio."
                self.app.call_from_thread(
                    self.app.notify, msg, title="Sinergia Posada", severity="success", timeout=6
                )
            elif resp.status_code == 400:
                err = resp.json().get("error", "No se pudo reclamar.")
                self.app.call_from_thread(
                    self.app.notify, f"Aviso: {err}", severity="warning"
                )
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error del sistema: {resp.text}", severity="error"
                )
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Falla de red: {e}", severity="error"
            )

class PuzzleScreen(Screen):
    """Pantalla para resolver el Puzzle Diario de Lichess."""
    
    BINDINGS = [
        Binding("escape, q", "go_back", "Volver")
    ]
    
    CSS = """
    #puzzle_root {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 2fr 1fr;
        padding: 1 2;
        grid-gutter: 1 2;
    }
    
    #board_container_puzzle {
        border: heavy $success;
        background: $surface;
        align: center middle;
        content-align: center middle;
        layout: horizontal;
    }
    
    #info_panel_puzzle {
        border: heavy $warning;
        background: $surface;
        padding: 1 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Grid(id="puzzle_root"):
            with Horizontal(id="board_container_puzzle"):
                yield Static(render_eval_bar(50.0), id="eval_bar_puzzle")
                yield Static(render_fen("8/8/8/8/8/8/8/8"), id="board_view_puzzle")
                
            with Vertical(id="info_panel_puzzle"):
                yield Markdown("## 🧩 Puzzle Diario\nCargando conexión con Lichess...", id="puzzle_info")
                yield Input(placeholder="Ingresa tu jugada (Ej: e4, d4f4)...", id="puzzle_input")
        yield Footer()
        
    def on_mount(self) -> None:
        self.puzzle_data = None
        self.puzzle_solved = False
        self.solution_moves = []
        self.current_fen = ""
        self.current_orientation = "white"
        self.app.call_from_thread(self.fetch_daily_puzzle)
        
    @work(thread=True)
    def fetch_daily_puzzle(self):
        try:
            from .constants import API_CHESS_DAILY_PUZZLE
            resp = httpx.get(API_CHESS_DAILY_PUZZLE, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(self.load_puzzle, data)
            else:
                self.app.call_from_thread(self.show_error, "No se pudo obtener el puzzle.")
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))
            
    def show_error(self, msg: str):
        self.query_one("#puzzle_info", Markdown).update(f"## ❌ Error\n{msg}")
        
    def load_puzzle(self, data: dict):
        if data.get("solved"):
            self.query_one("#puzzle_info", Markdown).update("## 🏆 Puzzle Resuelto\nYa resolviste el puzzle diario hoy. ¡Vuelve mañana!")
            self.query_one("#puzzle_input", Input).display = False
            
            # Still show the board
            p = data.get("puzzle", {})
            self.current_fen = p.get("fen", "")
            if self.current_fen:
                import chess
                board = chess.Board(self.current_fen)
                self.current_orientation = "white" if board.turn == chess.WHITE else "black"
                self.query_one("#board_view_puzzle", Static).update(render_fen(self.current_fen, self.current_orientation))
            return
            
        p = data.get("puzzle", {})
        self.puzzle_data = p
        self.solution_moves = p.get("solution", [])
        self.current_fen = p.get("fen", "")
        
        import chess
        board = chess.Board(self.current_fen)
        self.current_orientation = "white" if board.turn == chess.WHITE else "black"
        
        self.query_one("#board_view_puzzle", Static).update(render_fen(self.current_fen, self.current_orientation))
        
        info = f"## 🧩 Puzzle Diario\n**Rating:** {p.get('rating')}\n**Juegan:** {'Blancas' if self.current_orientation == 'white' else 'Negras'}\n\nEscribe tu jugada para resolverlo."
        self.query_one("#puzzle_info", Markdown).update(info)
        self.query_one("#puzzle_input", Input).focus()
        
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.puzzle_solved or not self.puzzle_data or event.control.id != "puzzle_input":
            return
            
        move_str = event.value.strip()
        event.control.value = ""
        
        if not self.solution_moves:
            return
            
        correct_uci = self.solution_moves[0]
        import chess
        board = chess.Board(self.current_fen)
        
        try:
            try:
                move = board.parse_san(move_str)
            except ValueError:
                move = board.parse_uci(move_str)
                
            if move.uci() == correct_uci:
                board.push(move)
                self.current_fen = board.fen()
                self.solution_moves.pop(0)
                
                if not self.solution_moves:
                    self.puzzle_solved = True
                    self.query_one("#board_view_puzzle", Static).update(render_fen(self.current_fen, self.current_orientation))
                    self.query_one("#puzzle_info", Markdown).update("## 🎉 ¡CORRECTO!\nEnviando recompensa a la Posada...")
                    self.app.call_from_thread(self.submit_solved)
                    return
                    
                opponent_uci = self.solution_moves.pop(0)
                opp_move = chess.Move.from_uci(opponent_uci)
                board.push(opp_move)
                self.current_fen = board.fen()
                
                self.query_one("#board_view_puzzle", Static).update(render_fen(self.current_fen, self.current_orientation))
            else:
                self.app.notify("Jugada incorrecta. Intenta de nuevo.", severity="warning")
        except ValueError:
            self.app.notify("Jugada ilegal o no reconocida.", severity="error")
            
    @work(thread=True)
    def submit_solved(self):
        try:
            from .constants import API_CHESS_SOLVE_PUZZLE
            resp = httpx.post(API_CHESS_SOLVE_PUZZLE, json={"puzzle_id": self.puzzle_data["id"], "rating": self.puzzle_data["rating"]}, timeout=5.0)
            if resp.status_code == 200:
                msg = resp.json().get("message", "Puzzle Resuelto!")
                self.app.call_from_thread(self.update_solved_ui, f"## 🏆 ¡PUZZLE SUPERADO!\n{msg}")
            else:
                self.app.call_from_thread(self.show_error, "No se pudo registrar la victoria.")
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))
            
    def update_solved_ui(self, msg: str):
        self.query_one("#puzzle_info", Markdown).update(msg)
        self.query_one("#puzzle_input", Input).display = False
        
    def action_go_back(self):
        self.app.pop_screen()
