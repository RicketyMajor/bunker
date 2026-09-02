from textual.app import App
from .screens import BunkerLauncherScreen


class BunkerApp(App):
    """El núcleo central de la terminal Bunker."""
    theme = "gruvbox"

    # `ctrl+g` AND NOT `ctrl+h`, WHICH IS WHAT THE BACKLOG PROPOSED — measured, not a preference:
    # most terminals send 0x08 when ctrl+h is pressed, and `textual/_ansi_sequences.py` translates
    # it to `Keys.Backspace` (checked on Textual 8.2.1: `\x08` -> backspace). A `ctrl+h` binding
    # would NEVER fire, and if it did it would swallow deletion in every `Input` in the TUI.
    # `ctrl+i`, `ctrl+m` and `ctrl+j` have the same problem (tab, enter, newline); `ctrl+g` and
    # `ctrl+o` arrive as themselves. `ctrl+b` is already "Explorador" on the three collection
    # screens, and `ctrl+t` is taken.
    BINDINGS = [
        ("q", "app.quit", "Salir del Bunker"),
        # No alcanza a un `ModalScreen`: Textual corta la cadena de enlaces en el primer modal.
        # Medido, y a proposito — ver `action_al_launcher`.
        ("ctrl+g", "al_launcher", "Centro de mando"),
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

    def action_al_launcher(self) -> None:
        """Back to the command centre from any SCREEN. NOT from a modal, and that is Textual's.

        ⚠ THE FIRST VERSION OF THIS DOCSTRING SAID "modals included" AND IT WAS FALSE.
        `Screen._modal_binding_chain` truncates the chain at the first `is_modal` node, so
        App-level `BINDINGS` are unreachable while any `ModalScreen` is on top. Measured on the
        running app (Textual 8.2.1), Launcher -> MovieMainScreen -> WatcherModal, pressing
        `ctrl+g`: the top screen stays `WatcherModal` and the stack keeps its 5 entries. Found by
        `/code-review` 2026-09-02; `test_ctrl_g_vuelve_al_launcher` only stacked NON-modal screens,
        so the claim was untested. *A docstring is not covered by a check that never exercises it.*

        The behaviour is left as Textual designs it, not worked around: a modal is a dialog with a
        pending answer, and escaping it to the launcher would abandon a half-finished action. Press
        Escape first. `test_ctrl_g_no_atraviesa_un_modal` pins it so nobody "fixes" it blind.

        THE STACK IS ASKED, screens are not counted: `pop_screen` on a stack that no longer has a
        Launcher underneath would leave the app on the base screen, blank and with no keys. The
        guard above makes that impossible — with no Launcher this does nothing — which is why the
        loop cannot empty the stack.
        """
        if not any(isinstance(p, BunkerLauncherScreen) for p in self.screen_stack):
            return
        while not isinstance(self.screen, BunkerLauncherScreen):
            self.pop_screen()
