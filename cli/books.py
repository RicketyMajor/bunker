import typer
import re
import httpx
from rich.console import Console
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm
# 🎨 Añadimos las herramientas de maquetación avanzada
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
# 🎨 Añadimos Group y Align para el ensamblaje maestro
from rich.console import Group
from rich.align import Align
from cli.api import fetch_book_by_isbn
import json

console = Console()
book_app = typer.Typer(
    help="Manage your library books, comics, and mangas.", no_args_is_help=True)

API_LIBRARY = "http://localhost:8000/api/books/library/"
API_SCAN = "http://localhost:8000/api/books/scan/"


def parse_manga_title(raw_title: str):
    """
    Intenta extraer el título base y el número de tomo usando Regex.
    Ej: 'Chainsaw Man, Vol. 14' -> ('Chainsaw Man', '14')
    Ej: 'Berserk 01' -> ('Berserk', '1')
    """
    # Busca: [Cualquier texto] [Separadores opcionales] [Números al final]
    pattern = r"^(.*?)\s*(?:vol\.?|volume|tomo|#|-)?\s*0*(\d+)\s*$"
    match = re.search(pattern, raw_title, re.IGNORECASE)

    if match:
        base_title = match.group(1).strip()
        tomo = match.group(2).strip()
        # Limpiamos comas o guiones que queden colgando al final del título base
        base_title = re.sub(r"[,:-]$", "", base_title).strip()
        return base_title, tomo

    return raw_title, None


@book_app.command(name="list")
def list_books(
    title: str = typer.Option(None, "--title", "-t",
                              help="Filtrar por título parcial"),
    author: str = typer.Option(
        None, "--author", "-a", help="Filtrar por nombre de autor"),
    genre: str = typer.Option(None, "--genre", "-g",
                              help="Filtrar por género"),
    format_type: str = typer.Option(
        None, "--format", "-f", help="Filtrar por formato (NOVEL, MANGA, COMIC)"),
    read: bool = typer.Option(None, "--read/--unread",
                              help="Filtrar por estado de lectura")
):
    """Muestra los libros de tu biblioteca con opciones de búsqueda avanzada."""

    # Construimos el diccionario de parámetros para enviar en la URL
    params = {}
    if title:
        params['title'] = title
    if author:
        params['author'] = author
    if genre:
        params['genre'] = genre
    if format_type:
        params['format_type'] = format_type.upper()

    # Manejamos el booleano (si el usuario usó --read o --unread)
    if read is not None:
        params['is_read'] = "true" if read else "false"

    try:
        # httpx convertirá el diccionario 'params' mágicamente en ?author=X&title=Y
        response = httpx.get(API_LIBRARY, params=params)
        response.raise_for_status()
        books = response.json()
    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")
        return

    if not books:
        console.print(
            "[yellow]No se encontraron libros con esos filtros.[/yellow]")
        return

    # Imprimimos qué filtros estamos usando
    filters_used = ", ".join([f"{k}={v}" for k, v in params.items()])
    table_title = f"❖ [bold cyan]INVENTARIO DE BIBLIOTECA[/bold cyan] ❖"
    if filters_used:
        table_title += f"\n[dim](Filtros: {filters_used})[/dim]"

    # 🚀 REVOLUCIÓN VISUAL: box.SIMPLE_HEAVY elimina el ruido vertical
    table = Table(title=table_title, box=box.SIMPLE_HEAVY,
                  header_style="bold cyan", border_style="cyan")
    table.add_column("ID", justify="right", style="dim", no_wrap=True)
    table.add_column("Título", style="bold white")
    table.add_column("Autor", style="yellow")
    table.add_column("Formato", style="magenta")
    table.add_column("Leído", justify="center")
    table.add_column("Ubicación", justify="center")

    for book in books:
        # Glifos monocromáticos inyectados con color puro
        status = "[green]✔[/green]" if book.get('is_read') else "[red]✘[/red]"
        ubicacion = "[bold red]⇋ Prestado[/bold red]" if book.get(
            'is_loaned') else "[bold green]❖ Estantería[/bold green]"

        # 🚀 LÓGICA DEL TÍTULO EN ÁRBOL (Subtítulos dinámicos)
        title_display = book.get('title', 'Sin título').upper()
        details = book.get('details', {})
        format_type = book.get('format_type', 'NOVEL')

        # Si es Manga, calculamos la cantidad de tomos obtenidos
        if format_type == "MANGA" and details:
            tomos_raw = details.get('tomos_obtenidos', '')
            if tomos_raw:
                # Contamos los tomos separando por comas
                cantidad_tomos = len(
                    [t for t in str(tomos_raw).split(',') if t.strip()])
                title_display += f"\n  [dim]↳ {cantidad_tomos} tomos en colección[/dim]"

        # Si es Antología, contamos la longitud de la lista de cuentos
        elif format_type == "ANTHOLOGY" and details:
            cuentos = details.get('lista_cuentos', [])
            if cuentos:
                title_display += f"\n  [dim]↳ {len(cuentos)} cuentos incluidos[/dim]"

        table.add_row(
            str(book.get('id')),
            title_display,  # Pasamos nuestro título con la información inyectada
            book.get('author_name', 'Desconocido'),
            book.get('format_type', '-'),
            status,
            ubicacion
        )

    console.print()
    # Centramos la tabla en la pantalla
    console.print(Align.center(table))
    console.print()


