from django.db import models
from django.utils.timezone import localdate


class AlbumDirectory(models.Model):
    name = models.CharField(max_length=100)
    color_hex = models.CharField(max_length=20, default="magenta")

    def __str__(self):
        return self.name


class Album(models.Model):
    FORMAT_CHOICES = [
        ('VINYL', 'Vinilo'),
        ('CD', 'CD'),
        ('CASSETTE', 'Cassette'),
        ('DIGITAL', 'Digital / FLAC')
    ]

    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, default="Desconocido")
    label = models.CharField(max_length=255, blank=True,
                             null=True, help_text="Sello discográfico")

    release_year = models.IntegerField(null=True, blank=True)
    track_count = models.IntegerField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duración total en minutos")
    tracklist = models.JSONField(default=list, blank=True, help_text="Lista de pistas (título, duración)")
    format_type = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default='VINYL')

    genres = models.JSONField(default=list, blank=True)
    cover_url = models.URLField(blank=True, null=True)

    is_listened = models.BooleanField(default=False)
    is_loaned = models.BooleanField(default=False)
    friend_name = models.CharField(max_length=255, blank=True, null=True)

    personal_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, help_text="1.0 a 10.0")
    review_notes = models.TextField(blank=True, null=True)

    directory = models.ForeignKey(
        AlbumDirectory, null=True, blank=True, on_delete=models.SET_NULL, related_name='albums')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.artist}"


class MusicWatcher(models.Model):
    """Bandas o géneros que el scraper vigilará."""
    keyword = models.CharField(
        max_length=255, help_text="Artista o Banda (Ej: Pink Floyd)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.keyword


class MusicWishlist(models.Model):
    """Discos que el scraper encuentra en tiendas."""
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, null=True, blank=True)
    release_year = models.CharField(max_length=10, null=True, blank=True)
    discogs_id = models.IntegerField(null=True, blank=True)

    date_found = models.DateTimeField(auto_now_add=True)
    is_rejected = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class MusicInbox(models.Model):
    """Bandeja de entrada del escáner móvil de códigos de barras EAN/UPC."""
    barcode = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    date_scanned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.barcode


class MusicAnnualRecord(models.Model):
    """Registro histórico de sesiones de escucha profundas."""
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, blank=True, null=True)
    album = models.ForeignKey(Album, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='listen_records')

    is_owned = models.BooleanField(default=True)
    date_listened = models.DateField(default=localdate)

    def __str__(self):
        return f"{self.title} - Escuchado el {self.date_listened}"

class ListeningEntry(models.Model):
    """Diario de escucha (Event Sourcing)"""
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name='listening_entries')
    date = models.DateField(default=localdate)
    minutes_listened = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.date}: {self.minutes_listened} minutos"
