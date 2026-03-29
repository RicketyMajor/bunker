from django.db import models
from django.utils import timezone
from datetime import timedelta


class Author(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(
        max_length=100, help_text="e.g., Science Fiction, Fantasy, Cyberpunk")

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True, null=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    author = models.ForeignKey(
        'Author', on_delete=models.CASCADE, related_name='books', null=True, blank=True)
    genres = models.ManyToManyField('Genre', related_name='books', blank=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    directory = models.ForeignKey(
        'Directory', on_delete=models.SET_NULL, related_name='books', null=True, blank=True)

    # Formato principal para clasificar
    FORMAT_CHOICES = [
        ('NOVEL', 'Novela'),
        ('MANGA', 'Manga / Cómic'),
        ('COMIC', 'Cómic Occidental'),
        ('ANTHOLOGY', 'Antología / Cuentos'),
        ('ACADEMIC', 'Libro Académico'),
    ]
    format_type = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default='NOVEL')

    details = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)
    is_loaned = models.BooleanField(default=False)
    page_count = models.IntegerField(blank=True, null=True)
    publish_date = models.CharField(max_length=50, blank=True, null=True)
    cover_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title


class Friend(models.Model):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name


def default_due_date():
    """Por defecto, los préstamos duran 30 días."""
    return (timezone.now() + timedelta(days=30)).date()


class Loan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    loan_date = models.DateField(default=timezone.now)
    due_date = models.DateField(default=default_due_date)
    returned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.book.title} -> {self.friend.name}"


class Directory(models.Model):
    """Carpetas maestras para agrupar libros o sagas (El Sistema de Archivos)."""
    name = models.CharField(max_length=100, unique=True)
    color_hex = models.CharField(
        max_length=20, default="cyan", help_text="Color de renderizado en la terminal")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# --- SISTEMA DE VIGILANCIA Y LISTA DE DESEOS ---

class Watcher(models.Model):
    """Palabras clave (autores, series) que el scraper buscará todos los días."""
    keyword = models.CharField(
        max_length=200, unique=True, help_text="Autor, serie o palabra clave a vigilar")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.keyword} (Activo: {self.is_active})"


class WishlistItem(models.Model):
    """Libros/Mangas encontrados por el scraper que te podrían interesar."""
    title = models.CharField(max_length=255)
    author_string = models.CharField(max_length=200, blank=True, null=True)
    publisher = models.CharField(max_length=100, blank=True, null=True)
    price = models.CharField(max_length=50, blank=True, null=True)

    buy_url = models.URLField(max_length=500, blank=True, null=True)
    cover_url = models.URLField(max_length=500, blank=True, null=True)

    date_found = models.DateTimeField(auto_now_add=True)

    is_rejected = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class ReadingSession(models.Model):
    """Libro mayor de páginas leídas por día (Event Sourcing)"""
    date = models.DateField(default=timezone.now)
    pages_read = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.date}: {self.pages_read} páginas"


class AnnualRecord(models.Model):
    """Registro histórico inmutable de libros terminados"""
    title = models.CharField(max_length=255)
    author_name = models.CharField(max_length=200, blank=True, null=True)

    book = models.ForeignKey(Book, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='read_records')

    is_owned = models.BooleanField(default=True)
    date_finished = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.title} - Terminado el {self.date_finished}"


class ScanInbox(models.Model):
    """Bandeja de entrada temporal para ISBNs escaneados desde el móvil (Purgatorio)."""
    isbn = models.CharField(max_length=20, unique=True)
    date_scanned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ISBN en espera: {self.isbn}"
