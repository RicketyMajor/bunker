"""The four methods the three collection screens genuinely share.

Measured, not assumed. Every method of `LibraryMainScreen`, `MovieMainScreen` and
`MusicMainScreen` was extracted by AST and compared pairwise:

    1.000  action_toggle_sidebar   identical byte for byte in all three
    0.987  action_focus_search     differs only in #books_table / #movies_table / #music_table
    0.975  action_switch_tab       differs only in #main_tabs / #movie_tabs / #music_tabs
    0.939  action_delete_habit     widget ids plus the sentence shown to the user
    ------------------------------------------------------------------ cut
    0.904  populate_inbox          reads item['isbn'] vs item['barcode']  <- domain, not an id
    0.830  action_sync_scraper
    ...    33 more, all below 0.70

`populate_inbox` stays copied three times on purpose: `ScanInbox` names its column `isbn`
(`catalog/models.py:157`) while `MovieInbox` and `MusicInbox` use `barcode`. Parameterising a
five-line method by table id, payload key and default is three knobs for five lines, and it
would hide a real schema difference behind a config value.

The other 33 diverged below 0.7, and this project's record says that is exactly where live bugs
hide. They are not touched.

`BINDINGS` deliberately do NOT live here: Textual merges them across the MRO, and the three
screens bind different keys (movies `M`, music `a`, books `ctrl+t`).

Gated by `tests/test_tui_arranca.py`, which mounts all three screens and asserts each of the
four actions resolves to this class.
"""
from textual.screen import Screen
from textual.widgets import DataTable, Input, TabbedContent, Tree

from cli.tui.modals import ConfirmModal


class ColeccionScreen(Screen):
    """Base de las tres pantallas de coleccion. Cada subclase fija sus cuatro constantes."""

    # Las subclases DEBEN sobrescribir las cuatro. Se dejan vacias en vez de con un valor
    # plausible: un id por defecto que casi funciona falla al pulsar una tecla, no al montar,
    # y un fallo al pulsar una tecla no lo ve ninguna compuerta de este proyecto.
    TABLA_PRINCIPAL: str = ""
    CONTENEDOR_TABS: str = ""
    TABLA_ANUAL: str = ""
    MSG_REVERTIR: str = ""

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Tree)
        sidebar.toggle_class("-visible")
        if sidebar.has_class("-visible"):
            sidebar.focus()

    def action_focus_search(self) -> None:
        search_bar = self.query_one("#search_bar", Input)
        if search_bar.has_class("-visible"):
            search_bar.remove_class("-visible")
            search_bar.value = ""
            self.query_one(self.TABLA_PRINCIPAL, DataTable).focus()
        else:
            search_bar.add_class("-visible")
            search_bar.focus()

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(self.CONTENEDOR_TABS, TabbedContent).active = tab_id

    def action_delete_habit(self) -> None:
        # Las tres constantes de id fallan solas si una subclase las olvida: `query_one("")`
        # lanza `NoMatches`. `MSG_REVERTIR` NO — `"".format(title=…)` funciona, y el usuario
        # veria un `ConfirmModal` en blanco pidiendole que confirme un borrado sin decirle de
        # que. Es el unico de los cuatro que falla en silencio, asi que se le pregunta aqui.
        if not self.MSG_REVERTIR:
            raise NotImplementedError(
                f"{type(self).__name__} no define MSG_REVERTIR: el dialogo saldria vacio")

        if self.query_one(self.CONTENEDOR_TABS, TabbedContent).active != "tab_tracker":
            return

        table = self.query_one(self.TABLA_ANUAL, DataTable)
        try:
            # Obtiene la ID y el titulo de la fila seleccionada
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key.value
            title = table.get_row(row_key)[1]

            def handle_confirm(confirm: bool) -> None:
                if confirm:
                    self.process_delete_habit(row_key)

            self.app.push_screen(ConfirmModal(
                self.MSG_REVERTIR.format(title=title)), handle_confirm)
        except Exception:
            self.app.notify(
                "Selecciona un registro en la tabla primero.", severity="warning")
