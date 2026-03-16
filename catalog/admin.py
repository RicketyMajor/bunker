from django.contrib import admin
from .models import Author, Genre, Book

# Registramos los modelos para que aparezcan en el panel
admin.site.register(Author)
admin.site.register(Genre)
admin.site.register(Book)
