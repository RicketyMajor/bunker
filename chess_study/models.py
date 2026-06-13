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
    orientation = models.CharField(
        max_length=5, choices=(('white', 'Blancas'), ('black', 'Negras')), default='white')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ChessVariation(models.Model):
    """Bifurcación de la línea principal (o de otra variación) de una partida.
    
    Almacena una lista de jugadas en SAN que divergen de la línea principal
    a partir de `parent_ply`. Permite crear árboles de análisis al estilo
    de chess.com.
    """
    room = models.ForeignKey(
        ChessRoom, on_delete=models.CASCADE, related_name='variations')
    # Ply desde donde nace esta variación (ej: si la bifurcación reemplaza la jugada 4, parent_ply=3)
    parent_ply = models.IntegerField()
    # FK recursiva: si es None, es un fork de la línea principal
    parent_variation = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='sub_variations')
    # Lista ordenada de jugadas SAN: ["d5", "exd5", "Qxd5", ...]
    moves_san = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['parent_ply', 'created_at']

    def __str__(self):
        first = self.moves_san[0] if self.moves_san else "?"
        return f"Variación en ply {self.parent_ply}: {first}... ({self.room.title})"


class ChessNote(models.Model):
    room = models.ForeignKey(
        ChessRoom, on_delete=models.CASCADE, related_name='notes')
    ply_number = models.IntegerField()
    move_san = models.CharField(max_length=20, blank=True)
    text = models.TextField()
    # Enlace opcional a una variación (None = nota en línea principal)
    variation = models.ForeignKey(
        ChessVariation, on_delete=models.CASCADE, null=True, blank=True,
        related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'ply_number', 'variation')
        ordering = ['ply_number']

    def __str__(self):
        room_title = self.room.title if self.room else "Sin sala"
        var_tag = f" [Var {self.variation_id}]" if self.variation else ""
        return f"Nota en {room_title} (Ply {self.ply_number}: {self.move_san}){var_tag}"

