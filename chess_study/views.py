import os
import io
import chess
import chess.pgn
from stockfish import Stockfish
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import ChessRoom, ChessNote, ChessDirectory, ChessVariation
from .serializers import ChessRoomSerializer, ChessNoteSerializer, ChessDirectorySerializer, ChessVariationSerializer


class ChessDirectoryViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar el árbol de directorios de ajedrez."""
    queryset = ChessDirectory.objects.all().order_by('name')
    serializer_class = ChessDirectorySerializer


class ChessRoomViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar las Estancias de Ajedrez."""
    queryset = ChessRoom.objects.all().order_by('-created_at')
    serializer_class = ChessRoomSerializer

    @action(detail=True, methods=['patch'])
    def update_mainline(self, request, pk=None):
        room = self.get_object()
        moves_san = request.data.get('moves_san', [])
        
        game = chess.pgn.Game()
        game.headers['Event'] = room.title
        node = game
        board = chess.Board()
        
        try:
            for san in moves_san:
                if san == "Inicial": continue
                move = board.parse_san(san)
                node = node.add_variation(move)
                board.push(move)
                
            room.pgn_data = str(game)
            room.save()
            return Response({"status": "success"})
        except ValueError as e:
            return Response({"error": f"Movimiento inválido: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def finish_analysis(self, request, pk=None):
        room = self.get_object()
        if room.is_analyzed:
            return Response({"error": "Esta partida ya fue analizada y su experiencia reclamada."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from posada.models import Adventurer, GuildProfile, DeepWorkSession
            from posada.engine.legacy import check_level_up
        except ImportError:
            return Response({"error": "El motor de Posada no está disponible."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        adv = Adventurer.objects.first()
        guild = GuildProfile.objects.first()
        if not adv or not guild:
            return Response({"error": "No hay un Aventurero o Gremio activo."}, status=status.HTTP_400_BAD_REQUEST)

        # Cálculo de Recompensas
        base_xp = 300
        if adv.adv_class == 'WIZ':
            base_xp += int(base_xp * 0.3)  # Bono 30%

        # Otorgar Prestigio
        guild.prestige_level += 2
        guild.save()

        # Otorgar Experiencia
        adv.experience += base_xp
        adv.save()
        
        log_messages = [f"Ganaste {base_xp} XP por tu riguroso estudio táctico."]
        check_level_up(adv, log_messages)
        
        # Registrar en Crónicas
        from django.utils import timezone
        session = DeepWorkSession.objects.create(
            duration_minutes=30,
            completed=True,
            category="Chess Study"
        )
        session.adventurers_involved.add(adv)
        
        events = [
            f"El aventurero {adv.name} se encerró en el Laboratorio de Ajedrez.",
            f"Analizó rigurosamente la partida: '{room.title}'.",
            f"El gremio gana 2 puntos de prestigio."
        ]
        events.extend(log_messages)
        
        session.event_log = events
        session.save()

        # Marcar como analizada
        room.is_analyzed = True
        room.save()

        return Response({
            "message": "Análisis completado",
            "xp_earned": base_xp,
            "prestige_earned": 2,
            "logs": events
        })


class ChessNoteViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar los apuntes tácticos."""
    queryset = ChessNote.objects.all().order_by('ply_number')
    serializer_class = ChessNoteSerializer


class ChessVariationViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar las bifurcaciones de variantes."""
    queryset = ChessVariation.objects.all().order_by('parent_ply')
    serializer_class = ChessVariationSerializer


@api_view(['POST'])
def parse_pgn(request):
    """
    Recibe un texto PGN crudo y lo transforma en una matriz secuencial 
    de movimientos y estados de tablero (FEN).
    """
    pgn_text = request.data.get('pgn')
    if not pgn_text or not pgn_text.strip():
        # PGN vacío: devolver solo la posición inicial
        return Response({
            "headers": {},
            "moves": [{
                "ply": 0,
                "san": "Posición Inicial",
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "turn": "white"
            }]
        }, status=status.HTTP_200_OK)

    # Convierte el string a un stream para que python-chess pueda leerlo
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)

    if game is None:
        return Response({"error": "El formato PGN es inválido o está corrupto."}, status=status.HTTP_400_BAD_REQUEST)

    moves_data = []
    board = game.board()

    # 1. Fotografía de la Posición Inicial
    moves_data.append({
        "ply": 0,
        "san": "Posición Inicial",
        "fen": board.fen(),
        "turn": "white"
    })

    # 2. Despliegue de la Línea Principal (Mainline)
    for node in game.mainline():
        move = node.move
        san = board.san(move)  # Ej: Nf3, e4, O-O
        board.push(move)       # Avanza el motor interno un turno

        moves_data.append({
            "ply": node.ply(),
            "san": san,
            "fen": board.fen(),
            "turn": "white" if board.turn == chess.WHITE else "black"
        })

    # Empaca cabeceras (Evento, Blancas, Negras) y la línea de tiempo FEN
    return Response({
        "headers": dict(game.headers),
        "moves": moves_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def evaluate_position(request):
    """
    Enciende a Stockfish en segundo plano, evalúa el contexto histórico completo 
    y devuelve la ventaja matemática y la mejor jugada sugerida (en SAN).
    """
    fen = request.data.get('fen')
    initial_fen = request.data.get('initial_fen')
    history = request.data.get('history', [])
    depth = request.data.get('depth', 15)  # Profundidad por defecto rápida

    if not fen:
        return Response({"error": "No se proporcionó FEN."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # turn_perspective=False garantiza que la evaluación siempre sea respecto a las blancas.
        stockfish_path = os.environ.get("STOCKFISH_PATH", "/usr/games/stockfish")
        stockfish = Stockfish(path=stockfish_path, turn_perspective=False)
        board = chess.Board(fen)

        if initial_fen and history:
            # Recrea la partida desde el inicio para darle a Stockfish contexto completo
            # (vital para la regla de los 50 movimientos y la triple repetición)
            temp_board = chess.Board(initial_fen)
            uci_moves = []
            for san_move in history:
                if san_move == "Inicial":
                    continue
                move = temp_board.parse_san(san_move)
                uci_moves.append(move.uci())
                temp_board.push(move)

            stockfish.set_fen_position(initial_fen)
            if uci_moves:
                stockfish.make_moves_from_current_position(uci_moves)
        else:
            stockfish.set_fen_position(fen)

        stockfish.set_depth(depth)

        eval_info = stockfish.get_evaluation()
        best_move_uci = stockfish.get_best_move()

        # Convertir la jugada UCI a SAN para que sea legible (Ej: "e2e4" -> "e4")
        try:
            best_move_san = board.san(board.parse_uci(best_move_uci)) if best_move_uci else "Ninguno"
        except Exception:
            best_move_san = best_move_uci

        return Response({
            # Formato: {"type": "cp", "value": 150} o {"type": "mate", "value": 3}
            "eval": eval_info,
            "best_move": best_move_san
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Falla en el motor Stockfish: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def validate_move(request):
    """
    Recibe una jugada en texto (Ej: 'e4' o 'Nf3') y un FEN. 
    Verifica si es legal usando la matemática de python-chess.
    """
    fen = request.data.get('fen')
    san_move = request.data.get('san')

    if not fen or not san_move:
        return Response({"error": "Faltan datos (FEN o SAN)."}, status=status.HTTP_400_BAD_REQUEST)

    board = chess.Board(fen)
    try:
        # Valida si la jugada existe y es legal en esta posición
        move = board.parse_san(san_move)
        board.push(move)

        return Response({
            "valid": True,
            "new_fen": board.fen(),
            "san": san_move,
            "turn": "white" if board.turn == chess.WHITE else "black"
        }, status=status.HTTP_200_OK)
    except ValueError:
        # Si parse_san falla, es un movimiento ilegal o mal escrito
        return Response({"valid": False, "error": "Movimiento ilegal o error de sintaxis."}, status=status.HTTP_400_BAD_REQUEST)
