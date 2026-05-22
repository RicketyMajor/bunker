from django.db import models


class ChessRoom(models.Model):
    """Una 'Estancia' de estudio para una partida o variante teórica."""
    title = models.CharField(
        max_length=255, help_text="Ej: Kasparov vs Topalov 1999 o Defensa Siciliana")
    pgn_data = models.TextField(
        blank=True, help_text="El texto PGN crudo importado de Chess.com o Lichess")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ChessNote(models.Model):
    """Una nota vinculada a un 'ply' (medio movimiento) específico dentro de una Estancia."""
    room = models.ForeignKey(
        ChessRoom, on_delete=models.CASCADE, related_name='notes')

    # ply_number: 1 = blanca mueve, 2 = negra mueve, 3 = blanca mueve 2...
    ply_number = models.IntegerField(
        help_text="El índice del medio movimiento")

    move_san = models.CharField(
        max_length=20, blank=True, help_text="Notación algebraica (Ej: Nxf7+)")
    text = models.TextField(
        help_text="Tus apuntes tácticos o teóricos para esta posición")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Una nota maestra por cada posición
        unique_together = ('room', 'ply_number')
        ordering = ['ply_number']

    def __str__(self):
        return f"Nota en {self.room.title} (Ply {self.ply_number}: {self.move_san})"