@book_app.command(name="add")
def add_book_wizard():
    """Asistente maestro para añadir libros (Escáner, ISBN o 100% Manual)."""

    console.print("\n[bold cyan]🔮 ASISTENTE DE ADQUISICIONES 🔮[/bold cyan]")
    console.print(
        "[dim]Selecciona el método de ingreso para tu nuevo ejemplar:[/dim]")
    console.print(
        "  [bold green][1][/bold green] 📱 Activar Escáner de Código de Barras (Web)")
    console.print(
        "  [bold yellow][2][/bold yellow] 🔢 Ingresar ISBN manualmente (Búsqueda automática)")
    console.print(
        "  [bold magenta][3][/bold magenta] ✍️  Ingreso 100% Manual (Para libros antiguos o rarezas)")

    choice = Prompt.ask("\nElige una opción", choices=[
                        "1", "2", "3"], default="2")

    # ---------------------------------------------------------
    # OPCIÓN 1: EL ESCÁNER WEB
    # ---------------------------------------------------------
    if choice == "1":
        console.print("\n[bold cyan]📡 MODO ESCÁNER ACTIVADO[/bold cyan]")
        console.print(
            "Para usar la cámara de tu teléfono, asegúrate de estar en la misma red WiFi y abre:")
        console.print(
            "👉 [bold underline blue]http://localhost:8000/scanner/[/bold underline blue] (o reemplaza 'localhost' por la IP de tu PC)")
        console.print(
            "[dim]Nota: Si usabas ngrok antes y el link está caído, debes volver a ejecutar 'ngrok http 8000' en otra terminal para obtener un link público nuevo.[/dim]\n")
        return

    # ---------------------------------------------------------
    # OPCIÓN 2: ISBN MANUAL (Con Vista Previa y Confirmación)
    # ---------------------------------------------------------
    elif choice == "2":
        isbn = Prompt.ask(
            "\n[bold yellow]🔢 Ingresa el código ISBN[/bold yellow]")
        console.print(f"Consultando registros globales para {isbn}...")

        try:
            preview = fetch_book_by_isbn(isbn)
            if not preview:
                console.print(
                    f"[bold red]❌ Libro con ISBN {isbn} no encontrado.[/bold red]")
                return

            raw_title = preview.get('title', 'Desconocido')
            base_title, tomo_detectado = parse_manga_title(raw_title)

            # 🐉 EL INTERCEPTADOR: Si detectamos un tomo, buscamos la saga en la DB
            saga_existente = None
            if tomo_detectado:
                resp_lib = httpx.get(API_LIBRARY, params={"title": base_title})
                if resp_lib.status_code == 200:
                    coincidencias = resp_lib.json()
                    # Buscamos si alguna coincidencia es MANGA y su título coincide con la base
                    saga_existente = next((b for b in coincidencias if b.get(
                        'format_type') == 'MANGA' and base_title.lower() in b.get('title', '').lower()), None)

            # 2. Mostramos la tarjeta de confirmación con diseño geométrico
            preview_text = Text()
            preview_text.append(f"❖ Título: ", style="bold white")
            preview_text.append(
                f"{preview.get('title', 'Desconocido')}\n", style="cyan")
            preview_text.append(f"✎ Autor: ", style="bold white")
            preview_text.append(
                f"{preview.get('author', 'Desconocido')}\n", style="yellow")
            preview_text.append(f"◷ Publicación: ", style="bold white")
            preview_text.append(
                f"{preview.get('publish_date', '-')}\n", style="green")
            preview_text.append(f"▤ Páginas: ", style="bold white")
            preview_text.append(
                f"{preview.get('page_count', '-')}", style="magenta")

            console.print()
            console.print(Panel(
                preview_text, title="[bold magenta]Vista Previa del Libro[/bold magenta]", border_style="magenta", expand=False))

           # 🐉 PREGUNTA DE FUSIÓN
            if tomo_detectado and saga_existente:
                console.print(
                    f"\n[bold magenta]🐉 ¡Saga Detectada en tu Biblioteca![/bold magenta]")
                console.print(
                    f"Parece que este es el [bold]Tomo {tomo_detectado}[/bold] de la obra [bold cyan]'{saga_existente['title']}'[/bold cyan].")

                if Confirm.ask("¿Deseas inyectarlo como un nuevo tomo en lugar de crear un registro huérfano?"):
                    detalles = saga_existente.get('details', {})
                    tomos_str = str(detalles.get('tomos_obtenidos', ''))
                    tomos_lista = [t.strip()
                                   for t in tomos_str.split(',') if t.strip()]

                    if tomo_detectado not in tomos_lista:
                        tomos_lista.append(tomo_detectado)
                        tomos_lista.sort(key=lambda x: int(
                            x) if x.isdigit() else x)  # Orden numérico

                    detalles['tomos_obtenidos'] = ", ".join(tomos_lista)

                    patch_resp = httpx.patch(
                        f"{API_LIBRARY}{saga_existente['id']}/", json={"details": detalles})
                    if patch_resp.status_code == 200:
                        console.print(
                            f"\n[bold green]✅ Tomo {tomo_detectado} inyectado exitosamente en '{saga_existente['title']}'.[/bold green]\n")
                    else:
                        console.print(
                            f"\n[bold red]❌ Error al fusionar el tomo.[/bold red]\n")
                    return  # Cortamos la ejecución para no guardarlo como libro nuevo

            # 3. 🛡️ BARRERA UX STANDARD (Si no es manga, o si el usuario dijo que no a la fusión)
            if not Confirm.ask("¿Deseas registrar permanentemente este libro en tu biblioteca?"):
                console.print("\n[yellow]Operación cancelada.[/yellow]\n")
                return

            # 4. Si aprueba, disparamos la petición a nuestra API para que lo guarde oficialmente
            response = httpx.post(API_SCAN, json={"isbn": isbn})
            data = response.json()

            if response.status_code == 201:
                console.print(
                    f"\n[bold green]✅ {data.get('message', 'Añadido')}[/bold green] (ID: {data['book']['id']})")
            elif response.status_code == 200:
                console.print(
                    f"\n[yellow]⚠️ {data.get('message', 'Ya existe')}[/yellow]")
            else:
                console.print(
                    f"\n[bold red]❌ Error: {data.get('error', 'Desconocido')}[/bold red]")

        except Exception as e:
            console.print(
                f"\n[bold red]❌ Error de conexión al servidor: {e}[/bold red]")

    # ---------------------------------------------------------
    # OPCIÓN 3: INGRESO 100% MANUAL (Polimorfismo en acción)
    # ---------------------------------------------------------
    elif choice == "3":
        console.print(
            "\n[bold magenta]✍️  MODO DE INGRESO MANUAL[/bold magenta]")

        # Datos base
        title = Prompt.ask("Título del libro")
        # El autor ahora es opcional en la BD, así que permitimos dejarlo en blanco
        author_name = Prompt.ask(
            "Autor [dim](Deja en blanco si es desconocido)[/dim]", default="")

        console.print("\n[cyan]Formato del libro:[/cyan]")
        console.print("1. NOVEL (Novela estándar)")
        console.print("2. MANGA (Manga o Cómic)")
        console.print("3. ANTHOLOGY (Antología de cuentos)")
        fmt_choice = Prompt.ask("Elige el formato", choices=[
                                "1", "2", "3"], default="1")

        format_map = {"1": "NOVEL", "2": "MANGA", "3": "ANTHOLOGY"}
        format_type = format_map[fmt_choice]

        # 🚀 APROVECHANDO EL POLIMORFISMO (JSONB)
        details = {}
        if format_type == "MANGA":
            tomos = Prompt.ask(
                "¿Cuántos tomos tiene en total esta obra?", default="Desconocido")
            details["tomos_totales"] = tomos
            details["tomos_obtenidos"] = Prompt.ask(
                "¿Qué tomos tienes actualmente? (Ej: 1,2,3)", default="1")

        elif format_type == "ANTHOLOGY":
            cuentos = Prompt.ask(
                "Nombra algunos cuentos incluidos (separados por coma)")
            details["lista_cuentos"] = [c.strip()
                                        for c in cuentos.split(",") if c.strip()]

        # Construimos el diccionario de datos para enviar a Django
        payload = {
            "title": title,
            "format_type": format_type,
            "details": details,
            "is_read": Confirm.ask("¿Ya leíste este libro?"),
        }

        # Manejamos el autor como un diccionario anidado si el usuario lo ingresó
        if author_name.strip():
            payload["author_input"] = author_name.strip()

        try:
            # Enviamos el POST al endpoint CRUD normal
            response = httpx.post(API_LIBRARY, json=payload)
            if response.status_code == 201:
                console.print(
                    f"\n[bold green]✅ ¡Obra registrada magistralmente en tu biblioteca![/bold green]")
            else:
                console.print(
                    f"\n[bold red]❌ Error al guardar: {response.text}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")


