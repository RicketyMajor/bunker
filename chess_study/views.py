import io
import chess
import chess.pgn
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChessRoom, ChessNote
from .serializers import ChessRoomSerializer, ChessNoteSerializer


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
