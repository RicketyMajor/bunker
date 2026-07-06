from django.db import models
from django.utils.timezone import localdate


class MovieDirectory(models.Model):
    name = models.CharField(max_length=100)
    color_hex = models.CharField(max_length=20, default="blue")

    def __str__(self):
        return self.name


class Movie(models.Model):
    FORMAT_CHOICES = [
        ('DVD', 'DVD'),
        ('BLU-RAY', 'Blu-ray'),
        ('4K', '4K UHD'),
        ('VHS', 'VHS'),
        ('DIGITAL', 'Digital')
    ]

    title = models.CharField(max_length=255)
    original_title = models.CharField(max_length=255, blank=True, null=True)
    director = models.CharField(max_length=255, default="Desconocido")
    writers = models.CharField(max_length=255, blank=True, null=True)
    production_company = models.CharField(
        max_length=255, blank=True, null=True)
    cast = models.TextField(
        blank=True, help_text="Reparto principal, separado por comas")

    release_year = models.IntegerField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    format_type = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default='BLU-RAY')

    # Usa JSONField para guardar la lista de géneros
    genres = models.JSONField(default=list, blank=True)
    synopsis = models.TextField(blank=True)
    poster_url = models.URLField(blank=True, null=True)

    is_watched = models.BooleanField(default=False)
    is_loaned = models.BooleanField(default=False)

    friend_name = models.CharField(max_length=255, blank=True, null=True)

    directory = models.ForeignKey(
        MovieDirectory, null=True, blank=True, on_delete=models.SET_NULL, related_name='movies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class MovieWatcher(models.Model):
    """Palabras clave, directores o sagas que el scraper vigilará en TMDB."""
    keyword = models.CharField(
        max_length=255, help_text="Director o Saga (Ej: Denis Villeneuve)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.keyword


class MovieWishlist(models.Model):
    """Lanzamientos o descubrimientos que el scraper inyecta en el sistema."""
    PRIORITY_CHOICES = [
        ('HIGH', 'Alta'),
        ('MED', 'Media'),
        ('LOW', 'Baja')
    ]
    ADDED_BY_CHOICES = [
        ('manual', 'Manual'),
        ('scraper', 'Scraper')
    ]

    title = models.CharField(max_length=255)
    director = models.CharField(max_length=255, null=True, blank=True)
    release_year = models.CharField(max_length=10, null=True, blank=True)
    tmdb_id = models.IntegerField(
        null=True, blank=True, help_text="ID oficial para obtener el póster luego")

    date_found = models.DateTimeField(auto_now_add=True)
    is_rejected = models.BooleanField(default=False)
    
    priority = models.CharField(max_length=4, choices=PRIORITY_CHOICES, default='MED')
    added_by = models.CharField(max_length=10, choices=ADDED_BY_CHOICES, default='scraper')

    def __str__(self):
        return self.title


class MovieInbox(models.Model):
    barcode = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    date_scanned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.barcode


class MovieViewingSession(models.Model):
    """Libro mayor de minutos vistos por día (Event Sourcing)"""
    date = models.DateField(default=localdate)
    minutes_watched = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.date}: {self.minutes_watched} minutos"


class MovieAnnualRecord(models.Model):
    """Registro histórico inmutable de películas vistas"""
    title = models.CharField(max_length=255)
    director = models.CharField(max_length=255, blank=True, null=True)

    movie = models.ForeignKey(Movie, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='watch_records')

    is_owned = models.BooleanField(default=True)
    date_watched = models.DateField(default=localdate)

    def __str__(self):
        return f"{self.title} - Vista el {self.date_watched}"