@book_app.command(name="delete")
def delete_book(book_id: int):
    """Elimina un libro de la biblioteca mediante la API."""

    # 🛡️ BARRERA UX
    if not Confirm.ask(f"¿Estás seguro de que deseas eliminar permanentemente el libro #{book_id}?"):
        console.print("\n[yellow]Operación cancelada.[/yellow]\n")
        return

    try:
        response = httpx.delete(f"{API_LIBRARY}{book_id}/")
        if response.status_code == 204:
            console.print(
                f"\n[bold green]✅ Libro #{book_id} eliminado correctamente del servidor.[/bold green]\n")
        else:
            console.print(
                f"\n[bold red]❌ No se pudo eliminar. ¿Existe el ID {book_id}?[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")


@book_app.command(name="details")
def book_details(book_id: int = typer.Argument(..., help="ID del libro")):
    """Muestra TODO el perfil del libro: metadatos, estado y descripción en un formato inmersivo."""
    try:
        response = httpx.get(f"{API_LIBRARY}{book_id}/")
        if response.status_code == 404:
            console.print(
                f"[bold red]❌ Libro #{book_id} no encontrado en la biblioteca.[/bold red]")
            return

        book = response.json()

        # --- 1. LA CABECERA (Header) ---
        title_str = book.get('title', 'Sin Título').upper()
        title_text = Text(title_str, style="bold cyan", justify="center")

        if book.get('subtitle'):
            title_text.append(f"\n{book.get('subtitle')}", style="italic dim")

        author = book.get('author_name')
        if author:
            title_text.append(f"\n✎  {author}", style="bold yellow")

        # 🚀 COMPRESIÓN: padding vertical a 0
        header_panel = Panel(title_text, box=box.HEAVY,
                             border_style="cyan", padding=(0, 4))

        # --- 2. COLUMNA IZQUIERDA: Ficha Técnica y Estado ---
        tech_text = Text(justify="center")
        tech_text.append(f"❖ Editorial: ", style="bold white")
        tech_text.append(f"{book.get('publisher') or '-'}\n", style="yellow")
        tech_text.append(f"◈ Formato: ", style="bold white")
        tech_text.append(
            f"{book.get('format_type') or '-'}\n", style="magenta")
        tech_text.append(f"◷ Publicación: ", style="bold white")
        tech_text.append(f"{book.get('publish_date') or '-'}\n", style="green")

        # 🚀 COMPRESIÓN: Quitamos el \n extra que había aquí
        tech_text.append(f"▤ Páginas: ", style="bold white")
        tech_text.append(f"{book.get('page_count') or '-'}\n", style="cyan")

        tech_text.append("► Estado Físico ◄\n", style="bold underline white")
        tech_text.append(
            f"  ✔ Leído: {'Sí' if book.get('is_read') else 'No'}\n")

        if book.get('is_loaned'):
            tech_text.append("  ⌖ Ubicación: ", style="bold")
            tech_text.append("Prestado", style="bold red")
        else:
            tech_text.append("  ⌖ Ubicación: ", style="bold")
            tech_text.append("En Estantería", style="bold green")

        # 🚀 COMPRESIÓN: padding vertical a 0
        tech_panel = Panel(
            tech_text, title="[bold cyan]Ficha Técnica[/bold cyan]", border_style="cyan", padding=(0, 2))

        # --- 3. COLUMNA DERECHA: Detalles y Sinopsis ---
        details = book.get('details', {})
        details_panel = None
        if details:
            det_text = Text(justify="center")
            for key, value in details.items():
                clean_key = key.replace("_", " ").title()
                if isinstance(value, list):
                    value = ", ".join(value)
                det_text.append(f"▪ {clean_key}: ", style="bold white")
                det_text.append(f"{value}\n", style="green")

            details_panel = Panel(
                det_text, title="[bold magenta]Detalles[/bold magenta]", border_style="magenta", padding=(0, 2))

        desc = book.get('description')
        synopsis_panel = None
        if desc:
            # 🚀 COMPRESIÓN: Reducimos a 350 caracteres máximos para no estirar la columna
            if len(desc) > 350:
                desc = desc[:350] + "..."
            synopsis_panel = Panel(Text(desc, justify="center", style="dim"),
                                   title="[bold yellow]Sinopsis[/bold yellow]", border_style="yellow", padding=(0, 2))

        # --- 4. EL ENSAMBLAJE FINAL ---

        # Apilamos detalles arriba y sinopsis abajo en el mismo bloque derecho
        right_items = []
        if details_panel:
            right_items.append(details_panel)
        if synopsis_panel:
            right_items.append(synopsis_panel)

        if right_items:
            right_column = Group(*right_items)
            middle_section = Columns([tech_panel, right_column], equal=True)
        else:
            middle_section = tech_panel

        render_group = Group(header_panel, middle_section)

        # 🚀 COMPRESIÓN: Eliminamos los saltos de línea (console.print()) antes y después
        console.print(Align.center(render_group, width=90))

    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")


