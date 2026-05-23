from django.db import models


class ChessDirectory(models.Model):
    name = models.CharField(max_length=100)
    # Relación recursiva: un directorio puede pertenecer a otro directorio
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True, related_name='subdirectories')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ChessRoom(models.Model):
    title = models.CharField(max_length=255)
    # Enlazamos la partida a un directorio (puede ser null si está en la raíz)
    directory = models.ForeignKey(
        ChessDirectory, on_delete=models.SET_NULL, null=True, blank=True, related_name='rooms')
    pgn_data = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ChessNote(models.Model):
    room = models.ForeignKey(
        ChessRoom, on_delete=models.CASCADE, related_name='notes')
    ply_number = models.IntegerField()
    move_san = models.CharField(max_length=20, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'ply_number')
        ordering = ['ply_number']

    def __str__(self):
        room_title = self.room.title if self.room else "Sin sala"
        return f"Nota en {room_title} (Ply {self.ply_number}: {self.move_san})"
