from django.apps import AppConfig


class DisqueraConfig(AppConfig):
    # Same split as `books/`: the directory says what it holds, the label stays `disquera`,
    # which is the module's name inside Bunker and what the tables and migrations carry.
    name = 'music'
    label = 'disquera'
