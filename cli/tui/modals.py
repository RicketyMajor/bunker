import re
import os
import asyncio.subprocess
import qrcode
import io
import socket
import asyncio
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Checkbox, RichLog, Select, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from pathlib import Path


class IsbnModal(ModalScreen[str]):
    """Ventana flotante para ingresar un ISBN nuevo."""

    def compose(self) -> ComposeResult:
        with Vertical(id="isbn_dialog"):
            yield Label("Añadir Nuevo Ejemplar", classes="modal_title")
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
            yield Label(f"Editando: {self.book.get('title')}", classes="modal_title")
            with VerticalScroll():
                yield Label("Título de la obra (*):", classes="edit_label")
                yield Input(value=self.book.get('title', ''), id="inp_title")
                yield Label("Subtítulo (Opcional):", classes="edit_label")
                yield Input(value=self.book.get('subtitle', ''), id="inp_sub")
                yield Label("Autor Principal:", classes="edit_label")
                yield Input(value=self.book.get('author_name', ''), id="inp_author")
                # Widget Select para los formatos
                yield Label("Formato:", classes="edit_label")
                FORMATS = [(f, f) for f in ["NOVEL", "MANGA",
                                            "COMIC", "ANTHOLOGY", "ACADEMIC", "POEM"]]
                yield Select(FORMATS, value=self.book.get('format_type', 'NOVEL'), id="sel_format")

                yield Label("Editorial:", classes="edit_label")
                yield Input(value=self.book.get('publisher', ''), id="inp_publisher")
                yield Label("Géneros (separados por coma):", classes="edit_label")
                generos_str = ", ".join(self.book.get(
                    'genre_list', [])) if self.book.get('genre_list') else ""
                yield Input(value=generos_str, id="inp_genres")
                yield Label("Número total de páginas:", classes="edit_label")
                yield Input(value=str(self.book.get('page_count', '')), id="inp_pages")
                yield Label("")
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
                # Extraído del Select
                "format_type": self.query_one("#sel_format", Select).value,
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
            yield Label("Prestar Ejemplar", classes="modal_title")
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
            yield Label("📁 Nuevo Directorio", classes="modal_title")
            yield Input(placeholder="Nombre (Ej: DC Comics)", id="inp_dirname")

            yield Label("Color:", classes="edit_label")
            COLORS = [(c.capitalize(), c) for c in ["red", "green",
                                                    "yellow", "blue", "magenta", "cyan", "white"]]
            yield Select(COLORS, value="cyan", id="sel_dircolor")

            with Horizontal(classes="form_buttons"):
                yield Button("Crear", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self.dismiss({
                "name": self.query_one("#inp_dirname", Input).value,
                # Extraído del Select
                "color_hex": self.query_one("#sel_dircolor", Select).value
            })
        else:
            self.dismiss(None)


class SyncConsoleModal(ModalScreen[None]):
    """La Terminal de Matrix: Ejecuta el Scraper Dockerizado en vivo."""

    def __init__(self, service_name: str = "scraper-books", **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name

    def compose(self) -> ComposeResult:
        with Vertical(id="sync_dialog"):
            yield Label(f"Matrix Scraper Network [{self.service_name}]", classes="modal_title")
            yield RichLog(id="sync_log", highlight=True, markup=True)
            yield Button("Cerrar Conexión", variant="error", id="btn_cancel")

    async def on_mount(self) -> None:
        log = self.query_one("#sync_log", RichLog)
        log.write(
            f"[bold cyan]Iniciando rastreo web en {self.service_name}...[/bold cyan]")

        project_dir = Path(__file__).resolve().parent.parent.parent

        try:
            process = await asyncio.create_subprocess_exec(
                "docker-compose", "run", "--rm", self.service_name,
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            asyncio.create_task(self.read_output(process, log))
        except Exception as e:
            log.write(f"[bold red]Error iniciando el sabueso: {e}[/bold red]")

    async def read_output(self, process, log):
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            log.write(line.decode().rstrip())
        await process.wait()
        log.write(
            "\n[bold green]Rastreo finalizado. Puedes cerrar esta ventana.[/bold green]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class WatcherModal(ModalScreen[str]):
    """Diálogo para añadir a la lista negra/vigilancia."""

    def compose(self) -> ComposeResult:
        with Vertical(id="watcher_dialog"):
            yield Label("Vigilar Nuevo Autor/Saga", classes="modal_title")
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
            yield Label("Anotar Páginas Leídas Hoy", classes="modal_title")
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


class AddMenuModal(ModalScreen[str]):
    """Menú principal de adquisición (Escáner, ISBN, Manual)."""

    def compose(self) -> ComposeResult:
        with Vertical(id="add_menu_dialog"):
            yield Label("Añadir Nuevo Ejemplar", classes="modal_title")
            yield Label("Selecciona el método de ingreso:", classes="edit_label")
            yield Button("Escáner Móvil (QR)", variant="primary", id="btn_scan")
            yield Button("Por código ISBN", variant="primary", id="btn_isbn")
            yield Button("Ingreso 100% Manual", variant="primary", id="btn_manual")
            yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_scan":
            self.dismiss("scan")
        elif event.button.id == "btn_isbn":
            self.dismiss("isbn")
        elif event.button.id == "btn_manual":
            self.dismiss("manual")
        else:
            self.dismiss(None)


class ManualAddModal(ModalScreen[dict]):
    """Formulario gigante para crear un libro desde cero."""

    def compose(self) -> ComposeResult:
        # Reusamos el ID "full_edit_dialog" para aprovechar su CSS de Scroll y tamaño
        with Vertical(id="full_edit_dialog"):
            yield Label("Ingreso Manual de Ejemplar", classes="modal_title")
            with VerticalScroll():
                yield Label("Título de la obra (*):", classes="edit_label")
                yield Input(id="inp_title", placeholder="Ej: Las Flores del Mal")

                yield Label("Subtítulo (Opcional):", classes="edit_label")
                yield Input(id="inp_sub")

                yield Label("Autor Principal:", classes="edit_label")
                yield Input(id="inp_author", placeholder="Ej: Charles Baudelaire")

                yield Label("Formato:", classes="edit_label")
                FORMATS = [(f, f) for f in ["NOVEL", "MANGA",
                                            "COMIC", "ANTHOLOGY", "ACADEMIC", "POEM"]]
                yield Select(FORMATS, value="POEM", id="sel_format")

                yield Label("Editorial:", classes="edit_label")
                yield Input(id="inp_publisher")

                yield Label("Géneros (separados por coma):", classes="edit_label")
                yield Input(id="inp_genres")

                yield Label("Número total de páginas:", classes="edit_label")
                yield Input(id="inp_pages")

                yield Label("")  # Espaciador
                yield Checkbox("✔ Libro Completado/Leído", value=False, id="chk_read")

            with Horizontal(classes="form_buttons"):
                yield Button("Guardar en Biblioteca", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            pages_val = self.query_one("#inp_pages", Input).value
            payload = {
                "title": self.query_one("#inp_title", Input).value,
                "subtitle": self.query_one("#inp_sub", Input).value,
                "author_input": self.query_one("#inp_author", Input).value,
                "format_type": self.query_one("#sel_format", Select).value,
                "publisher": self.query_one("#inp_publisher", Input).value,
                "genre_input": self.query_one("#inp_genres", Input).value,
                "is_read": self.query_one("#chk_read", Checkbox).value,
            }
            if pages_val.isdigit():
                payload["page_count"] = int(pages_val)
            self.dismiss(payload)
        elif event.button.id == "btn_cancel":
            self.dismiss(None)


class ScannerModal(ModalScreen[None]):
    """Modal ciberpunk que levanta un túnel SSH y dibuja el QR en ASCII."""

    def compose(self) -> ComposeResult:
        with Vertical(id="scanner_dialog"):
            yield Label("Iniciando Escáner Móvil...", id="scanner_title", classes="modal_title")
            yield RichLog(id="scanner_qr", markup=False, highlight=False)
            yield Button("Cerrar Conexión Segura", variant="error", id="btn_cancel")

    async def on_mount(self) -> None:
        log = self.query_one("#scanner_qr", RichLog)
        title = self.query_one("#scanner_title", Label)
        log.write("Negociando túnel cifrado SSH con localhost.run...\n")

        key_path = str(Path.home() / ".ssh" / "library_cli_key")
        try:
            # Levanta el túnel en background
            self.tunnel_process = await asyncio.create_subprocess_exec(
                "ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no", "-o",
                "ServerAliveInterval=60", "-R", "80:localhost:8000", "nokey@localhost.run",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            # Inicia el lector de logs
            asyncio.create_task(self.read_output(log, title))
        except Exception as e:
            log.write(f"Error crítico iniciando SSH: {e}")

    async def read_output(self, log: RichLog, title: Label) -> None:
        while True:
            line = await self.tunnel_process.stdout.readline()
            if not line:
                break
            text_line = line.decode().strip()

            # Intercepta la URL segura
            match = re.search(r"(https://[a-zA-Z0-9-]+\.lhr\.life)", text_line)
            if match:
                url = match.group(1) + "/scanner/"
                title.update(f"Escanea el QR o visita:\n{url}")
                self.render_qr(url, log)
                break  # Deja de leer la terminal para no saturar la pantalla

    def render_qr(self, url: str, log: RichLog) -> None:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(url)
        qr.make(fit=True)

        # Engaña a qrcode para que imprima en una variable en vez de la consola real
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)

        log.clear()
        # Inyecta el QR renderizado en ASCII directo a nuestro Widget
        log.write(f.getvalue())
        log.write(
            "\n[El servidor ya está escuchando. Escanea y presiona el botón abajo para terminar]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def on_unmount(self) -> None:
        # Si el usuario cierra el modal (con botón o ESC), matamos el proceso SSH
        if hasattr(self, 'tunnel_process') and self.tunnel_process:
            try:
                self.tunnel_process.terminate()
            except:
                pass


class MovieScannerModal(ModalScreen[None]):
    """Modal ciberpunk que levanta un túnel SSH y dibuja el QR en ASCII."""

    def compose(self) -> ComposeResult:
        with Vertical(id="scanner_dialog"):
            yield Label("Iniciando Escáner Móvil...", id="scanner_title", classes="modal_title")
            yield RichLog(id="scanner_qr", markup=False, highlight=False)
            yield Button("Cerrar Conexión Segura", variant="error", id="btn_cancel")

    async def on_mount(self) -> None:
        log = self.query_one("#scanner_qr", RichLog)
        title = self.query_one("#scanner_title", Label)
        log.write("Negociando túnel cifrado SSH con localhost.run...\n")

        key_path = str(Path.home() / ".ssh" / "library_cli_key")
        try:
            # Levanta el túnel en background
            self.tunnel_process = await asyncio.create_subprocess_exec(
                "ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no", "-o",
                "ServerAliveInterval=60", "-R", "80:localhost:8000", "nokey@localhost.run",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            # Inicia el lector de logs
            asyncio.create_task(self.read_output(log, title))
        except Exception as e:
            log.write(f"Error crítico iniciando SSH: {e}")

    async def read_output(self, log: RichLog, title: Label) -> None:
        while True:
            line = await self.tunnel_process.stdout.readline()
            if not line:
                break
            text_line = line.decode().strip()

            # Intercepta la URL segura
            match = re.search(r"(https://[a-zA-Z0-9-]+\.lhr\.life)", text_line)
            if match:
                url = match.group(1) + "/api/movies/scanner-web/"
                title.update(f"Escanea el QR o visita:\n{url}")
                self.render_qr(url, log)
                break  # Deja de leer la terminal para no saturar la pantalla

    def render_qr(self, url: str, log: RichLog) -> None:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(url)
        qr.make(fit=True)

        # Engaña a qrcode para que imprima en una variable en vez de la consola real
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)

        log.clear()
        # Inyecta el QR renderizado en ASCII directo a nuestro Widget
        log.write(f.getvalue())
        log.write(
            "\n[El servidor ya está escuchando. Escanea y presiona el botón abajo para terminar]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def on_unmount(self) -> None:
        # Si el usuario cierra el modal (con botón o ESC), matamos el proceso SSH
        if hasattr(self, 'tunnel_process') and self.tunnel_process:
            try:
                self.tunnel_process.terminate()
            except:
                pass


class FinishBookModal(ModalScreen[dict]):
    """Diálogo para registrar un libro como terminado en el año."""

    def compose(self) -> ComposeResult:
        with Vertical(id="finish_dialog"):
            yield Label("Registrar Libro Terminado", classes="modal_title")
            yield Label("Título de la obra:", classes="edit_label")
            yield Input(id="inp_title", placeholder="Ej: Dune")
            yield Label("Autor Principal:", classes="edit_label")
            yield Input(id="inp_author", placeholder="Ej: Frank Herbert")
            yield Label("")  # Espaciador
            yield Checkbox("✔ Este libro es de mi propiedad (En Estantería)", value=True, id="chk_owned")

            with Horizontal(classes="form_buttons"):
                yield Button("Registrar Victoria", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self.dismiss({
                "title": self.query_one("#inp_title", Input).value,
                "author_name": self.query_one("#inp_author", Input).value,
                "is_owned": self.query_one("#chk_owned", Checkbox).value
            })
        else:
            self.dismiss(None)


class WatchersListModal(ModalScreen[int]):
    """Lista los autores vigilados y permite eliminarlos por ID."""

    def __init__(self, watchers: list, **kwargs):
        super().__init__(**kwargs)
        self.watchers = watchers

    def compose(self) -> ComposeResult:
        with Vertical(id="watchers_list_dialog"):
            yield Label("Radar de Vigilancia Actual", classes="modal_title")
            with VerticalScroll(id="watchers_scroll"):
                if not self.watchers:
                    yield Label("No estás vigilando a nadie actualmente.", classes="edit_label")
                for w in self.watchers:
                    yield Label(f"[cyan]ID {w['id']}[/cyan] - {w['keyword']} (Desde: {w.get('created_at', '')[:10]})")

            yield Label("Para dejar de vigilar a alguien, ingresa su ID:", classes="edit_label")
            yield Input(placeholder="Ej: 3 (Deja en blanco para solo salir)", id="inp_del_id")

            with Horizontal(classes="form_buttons"):
                yield Button("Ejecutar", variant="error", id="btn_del")
                yield Button("Cerrar", variant="primary", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_del":
            val = self.query_one("#inp_del_id", Input).value
            self.dismiss(int(val) if val.isdigit() else None)
        else:
            self.dismiss(None)


class MoveToDirModal(ModalScreen[str]):
    """Diálogo para transferir un libro a un directorio existente."""

    def __init__(self, dirs: list, **kwargs):
        super().__init__(**kwargs)
        self.dirs = dirs

    def compose(self) -> ComposeResult:
        with Vertical(id="move_dir_dialog"):
            yield Label("Mover Ejemplar", classes="modal_title")
            yield Label("Selecciona la carpeta de destino:", classes="edit_label")

            # Genera las opciones: Primero la raíz, luego los directorios
            options = [("📁 Raíz (Sacar de la carpeta)", "root")] + \
                [(f"■ {d['name']}", str(d['id'])) for d in self.dirs]
            yield Select(options, id="sel_dest")

            with Horizontal(classes="form_buttons"):
                yield Button("Transferir", variant="success", id="btn_move")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_move":
            self.dismiss(self.query_one("#sel_dest", Select).value)
        else:
            self.dismiss("cancel")


class AddMovieMenuModal(ModalScreen[str]):
    """Las 3 vías de ingreso al Videoclub."""

    def compose(self) -> ComposeResult:
        with Vertical(id="add_menu_dialog"):
            yield Label("⌨ Añadir Película", classes="modal_title")
            yield Button("1. Escanear Código de Barras (Celular)", id="btn_scan", variant="primary")
            yield Button("2. Ingresar Nombre (Búsqueda TMDB)", id="btn_manual_name", variant="warning")
            yield Button("3. Ingreso 100% Manual (Ficha)", id="btn_full_manual", variant="success")
            yield Button("Cancelar", id="btn_cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_scan":
            self.dismiss("scan")
        elif event.button.id == "btn_manual_name":
            self.dismiss("name")
        elif event.button.id == "btn_full_manual":
            self.dismiss("full")
        else:
            self.dismiss("cancel")


class ManualMovieAddModal(ModalScreen[dict]):
    """Formulario gigante para crear una película desde cero."""

    def compose(self) -> ComposeResult:
        with Vertical(id="full_edit_dialog"):
            yield Label("Ingreso 100% Manual de Película", classes="modal_title")
            with VerticalScroll():
                yield Label("Título de la cinta (*):", classes="edit_label")
                yield Input(id="inp_title", placeholder="Ej: El Padrino")

                yield Label("Director:", classes="edit_label")
                yield Input(id="inp_director", placeholder="Ej: Francis Ford Coppola")

                yield Label("Año de Lanzamiento:", classes="edit_label")
                yield Input(id="inp_year", placeholder="Ej: 1972")

                yield Label("Duración (minutos):", classes="edit_label")
                yield Input(id="inp_duration", placeholder="Ej: 175")

                yield Label("Formato:", classes="edit_label")
                FORMATS = [(f, f)
                           for f in ["BLU-RAY", "DVD", "4K", "VHS", "DIGITAL"]]
                yield Select(FORMATS, value="BLU-RAY", id="sel_format")

                yield Label("Géneros (separados por coma):", classes="edit_label")
                yield Input(id="inp_genres", placeholder="Ej: Drama, Crimen")

                yield Label("")  # Espaciador
                yield Checkbox("✔ Ya he visto esta película", value=False, id="chk_watched")

            with Horizontal(classes="form_buttons"):
                yield Button("Guardar en Videoclub", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            payload = {
                "title": self.query_one("#inp_title", Input).value,
                "director": self.query_one("#inp_director", Input).value,
                "format_type": self.query_one("#sel_format", Select).value,
                "is_watched": self.query_one("#chk_watched", Checkbox).value,
            }

            # Validaciones numéricas y de listas
            year = self.query_one("#inp_year", Input).value
            dur = self.query_one("#inp_duration", Input).value
            genres = self.query_one("#inp_genres", Input).value

            if year.isdigit():
                payload["release_year"] = int(year)
            if dur.isdigit():
                payload["duration_minutes"] = int(dur)
            if genres:
                payload["genres"] = [g.strip() for g in genres.split(",")]

            self.dismiss(payload)
        elif event.button.id == "btn_cancel":
            self.dismiss(None)


class DeleteDirModal(ModalScreen[str]):
    """Diálogo para eliminar un directorio existente."""

    def __init__(self, dirs: list, **kwargs):
        super().__init__(**kwargs)
        self.dirs = dirs

    def compose(self) -> ComposeResult:
        with Vertical(id="move_dir_dialog"):  # Reutiliza el CSS del otro modal
            yield Label("Destruir Directorio", classes="modal_title")
            yield Label("Selecciona la carpeta a eliminar:", classes="edit_label")
            yield Label("[dim]Los ítems en su interior volverán a la raíz.[/dim]", classes="edit_label")

            options = [(f"■ {d['name']}", str(d['id'])) for d in self.dirs]
            yield Select(options, id="sel_dest")

            with Horizontal(classes="form_buttons"):
                yield Button("Destruir", variant="error", id="btn_delete")
                yield Button("Cancelar", variant="primary", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_delete":
            try:
                self.dismiss(self.query_one("#sel_dest", Select).value)
            except:
                self.dismiss("cancel")
        else:
            self.dismiss("cancel")


class LogMinutesModal(ModalScreen[int]):
    """Diálogo rápido para el Tracker de Videoclub."""

    def compose(self) -> ComposeResult:
        with Vertical(id="pages_dialog"):
            yield Label("Anotar Minutos Vistos Hoy", classes="modal_title")
            yield Input(placeholder="Ej: 120", id="inp_minutes")
            with Horizontal(classes="form_buttons"):
                yield Button("Guardar", variant="success", id="btn_add")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            val = self.query_one("#inp_minutes", Input).value
            self.dismiss(int(val) if val.isdigit() else None)
        else:
            self.dismiss(None)


class FinishMovieModal(ModalScreen[dict]):
    """Diálogo para registrar una película como vista en el año."""

    def compose(self) -> ComposeResult:
        with Vertical(id="finish_dialog"):
            yield Label("Registrar Película Vista", classes="modal_title")
            yield Label("Título de la cinta:", classes="edit_label")
            yield Input(id="inp_title", placeholder="Ej: Interstellar")
            yield Label("Director:", classes="edit_label")
            yield Input(id="inp_director", placeholder="Ej: Christopher Nolan")
            yield Label("")
            yield Checkbox("✔ La tengo en mi bóveda física", value=True, id="chk_owned")

            with Horizontal(classes="form_buttons"):
                yield Button("Registrar Victoria", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self.dismiss({
                "title": self.query_one("#inp_title", Input).value,
                "director": self.query_one("#inp_director", Input).value,
                "is_owned": self.query_one("#chk_owned", Checkbox).value
            })
        else:
            self.dismiss(None)
