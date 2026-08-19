from textual.app import App
from .screens import BunkerLauncherScreen


class BunkerApp(App):
    """El núcleo central de la terminal Bunker."""
    theme = "gruvbox"

    BINDINGS = [
        ("q", "app.quit", "Salir del Bunker"),
    ]

    # ESTILOS GLOBALES: Afectan a toda la app y a TODAS las ventanas emergentes
    CSS = """
    Screen { background: $surface-darken-1; }
    
    /* ---- ESTILOS MAESTROS PARA MODALES ---- */
    ModalScreen { 
        align: center middle; 
        background: $background 50%; 
    }
    
    #full_edit_dialog { width: 80; height: 90%; padding: 1 2; border: heavy $warning; background: $surface; } 
    
    #isbn_dialog, #lend_dialog, #dir_dialog, #watcher_dialog, #pages_dialog, #move_dir_dialog, #add_menu_dialog, #finish_dialog {
        width: 50; 
        height: auto; 
        padding: 1 2; 
        border: heavy $accent; 
        background: $surface; 
    }

    .modal_title { text-style: bold; margin-bottom: 1; text-align: center; width: 100%; }
    .edit_label { text-style: bold; margin-top: 1; color: $text-muted; }
    
    /* Obliga a la botonera a tener su espacio reservado */
    .form_buttons { height: 3; width: 100%; margin-top: 2; align: center middle; }

    #lend_dialog { border: heavy $success; }
    #sync_dialog { width: 80%; height: 80%; padding: 1 2; border: heavy $success; background: $surface; }
    #sync_log { height: 1fr; border: solid $primary; background: #0c0c0c; }
    #add_menu_dialog { width: 40; height: auto; padding: 1 2; border: heavy $accent; background: $surface; }
    #add_menu_dialog Button { width: 100%; margin-bottom: 1; }
    #scanner_dialog { width: 50; height: 35; padding: 1 2; border: heavy $success; background: $surface; }
    #scanner_qr { height: 1fr; background: #000000; color: #ffffff; text-align: center; } 
    #briefing_dialog { width: 64; height: auto; padding: 1 2; border: heavy $success; background: $surface; }
    #review_box { width: 72; height: auto; padding: 1 2; border: heavy $warning; background: $surface; margin: 2 4; }
    #review_box Label { margin-bottom: 1; }
    .review_sub { color: $text-muted; text-align: center; width: 100%; }
    #btn_cerrar_review { width: 100%; margin-top: 1; }
    #briefing_dialog Label { margin-bottom: 1; }
    .briefing_conclusion { color: $warning; }
    #watchers_list_dialog { width: 80; height: 25; padding: 1 2; border: heavy $accent; background: $surface; }
    #watchers_scroll { height: 1fr; border: solid $primary; padding: 1; margin-bottom: 1; }
    """

    def on_mount(self) -> None:
        self.push_screen(BunkerLauncherScreen())
