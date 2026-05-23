from django.db import models


class ChessRoom(models.Model):
    title = models.CharField(max_length=255)
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
