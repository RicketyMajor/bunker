from textual.app import App
from .screens import BunkerLauncherScreen


class BunkerApp(App):
    """El núcleo central de la terminal Bunker."""
    theme = "gruvbox"

    BINDINGS = [
        ("q", "app.quit", "Salir del Bunker"),
    ]

    CSS = """
    Screen { background: $surface-darken-1; }
    """

    def on_mount(self) -> None:
        self.push_screen(BunkerLauncherScreen())
