import re
import os
import asyncio.subprocess
import qrcode
import io
import socket
import asyncio
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Checkbox, RichLog, Select, Markdown, TextArea
from textual.containers import Vertical, Horizontal, VerticalScroll
from pathlib import Path
from textual import work
from textual_plotext import PlotextPlot
from .constants import API_GENRE_STATS
import httpx


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


class SyncConsoleModal(ModalScreen):
    """Terminal emulada para ejecutar scrapers de forma dinámica."""

    # Añade service_name con valor por defecto para no romper la Biblioteca
    def __init__(self, service_name: str = "scraper-books", **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name

    def compose(self) -> ComposeResult:
        with Vertical(id="sync_dialog"):
            yield Label(f"Terminal de Sincronización: {self.service_name.upper()}", classes="modal_title")
            yield RichLog(id="sync_log", highlight=True, markup=True)
            with Horizontal(classes="form_buttons"):
                yield Button("Cerrar Conexión", variant="error", id="btn_close")

    def on_mount(self) -> None:
        self.run_sync()

    @work(thread=True)
    def run_sync(self) -> None:
        log = self.query_one("#sync_log", RichLog)
        log.write(
            f"[bold green]Iniciando enlace con contenedor {self.service_name}...[/bold green]")

        base_dir = Path(__file__).resolve().parent.parent.parent
        compose_file = str(base_dir / "docker-compose.yml")

        # Inyectamos Node directo con la bandera --manual
        if self.service_name == "scraper-movies":
            cmd = ["docker-compose", "-f", compose_file, "exec", "-T",
                   "scraper-movies", "node", "movie_radar.js", "--manual"]
        else:
            cmd = ["docker-compose", "-f", compose_file, "exec", "-T",
                   "scraper-books", "node", "book_radar.js", "--manual"]

        try:
            import subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                self.app.call_from_thread(log.write, line.strip())

            process.wait()
            self.app.call_from_thread(
                log.write, "[bold cyan]--- TRANSMISIÓN FINALIZADA ---[/bold cyan]")
        except Exception as e:
            self.app.call_from_thread(
                log.write, f"[bold red]Error crítico de sistema:[/bold red] {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close":
            self.dismiss(None)


class WatcherModal(ModalScreen[str]):
    """Diálogo para añadir a la lista negra/vigilancia."""

    # Añadimos parámetros dinámicos para que sirva en Biblioteca y Videoclub
    def __init__(self, title_text: str = "Vigilar Nuevo Autor/Saga", placeholder_text: str = "Ej: Tatsuki Fujimoto", **kwargs):
        super().__init__(**kwargs)
        self.title_text = title_text
        self.placeholder_text = placeholder_text

    def compose(self) -> ComposeResult:
        with Vertical(id="watcher_dialog"):
            yield Label(self.title_text, classes="modal_title")
            yield Input(placeholder=self.placeholder_text, id="inp_keyword")
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
                "ServerAliveInterval=60", "-R", "80:localhost:8008", "nokey@localhost.run",
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
                "ServerAliveInterval=60", "-R", "80:localhost:8008", "nokey@localhost.run",
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
    """Diálogo para eliminar un directorio mediante selección explícita."""

    def __init__(self, dirs: list, **kwargs):
        super().__init__(**kwargs)
        self.dirs = dirs

    def compose(self) -> ComposeResult:
        with Vertical(id="move_dir_dialog"):  # Reciclamos el CSS de Mover Directorio
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


class MovieFullEditModal(ModalScreen[dict]):
    """Ventana flotante con Scroll para editar toda la ficha de la película."""

    def __init__(self, movie: dict, **kwargs):
        super().__init__(**kwargs)
        self.movie = movie

    def compose(self) -> ComposeResult:
        # Usamos el mismo ID para reciclar el CSS de scroll
        with Vertical(id="full_edit_dialog"):
            yield Label(f"Editando: {self.movie.get('title')}", classes="modal_title")
            with VerticalScroll():
                yield Label("Título de la cinta (*):", classes="edit_label")
                yield Input(value=self.movie.get('title', ''), id="inp_title")

                yield Label("Director:", classes="edit_label")
                yield Input(value=self.movie.get('director', ''), id="inp_director")

                yield Label("Guionistas:", classes="edit_label")
                yield Input(value=self.movie.get('writers', ''), id="inp_writers")

                yield Label("Productora:", classes="edit_label")
                yield Input(value=self.movie.get('production_company', ''), id="inp_production")

                yield Label("Formato:", classes="edit_label")
                FORMATS = [(f, f)
                           for f in ["BLU-RAY", "DVD", "4K", "VHS", "DIGITAL"]]
                yield Select(FORMATS, value=self.movie.get('format_type', 'BLU-RAY'), id="sel_format")

                yield Label("Año de Lanzamiento:", classes="edit_label")
                yield Input(value=str(self.movie.get('release_year') or ''), id="inp_year")

                yield Label("Duración (minutos):", classes="edit_label")
                yield Input(value=str(self.movie.get('duration_minutes') or ''), id="inp_duration")

                yield Label("Géneros (separados por coma):", classes="edit_label")
                generos_str = ", ".join(self.movie.get(
                    'genres', [])) if self.movie.get('genres') else ""
                yield Input(value=generos_str, id="inp_genres")

                yield Label("")  # Espaciador
                yield Checkbox("✔ Ya he visto esta película", value=self.movie.get('is_watched', False), id="chk_watched")

            with Horizontal(classes="form_buttons"):
                yield Button("Guardar Cambios", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            payload = {
                "title": self.query_one("#inp_title", Input).value,
                "director": self.query_one("#inp_director", Input).value,
                "writers": self.query_one("#inp_writers", Input).value,
                "production_company": self.query_one("#inp_production", Input).value,
                "format_type": self.query_one("#sel_format", Select).value,
                "is_watched": self.query_one("#chk_watched", Checkbox).value,
            }

            # Validaciones de números y listas
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
        else:
            self.dismiss(None)


class MovieTitleModal(ModalScreen[str]):
    """Pequeño diálogo para buscar una película por su nombre en TMDB."""

    def compose(self) -> ComposeResult:
        with Vertical(id="title_dialog"):  # Reutiliza CSS estándar de los modales pequeños
            yield Label("Buscar en TMDB", classes="modal_title")
            yield Label("Ingresa el título de la cinta:", classes="edit_label")
            yield Input(placeholder="Ej: Blade Runner", id="inp_title")
            with Horizontal(classes="form_buttons"):
                yield Button("Buscar", variant="success", id="btn_search")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_search":
            self.dismiss(self.query_one("#inp_title", Input).value)
        else:
            self.dismiss(None)


class AddMusicMenuModal(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        with Vertical(id="add_menu_dialog"):
            yield Label("🎵 Añadir Álbum", classes="modal_title")
            yield Button("1. Escanear Código de Barras (Celular)", id="btn_scan", variant="primary")
            yield Button("2. Buscar en Discogs (Nombre/Artista)", id="btn_manual_name", variant="warning")
            yield Button("3. Ingreso 100% Manual", id="btn_full_manual", variant="success")
            yield Button("Cancelar", id="btn_cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        options = {"btn_scan": "scan",
                   "btn_manual_name": "name", "btn_full_manual": "full"}
        self.dismiss(options.get(event.button.id, "cancel"))


class MusicTitleModal(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        with Vertical(id="title_dialog"):
            yield Label("Buscar en Discogs", classes="modal_title")
            yield Label("Ingresa Título y/o Artista:", classes="edit_label")
            yield Input(placeholder="Ej: The Dark Side of the Moon", id="inp_title")
            with Horizontal(classes="form_buttons"):
                yield Button("Buscar", variant="success", id="btn_search")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_search":
            self.dismiss(self.query_one("#inp_title", Input).value)
        else:
            self.dismiss(None)


class FinishMusicModal(ModalScreen[dict]):
    def compose(self) -> ComposeResult:
        with Vertical(id="finish_dialog"):
            yield Label("Registrar Sesión de Escucha", classes="modal_title")
            yield Label("Título del Álbum:", classes="edit_label")
            yield Input(id="inp_title", placeholder="Ej: Abbey Road")
            yield Label("Artista:", classes="edit_label")
            yield Input(id="inp_artist", placeholder="Ej: The Beatles")
            yield Label("")
            yield Checkbox("✔ Lo tengo en mi colección física", value=True, id="chk_owned")
            with Horizontal(classes="form_buttons"):
                yield Button("Registrar", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self.dismiss({
                "title": self.query_one("#inp_title", Input).value,
                "artist": self.query_one("#inp_artist", Input).value,
                "is_owned": self.query_one("#chk_owned", Checkbox).value
            })
        else:
            self.dismiss(None)


class MusicFullEditModal(ModalScreen[dict]):
    def __init__(self, album: dict, **kwargs):
        super().__init__(**kwargs)
        self.album = album

    def compose(self) -> ComposeResult:
        with Vertical(id="full_edit_dialog"):
            yield Label("Editando Álbum", classes="modal_title")
            with VerticalScroll():
                yield Label("Título (*):", classes="edit_label")
                yield Input(value=self.album.get('title', ''), id="inp_title")
                yield Label("Artista:", classes="edit_label")
                yield Input(value=self.album.get('artist', ''), id="inp_artist")
                yield Label("Sello Discográfico:", classes="edit_label")
                yield Input(value=self.album.get('label', ''), id="inp_label")
                yield Label("Formato:", classes="edit_label")
                FORMATS = [(f, f)
                           for f in ["VINYL", "CD", "CASSETTE", "DIGITAL"]]
                yield Select(FORMATS, value=self.album.get('format_type', 'VINYL'), id="sel_format")
                yield Label("Año de Lanzamiento:", classes="edit_label")
                yield Input(value=str(self.album.get('release_year') or ''), id="inp_year")
            with Horizontal(classes="form_buttons"):
                yield Button("Guardar", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            payload = {
                "title": self.query_one("#inp_title", Input).value,
                "artist": self.query_one("#inp_artist", Input).value,
                "label": self.query_one("#inp_label", Input).value,
                "format_type": self.query_one("#sel_format", Select).value,
            }
            year = self.query_one("#inp_year", Input).value
            if year.isdigit():
                payload["release_year"] = int(year)
            self.dismiss(payload)
        else:
            self.dismiss(None)


class MusicScannerModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        with Vertical(id="scanner_dialog"):
            yield Label("Iniciando Escáner (Discogs)...", id="scanner_title", classes="modal_title")
            yield RichLog(id="scanner_qr", markup=False, highlight=False)
            yield Button("Cerrar Conexión Segura", variant="error", id="btn_cancel")

    async def on_mount(self) -> None:
        log = self.query_one("#scanner_qr", RichLog)
        title = self.query_one("#scanner_title", Label)
        log.write("Negociando túnel cifrado SSH...\n")
        import asyncio
        from pathlib import Path
        import re
        key_path = str(Path.home() / ".ssh" / "library_cli_key")
        try:
            self.tunnel_process = await asyncio.create_subprocess_exec(
                "ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no", "-o",
                "ServerAliveInterval=60", "-R", "80:localhost:8008", "nokey@localhost.run",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            asyncio.create_task(self.read_output(log, title))
        except Exception as e:
            log.write(f"Error crítico SSH: {e}")

    async def read_output(self, log: RichLog, title: Label) -> None:
        import re
        while True:
            line = await self.tunnel_process.stdout.readline()
            if not line:
                break
            text_line = line.decode().strip()
            match = re.search(r"(https://[a-zA-Z0-9-]+\.lhr\.life)", text_line)
            if match:
                url = match.group(1) + "/api/music/scan/"
                title.update(f"Escanea o visita:\n{url}")
                self.render_qr(url, log)
                break

    def render_qr(self, url: str, log: RichLog) -> None:
        import qrcode
        import io
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)
        log.clear()
        log.write(f.getvalue())
        log.write(
            "\n[El servidor de Discogs escucha. Escanea y cierra al terminar]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def on_unmount(self) -> None:
        if hasattr(self, 'tunnel_process') and self.tunnel_process:
            try:
                self.tunnel_process.terminate()
            except:
                pass


class EvacuationModal(ModalScreen[str]):
    """Menú de emergencia para el Protocolo de Evacuación de Datos."""

    def compose(self) -> ComposeResult:
        with Vertical(id="add_menu_dialog"):
            yield Label("Protocolo de Evacuación", classes="modal_title")
            yield Label("[dim]Administración de las Cápsulas del Tiempo (Backups).[/dim]")
            yield Button("1. Generar Cápsula (Backup)", id="btn_backup", variant="success")
            yield Button("2. Restaurar Búnker", id="btn_restore", variant="error")
            yield Button("Cancelar", id="btn_cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        options = {"btn_backup": "backup", "btn_restore": "restore"}
        self.dismiss(options.get(event.button.id, "cancel"))


class ImportPGNModal(ModalScreen[dict]):
    """Diálogo para pegar una partida PGN en crudo y ubicarla en el árbol."""

    def __init__(self, dirs: list, **kwargs):
        super().__init__(**kwargs)
        self.dirs = dirs

    def compose(self) -> ComposeResult:
        with Vertical(id="full_edit_dialog"):
            yield Label("♟️ Importar Partida (PGN)", classes="modal_title")
            with VerticalScroll():
                yield Label("Título de la Estancia:", classes="edit_label")
                yield Input(id="inp_title", placeholder="Ej: Kasparov vs Topalov (Inmortal)")

                yield Label("Ubicación en el Explorador:", classes="edit_label")
                options = [("Raíz (Ninguno)", "")] + \
                    [(f"■ {d['name']}", str(d['id'])) for d in self.dirs]
                yield Select(options, id="sel_dir")

                yield Label("Pega el texto PGN:", classes="edit_label")
                yield TextArea(id="inp_pgn", language="markdown")

            with Horizontal(classes="form_buttons"):
                yield Button("Analizar", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            dir_val = self.query_one("#sel_dir", Select).value
            self.dismiss({
                "title": self.query_one("#inp_title", Input).value,
                "directory": int(dir_val) if dir_val else None,
                "pgn": self.query_one("#inp_pgn", TextArea).text
            })
        else:
            self.dismiss(None)


class CreateGameModal(ModalScreen[dict]):
    """Diálogo para crear una partida de ajedrez desde cero."""

    def __init__(self, dirs: list, **kwargs):
        super().__init__(**kwargs)
        self.dirs = dirs

    def compose(self) -> ComposeResult:
        with Vertical(id="dir_dialog"):  # Usamos un CSS existente para modales de tamaño moderado
            yield Label("♟️ Crear Partida en Blanco", classes="modal_title")
            
            yield Label("Título de la Estancia:", classes="edit_label")
            yield Input(id="inp_title", placeholder="Ej: Laboratorio de Siciliana")

            yield Label("Ubicación en el Explorador:", classes="edit_label")
            options = [("Raíz (Ninguno)", "")] + \
                [(f"■ {d['name']}", str(d['id'])) for d in self.dirs]
            yield Select(options, id="sel_dir")

            yield Label("Orientación del Tablero:", classes="edit_label")
            yield Select([("Jugar con Blancas", "white"), ("Jugar con Negras", "black")], value="white", id="sel_orientation")

            with Horizontal(classes="form_buttons"):
                yield Button("Crear", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            dir_val = self.query_one("#sel_dir", Select).value
            orientation_val = self.query_one("#sel_orientation", Select).value
            self.dismiss({
                "title": self.query_one("#inp_title", Input).value,
                "directory": int(dir_val) if dir_val else None,
                "orientation": orientation_val,
            })
        else:
            self.dismiss(None)


class CreateVariationModal(ModalScreen[str | None]):
    """Modal para crear una bifurcación ingresando la jugada alternativa."""

    def __init__(self, current_san: str, ply_number: int, **kwargs):
        super().__init__(**kwargs)
        self.current_san = current_san
        self.ply_number = ply_number

    def compose(self) -> ComposeResult:
        with Vertical(id="dir_dialog"):
            yield Label(f"⑂ Crear Variante en Jugada: {self.current_san}", classes="modal_title")
            yield Label(f"Ply {self.ply_number} — Ingresa la jugada alternativa:", classes="edit_label")
            yield Input(id="inp_var_move", placeholder="Ej: c5, Nf6, d4...")
            with Horizontal(classes="form_buttons"):
                yield Button("Crear Variante", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            val = self.query_one("#inp_var_move", Input).value.strip()
            self.dismiss(val if val else None)
        else:
            self.dismiss(None)


class SelectVariationModal(ModalScreen[int | None]):
    """Modal para seleccionar una bifurcación existente."""

    def __init__(self, variations: list, **kwargs):
        super().__init__(**kwargs)
        self.variations_list = variations

    def compose(self) -> ComposeResult:
        with Vertical(id="dir_dialog"):
            yield Label("⑂ Seleccionar Variante", classes="modal_title")
            options = []
            for i, v in enumerate(self.variations_list):
                first_move = v['moves_san'][0] if v.get('moves_san') else '?'
                preview = ' '.join(v['moves_san'][:4])
                options.append((f"{i+1}. {first_move} ({preview}...)", i))
            yield Select(options, id="sel_variation")
            with Horizontal(classes="form_buttons"):
                yield Button("Entrar", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            val = self.query_one("#sel_variation", Select).value
            self.dismiss(val if val is not Select.BLANK else None)
        else:
            self.dismiss(None)


class ChessNoteModal(ModalScreen[str]):
    """Editor dividido (estilo Obsidian) para la bitácora teórica."""

    # Inyectamos CSS específico para que el modal sea gigante y dividido
    CSS = """
    #obsidian_edit_dialog {
        width: 90%;
        height: 90%;
        background: $surface;
        border: heavy $primary;
        padding: 1 2;
    }
    #obsidian_split {
        height: 1fr;
        margin-bottom: 1;
    }
    .obsidian_panel {
        width: 1fr;
        height: 100%;
        border: solid $accent;
        margin: 0 1;
        padding: 0 1;
    }
    #md_preview {
        height: 100%;
        overflow-y: auto;
    }
    """

    def __init__(self, current_text: str = "", **kwargs):
        super().__init__(**kwargs)
        self.current_text = current_text

    def compose(self) -> ComposeResult:
        with Vertical(id="obsidian_edit_dialog"):
            yield Label("📝 Editor Táctico (Markdown)", classes="modal_title")

            # Contenedor Horizontal para dividir la pantalla
            with Horizontal(id="obsidian_split"):
                # Panel Izquierdo: Escritura cruda
                with Vertical(classes="obsidian_panel"):
                    yield Label("Modo Edición:", classes="edit_label")
                    yield TextArea(self.current_text, id="inp_note", language="markdown")

                # Panel Derecho: Renderizado en vivo
                with Vertical(classes="obsidian_panel"):
                    yield Label("Previsualización:", classes="edit_label")
                    yield Markdown(self.current_text, id="md_preview")

            with Horizontal(classes="form_buttons"):
                yield Button("Guardar", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_mount(self) -> None:
        # Pone el cursor automáticamente en el cuadro de texto al abrir
        self.query_one("#inp_note", TextArea).focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        # La magia de la reactividad: lo que escribes a la izquierda, se renderiza a la derecha
        self.query_one("#md_preview", Markdown).update(event.text_area.text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            self.dismiss(self.query_one("#inp_note", TextArea).text)
        else:
            self.dismiss(None)


class ChessDirModal(ModalScreen[dict]):
    """Diálogo para crear un directorio táctico en el árbol."""

    def __init__(self, dirs: list, **kwargs):
        super().__init__(**kwargs)
        self.dirs = dirs

    def compose(self) -> ComposeResult:
        with Vertical(id="dir_dialog"):
            yield Label("📁 Nuevo Directorio Táctico", classes="modal_title")
            yield Input(placeholder="Ej: Defensa Siciliana", id="inp_dirname")

            yield Label("Directorio Padre (Opcional):", classes="edit_label")
            options = [("Raíz (Ninguno)", "")] + \
                [(f"■ {d['name']}", str(d['id'])) for d in self.dirs]
            yield Select(options, id="sel_parent")

            with Horizontal(classes="form_buttons"):
                yield Button("Crear", variant="success", id="btn_save")
                yield Button("Cancelar", variant="error", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            parent_val = self.query_one("#sel_parent", Select).value
            self.dismiss({
                "name": self.query_one("#inp_dirname", Input).value,
                "parent": int(parent_val) if parent_val else None
            })
        else:
            self.dismiss(None)


class GenreStatsModal(ModalScreen[None]):
    """Modal ancho para mostrar el gráfico de barras de géneros."""

    def compose(self) -> ComposeResult:
        with Vertical(id="genre_stats_dialog"):
            yield Label("Estadísticas de Género", classes="modal_title")
            yield PlotextPlot(id="genre_plot")
            with Horizontal(classes="form_buttons"):
                yield Button("Cerrar", variant="error", id="btn_cancel")

    def on_mount(self) -> None:
        self.fetch_data()

    @work(thread=True)
    def fetch_data(self) -> None:
        try:
            resp = httpx.get(API_GENRE_STATS, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self.app.call_from_thread(self.draw_plot, data.get("labels", []), data.get("values", []))
            else:
                self.app.call_from_thread(self.app.notify, "Error obteniendo géneros", severity="error")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Red: {e}", severity="error")

    def draw_plot(self, labels: list, values: list) -> None:
        plot = self.query_one("#genre_plot", PlotextPlot)
        plt = plot.plt
        plt.clear_data()
        
        # Invertimos para que el mayor quede arriba si usamos bar() o similar
        plt.bar(labels, values)
        plt.title("Distribución por Géneros")
        plt.theme('dark')
        plot.refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)
