from django.db import models


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
    cast = models.TextField(
        blank=True, help_text="Reparto principal, separado por comas")

    release_year = models.IntegerField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    format_type = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default='BLU-RAY')

    # Usa JSONField para guardar la lista de géneros fácilmente
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
    title = models.CharField(max_length=255)
    director = models.CharField(max_length=255, null=True, blank=True)
    release_year = models.CharField(max_length=10, null=True, blank=True)
    tmdb_id = models.IntegerField(
        null=True, blank=True, help_text="ID oficial para obtener el póster luego")

    date_found = models.DateTimeField(auto_now_add=True)
    # El martillo de borrado (Soft Delete)
    is_rejected = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class MovieInbox(models.Model):
    barcode = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    date_scanned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.barcode
