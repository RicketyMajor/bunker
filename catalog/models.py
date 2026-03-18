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
    FORMAT_CHOICES = [
        ('NOVEL', 'Novel'),
        ('COMIC', 'Comic Book'),
        ('MANGA', 'Manga'),
        ('ANTHOLOGY', 'Anthology'),
    ]

    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
    genres = models.ManyToManyField(Genre)
    format_type = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default='NOVEL')
    is_read = models.BooleanField(default=False)

    publisher = models.CharField(
        max_length=200, null=True, blank=True)  # Editorial

    # --- NUEVOS CAMPOS DE METADATOS ---
    subtitle = models.CharField(max_length=255, null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    publish_date = models.CharField(max_length=50, null=True, blank=True)
    cover_url = models.URLField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    # Sistema de control para Cómics/Mangas
    is_series = models.BooleanField(default=False)
    total_volumes = models.IntegerField(null=True, blank=True)
    owned_volumes = models.CharField(max_length=255, null=True, blank=True)
    anthology_stories = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title


class Friend(models.Model):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name


def default_due_date():
    """Por defecto, los préstamos duran 30 días."""
    return timezone.now() + timedelta(days=30)


class Loan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    loan_date = models.DateField(default=timezone.now)
    due_date = models.DateField(default=default_due_date)
    returned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.book.title} -> {self.friend.name}"


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

    def __str__(self):
        return self.title
