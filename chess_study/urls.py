from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChessRoomViewSet, ChessNoteViewSet, ChessDirectoryViewSet,
    ChessVariationViewSet,
    parse_pgn, evaluate_position, validate_move,
    get_daily_puzzle, solve_daily_puzzle
)

router = DefaultRouter()
router.register(r'rooms', ChessRoomViewSet)
router.register(r'notes', ChessNoteViewSet)
router.register(r'directories', ChessDirectoryViewSet)
router.register(r'variations', ChessVariationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('parse-pgn/', parse_pgn, name='parse-pgn'),
    path('evaluate/', evaluate_position, name='evaluate_position'),
    path('validate-move/', validate_move, name='validate_move'),
    path('puzzles/daily/', get_daily_puzzle, name='get_daily_puzzle'),
    path('puzzles/solve/', solve_daily_puzzle, name='solve_daily_puzzle'),
]
