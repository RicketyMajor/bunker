from django.apps import AppConfig


class CatalogConfig(AppConfig):
    # The directory is `books/` so the three collections read alike next to `movies/` and
    # `music/`. The label stays `catalog`: it is what names the database tables
    # (`catalog_book`), the 18 migrations, `BACKUP_APPS` and every `"model": "catalog.book"`
    # row inside bunker_backup.json. Renaming it would be a data migration, not a rename.
    name = 'books'
    label = 'catalog'
