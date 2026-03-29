from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


class NeoLibraryApp(App):
    """El nuevo entorno inmersivo TUI de tu biblioteca (Estilo Neovim)."""

    # CSS básico integrado para asegurar que el fondo se vea limpio
    CSS = """
    Screen {
        background: $surface-darken-1;
    }
    """

    # Atajos globales de teclado (Vim-style)
    BINDINGS = [
        ("q", "quit", "Salir de la Biblioteca"),
    ]

    def compose(self) -> ComposeResult:
        """Dibuja los elementos principales de la interfaz. (El DOM de la terminal)."""
        # Una cabecera elegante con la hora en vivo
        yield Header(show_clock=True)

        # Aquí es donde inyectaremos la tabla de libros en la Fase 39

        # Un pie de página que muestra dinámicamente qué teclas puedes presionar
        yield Footer()
