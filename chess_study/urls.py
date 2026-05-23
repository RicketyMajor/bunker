from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChessRoomViewSet, ChessNoteViewSet, ChessDirectoryViewSet, parse_pgn

router = DefaultRouter()
router.register(r'rooms', ChessRoomViewSet)
router.register(r'notes', ChessNoteViewSet)
router.register(r'directories', ChessDirectoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('parse-pgn/', parse_pgn, name='parse-pgn'),
]