@book_app.command(name="edit")
def edit_book(book_id: int = typer.Argument(..., help="ID del libro a editar")):
    """Modifica rápidamente el estado de lectura, formato o añade metadatos polimórficos a un libro existente."""
    try:
        # 1. Obtenemos el libro actual
        response = httpx.get(f"{API_LIBRARY}{book_id}/")
        if response.status_code == 404:
            console.print(
                f"[bold red]❌ Libro #{book_id} no encontrado.[/bold red]")
            return

        book = response.json()
        console.print(
            f"\n✏️  [bold yellow]Editando: {book.get('title')}[/bold yellow]")
        console.print(
            "[dim]Presiona ENTER para mantener el valor actual.[/dim]\n")

        # 2. Preparamos el payload con los datos existentes
        payload = {}

        # Editamos el estado de lectura
        current_read = book.get('is_read', False)
        read_prompt = Prompt.ask(
            f"¿Ya está leído? [y/n] (Actual: {'y' if current_read else 'n'})", default="")
        if read_prompt.lower() in ['y', 'yes', 's', 'si']:
            payload['is_read'] = True
        elif read_prompt.lower() in ['n', 'no']:
            payload['is_read'] = False

        # Editamos el formato si OpenLibrary lo clasificó mal (ej. clasificó un manga como novela)
        current_format = book.get('format_type', 'NOVEL')
        console.print(f"\nFormato actual: [cyan]{current_format}[/cyan]")
        new_format = Prompt.ask(
            "Nuevo formato (1=NOVEL, 2=MANGA, 3=ANTHOLOGY, ENTER para saltar)", default="")

        if new_format == "1":
            payload['format_type'] = "NOVEL"
        elif new_format == "2":
            payload['format_type'] = "MANGA"
        elif new_format == "3":
            payload['format_type'] = "ANTHOLOGY"

        # 3. Lógica para inyectar detalles (Polimorfismo Retroactivo)
        # Si cambiamos el formato a MANGA, o si ya era MANGA y queremos actualizar los tomos
        final_format = payload.get('format_type', current_format)

        if final_format == "MANGA":
            if Confirm.ask("\n¿Deseas actualizar los datos de los tomos?"):
                details = book.get('details', {})
                tomos_totales = Prompt.ask("Tomos totales", default=str(
                    details.get('tomos_totales', '')))
                tomos_obtenidos = Prompt.ask("Tomos en tu colección (ej. 1,2,3)", default=str(
                    details.get('tomos_obtenidos', '')))

                details['tomos_totales'] = tomos_totales
                details['tomos_obtenidos'] = tomos_obtenidos
                payload['details'] = details

        elif final_format == "ANTHOLOGY":
            if Confirm.ask("\n¿Deseas actualizar la lista de cuentos?"):
                details = book.get('details', {})
                current_cuentos = ", ".join(details.get('lista_cuentos', []))
                cuentos = Prompt.ask(
                    "Nombra los cuentos (separados por coma)", default=current_cuentos)

                details["lista_cuentos"] = [c.strip()
                                            for c in cuentos.split(",") if c.strip()]
                payload['details'] = details

        # 4. Enviamos la actualización usando el método PATCH (modificación parcial)
        if payload:
            update_response = httpx.patch(
                f"{API_LIBRARY}{book_id}/", json=payload)
            if update_response.status_code == 200:
                console.print(
                    "\n[bold green]✅ Libro actualizado correctamente en la base de datos.[/bold green]\n")
            else:
                console.print(
                    f"\n[bold red]❌ Error al actualizar: {update_response.text}[/bold red]\n")
        else:
            console.print("\n[yellow]No se realizaron cambios.[/yellow]\n")

    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")


