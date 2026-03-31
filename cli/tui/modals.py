import asyncio
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Checkbox, RichLog
from textual.containers import Vertical, Horizontal, VerticalScroll
from pathlib import Path


class IsbnModal(ModalScreen[str]):
    """Ventana flotante para ingresar un ISBN nuevo."""

    def compose(self) -> ComposeResult:
        with Vertical(id="isbn_dialog"):
            yield Label("📚 Añadir Nuevo Ejemplar", classes="modal_title")
            yield Label("Ingresa el código ISBN:")
            yield Input(placeholder="Ej: 9788414106222", id="isbn_input")
            with Horizontal(classes="form_buttons"):
                yield Button("Añadir", variant="success", id="btn_add")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            val = self.query_one("#isbn_input", Input).value
            self.dismiss(val)
        else:
            self.dismiss(None)


class FullEditModal(ModalScreen[dict]):
    """Ventana flotante con Scroll para editar toda la ficha."""

    def __init__(self, book: dict, **kwargs):
        super().__init__(**kwargs)
        self.book = book

    def compose(self) -> ComposeResult:
        with Vertical(id="full_edit_dialog"):
            yield Label(f"✏️ Editando: {self.book.get('title')}", classes="modal_title")
            with VerticalScroll():
                yield Label("Título de la obra:", classes="edit_label")
                yield Input(value=self.book.get('title', ''), id="inp_title")

                yield Label("Subtítulo (Opcional):", classes="edit_label")
                yield Input(value=self.book.get('subtitle', ''), id="inp_sub")

                yield Label("Autor Principal:", classes="edit_label")
                yield Input(value=self.book.get('author_name', ''), id="inp_author")

                yield Label("Formato (NOVEL, MANGA, COMIC, ANTHOLOGY, ACADEMIC):", classes="edit_label")
                yield Input(value=self.book.get('format_type', ''), id="inp_format")

                yield Label("Editorial:", classes="edit_label")
                yield Input(value=self.book.get('publisher', ''), id="inp_publisher")

                yield Label("Géneros (separados por coma):", classes="edit_label")
                generos_str = ", ".join(self.book.get(
                    'genre_list', [])) if self.book.get('genre_list') else ""
                yield Input(value=generos_str, id="inp_genres")

                yield Label("Número total de páginas:", classes="edit_label")
                yield Input(value=str(self.book.get('page_count', '')), id="inp_pages")

                # Checkbox al final
                yield Label("")  # Espaciador
                yield Checkbox("✔ Libro Completado/Leído", value=self.book.get('is_read', False), id="chk_read")

            with Horizontal(classes="form_buttons"):
                yield Button("Guardar Cambios", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            pages_val = self.query_one("#inp_pages", Input).value
            payload = {
                "title": self.query_one("#inp_title", Input).value,
                "subtitle": self.query_one("#inp_sub", Input).value,
                "author_input": self.query_one("#inp_author", Input).value,
                # Asegura mayúsculas
                "format_type": self.query_one("#inp_format", Input).value.upper(),
                "publisher": self.query_one("#inp_publisher", Input).value,
                "genre_input": self.query_one("#inp_genres", Input).value,
                "is_read": self.query_one("#chk_read", Checkbox).value,
            }
            if pages_val.isdigit():
                payload["page_count"] = int(pages_val)
            self.dismiss(payload)
        else:
            self.dismiss(None)


class LendModal(ModalScreen[str]):
    """Pequeño diálogo para preguntar el nombre del amigo."""

    def compose(self) -> ComposeResult:
        with Vertical(id="lend_dialog"):
            yield Label("🤝 Prestar Ejemplar", classes="modal_title")
            yield Input(placeholder="Nombre de tu amigo...", id="inp_friend")
            with Horizontal(classes="form_buttons"):
                yield Button("Prestar", variant="success", id="btn_lend")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lend":
            self.dismiss(self.query_one("#inp_friend", Input).value)
        else:
            self.dismiss(None)


class DirModal(ModalScreen[dict]):
    """Pequeño diálogo para crear un Directorio."""

    def compose(self) -> ComposeResult:
        with Vertical(id="dir_dialog"):
            yield Label("📁 Nuevo Universo/Directorio", classes="modal_title")
            yield Input(placeholder="Nombre (Ej: DC Comics)", id="inp_dirname")
            yield Input(placeholder="Color (red, cyan, green...)", value="cyan", id="inp_dircolor")
            with Horizontal(classes="form_buttons"):
                yield Button("Crear", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self.dismiss({
                "name": self.query_one("#inp_dirname", Input).value,
                "color_hex": self.query_one("#inp_dircolor", Input).value
            })
        else:
            self.dismiss(None)


class SyncConsoleModal(ModalScreen[None]):
    """La Terminal de Matrix: Ejecuta el Scraper Dockerizado en vivo."""

    def compose(self) -> ComposeResult:
        with Vertical(id="sync_dialog"):
            yield Label("👾 Matrix Scraper Network", classes="modal_title")
            # RichLog es un widget especializado en recibir texto de terminal
            yield RichLog(id="sync_log", highlight=True, markup=True)
            yield Button("Cerrar Conexión", variant="error", id="btn_cancel")

    async def on_mount(self) -> None:
        log = self.query_one("#sync_log", RichLog)
        log.write("[bold cyan]Iniciando rastreo web distribuido...[/bold cyan]")

        # Retrocedemos 3 carpetas (cli/tui/modals.py -> cli/tui -> cli -> raiz)
        project_dir = Path(__file__).resolve().parent.parent.parent

        try:
            # Lanza Docker sin congelar la interfaz
            process = await asyncio.create_subprocess_exec(
                "docker-compose", "run", "--rm", "scraper",
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            # Crea un hilo de fondo que lee la salida de Node.js línea por línea
            asyncio.create_task(self.read_output(process, log))
        except Exception as e:
            log.write(f"[bold red]Error iniciando el sabueso: {e}[/bold red]")

    async def read_output(self, process, log):
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            # Escribimos en el panel de Matrix
            log.write(line.decode().rstrip())
        await process.wait()
        log.write(
            f"\n[bold green]Rastreo finalizado. Puedes cerrar esta ventana.[/bold green]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class WatcherModal(ModalScreen[str]):
    """Diálogo para añadir a la lista negra/vigilancia."""

    def compose(self) -> ComposeResult:
        with Vertical(id="watcher_dialog"):
            yield Label("👀 Vigilar Nuevo Autor/Saga", classes="modal_title")
            yield Input(placeholder="Ej: Tatsuki Fujimoto", id="inp_keyword")
            with Horizontal(classes="form_buttons"):
                yield Button("Vigilar", variant="success", id="btn_add")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            self.dismiss(self.query_one("#inp_keyword", Input).value)
        else:
            self.dismiss(None)


class LogPagesModal(ModalScreen[int]):
    """Diálogo rápido para el Tracker."""

    def compose(self) -> ComposeResult:
        with Vertical(id="pages_dialog"):
            yield Label("📖 Anotar Páginas Leídas Hoy", classes="modal_title")
            yield Input(placeholder="Ej: 50", id="inp_pages")
            with Horizontal(classes="form_buttons"):
                yield Button("Guardar", variant="success", id="btn_add")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            val = self.query_one("#inp_pages", Input).value
            self.dismiss(int(val) if val.isdigit() else None)
        else:
            self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    """Diálogo de confirmación universal y peligroso."""

    def __init__(self, prompt_text: str, **kwargs):
        super().__init__(**kwargs)
        self.prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_dialog"):
            yield Label(self.prompt_text, classes="modal_title")
            with Horizontal(classes="form_buttons"):
                yield Button("Confirmar", variant="error", id="btn_confirm")
                yield Button("Cancelar", variant="primary", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)
