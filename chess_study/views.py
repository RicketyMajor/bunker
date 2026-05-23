import io
import chess
import chess.pgn
from stockfish import Stockfish
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChessRoom, ChessNote, ChessDirectory
from .serializers import ChessRoomSerializer, ChessNoteSerializer, ChessDirectorySerializer


class ChessDirectoryViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar el árbol de directorios de ajedrez."""
    queryset = ChessDirectory.objects.all().order_by('name')
    serializer_class = ChessDirectorySerializer


class ChessRoomViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar las Estancias de Ajedrez."""
    queryset = ChessRoom.objects.all().order_by('-created_at')
    serializer_class = ChessRoomSerializer


class ChessNoteViewSet(viewsets.ModelViewSet):
    """Controlador para gestionar los apuntes tácticos."""
    queryset = ChessNote.objects.all().order_by('ply_number')
    serializer_class = ChessNoteSerializer


@api_view(['POST'])
def parse_pgn(request):
    """
    Recibe un texto PGN crudo y lo transforma en una matriz secuencial 
    de movimientos y estados de tablero (FEN).
    """
    pgn_text = request.data.get('pgn')
    if not pgn_text:
        return Response({"error": "No se detectó texto PGN en la transmisión."}, status=status.HTTP_400_BAD_REQUEST)

    # Convertimos el string a un stream para que python-chess pueda leerlo
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
        board.push(move)       # Avanzamos el motor interno un turno

        moves_data.append({
            "ply": node.ply(),
            "san": san,
            "fen": board.fen(),
            "turn": "white" if board.turn == chess.WHITE else "black"
        })

    # Empacamos cabeceras (Evento, Blancas, Negras) y la línea de tiempo FEN
    return Response({
        "headers": dict(game.headers),
        "moves": moves_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def evaluate_position(request):
    """
    Enciende a Stockfish en segundo plano, evalúa el FEN actual 
    y devuelve la ventaja matemática y la mejor jugada sugerida.
    """
    fen = request.data.get('fen')
    depth = request.data.get('depth', 15)  # Profundidad por defecto rápida

    if not fen:
        return Response({"error": "No se proporcionó FEN."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # En contenedores Linux (Debian/Ubuntu), apt-get instala stockfish aquí:
        stockfish = Stockfish(path="/usr/games/stockfish")
        stockfish.set_fen_position(fen)
        stockfish.set_depth(depth)

        eval_info = stockfish.get_evaluation()
        best_move = stockfish.get_best_move()

        return Response({
            # Formato: {"type": "cp", "value": 150} o {"type": "mate", "value": 3}
            "eval": eval_info,
            "best_move": best_move
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
        # Validamos si la jugada existe y es legal en esta posición
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
