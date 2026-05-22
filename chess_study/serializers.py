from rest_framework import serializers
from .models import ChessRoom, ChessNote


class ChessNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChessNote
        fields = '__all__'


class ChessRoomSerializer(serializers.ModelSerializer):
    # Anidamos las notas para que al descargar una partida, vengan todos sus apuntes
    notes = ChessNoteSerializer(many=True, read_only=True)

    class Meta:
        model = ChessRoom
        fields = '__all__'
