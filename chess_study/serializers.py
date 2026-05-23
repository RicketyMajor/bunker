from rest_framework import serializers
from .models import ChessRoom, ChessNote, ChessDirectory


class ChessDirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChessDirectory
        fields = '__all__'


class ChessNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChessNote
        fields = '__all__'


class ChessRoomSerializer(serializers.ModelSerializer):
    notes = ChessNoteSerializer(many=True, read_only=True)

    class Meta:
        model = ChessRoom
        fields = '__all__'