@book_app.command(name="consolidate")
def consolidate_mangas():
    """Escanea la biblioteca, agrupa tomos de mangas sueltos y los fusiona en sagas únicas."""
    console.print(
        "\n[bold cyan]🐉 INICIANDO MOTOR DE CONSOLIDACIÓN DE SAGAS 🐉[/bold cyan]\n")
    try:
        resp = httpx.get(API_LIBRARY)
        all_books = resp.json()

        # Diccionario: { "chainsaw man": [(book_dict, "1"), (book_dict, "2")] }
        sagas = {}

        # 1. Fase de Extracción: Agrupamos todos los tomos sueltos
        for book in all_books:
            base_title, tomo = parse_manga_title(book['title'])
            if tomo:
                base_key = base_title.lower()
                if base_key not in sagas:
                    sagas[base_key] = []
                sagas[base_key].append((book, tomo))

        fusion_count = 0

        # 2. Fase de Transformación y Carga (ETL)
        for base_key, tomos_detectados in sagas.items():
            # Buscamos si el usuario ya había creado manualmente la saga Master
            posibles_masters = [b for b in all_books if b['title'].lower(
            ) == base_key and b.get('format_type') == 'MANGA']

            if posibles_masters:
                master = posibles_masters[0]
                master_details = master.get('details', {})
                tomos_str = str(master_details.get('tomos_obtenidos', ''))
                tomos_lista = [t.strip()
                               for t in tomos_str.split(',') if t.strip()]
            elif len(tomos_detectados) > 1:
                # Si no hay master pero hay varios tomos, convertimos el primer tomo en el Master
                master_tuple = tomos_detectados.pop(0)
                master = master_tuple[0]
                tomos_lista = [master_tuple[1]]

                # Promovemos el registro en la API
                console.print(
                    f"[dim]Promoviendo '{master['title']}' a Master Saga...[/dim]")
                httpx.patch(
                    f"{API_LIBRARY}{master['id']}/", json={"title": base_key.title(), "format_type": "MANGA"})
                master['title'] = base_key.title()
                master_details = {}
            else:
                continue  # Es solo 1 tomo suelto y no hay master, lo ignoramos

            # Inyectamos los demás tomos en el master
            tomos_a_eliminar = []
            for t_tuple in tomos_detectados:
                tomo_book = t_tuple[0]
                tomo_num = t_tuple[1]
                if tomo_num not in tomos_lista:
                    tomos_lista.append(tomo_num)
                tomos_a_eliminar.append(tomo_book['id'])

            if not tomos_a_eliminar and not posibles_masters:
                continue

            # Actualizamos el Master con la nueva lista de tomos
            tomos_lista.sort(key=lambda x: int(x) if x.isdigit() else x)
            master_details['tomos_obtenidos'] = ", ".join(tomos_lista)
            httpx.patch(
                f"{API_LIBRARY}{master['id']}/", json={"details": master_details})

            # Eliminamos los registros huérfanos que ya fueron absorbidos
            for del_id in tomos_a_eliminar:
                httpx.delete(f"{API_LIBRARY}{del_id}/")

            console.print(
                f"✅ Saga [bold green]'{master['title']}'[/bold green] consolidada. Tomos actuales: {master_details['tomos_obtenidos']}")
            fusion_count += len(tomos_a_eliminar)

        if fusion_count == 0:
            console.print(
                "[yellow]No se encontraron tomos huérfanos. Tu biblioteca está optimizada.[/yellow]\n")
        else:
            console.print(
                f"\n[bold magenta]✨ Consolidación terminada. Se absorbieron {fusion_count} registros redundantes.[/bold magenta]\n")

    except Exception as e:
        console.print(f"[bold red]❌ Error de conexión: {e}[/bold red]")
