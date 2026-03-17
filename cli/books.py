import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box
from rich.panel import Panel  # Para dibujar un cuadro bonito con el resumen
from cli.api import fetch_book_by_isbn  # Importamos nuestra nueva función

# Inicializamos el grupo de comandos y la consola para este archivo
book_app = typer.Typer(
    help="Manage your books, comics, and mangas.", no_args_is_help=True)
console = Console()


@book_app.command(name="list")
def list_books(
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search by title"),
    author: Optional[str] = typer.Option(
        None, "--author", "-a", help="Filter by author name"),
    publisher: Optional[str] = typer.Option(
        None, "--publisher", "-p", help="Filter by publisher"),
    genre: Optional[str] = typer.Option(
        None, "--genre", "-g", help="Filter by genre"),
    unread: bool = typer.Option(
        False, "--unread", "-u", help="Show only unread books"),
):
    """Fetches, filters, and displays books in the library."""
    from catalog.models import Book

    query = Book.objects.all()

    if search:
        query = query.filter(title__icontains=search)
    if author:
        query = query.filter(author__name__icontains=author)
    if publisher:
        query = query.filter(publisher__icontains=publisher)
    if genre:
        query = query.filter(genres__name__icontains=genre)
    if unread:
        query = query.filter(is_read=False)

    books = query.order_by('title').distinct()

    if not books:
        console.print(
            "[bold yellow]No books found matching your criteria.[/bold yellow]")
        return

    table = Table(
        title="📚 [bold gold1]My Personal Library[/bold gold1]",
        title_justify="center",
        box=box.ROUNDED,
        caption=f"[dim italic]Total books found: {books.count()}[/dim italic]",
        header_style="bold cyan"
    )

    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Title", style="magenta")
    table.add_column("Author", style="green")
    table.add_column("Publisher", style="yellow")
    table.add_column("Format", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Read", justify="center")

    for book in books:
        author_name = book.author.name if book.author else "Unknown"
        is_read_status = "[bold green]✅[/bold green]" if book.is_read else "[bold red]❌[/bold red]"

        # Construcción visual del título
        title_display = f"[bold]{book.title}[/bold]"
        if book.is_series:
            title_display += f"\n[dim cyan]↳ Serie (Vols: {book.owned_volumes or 'N/A'})[/dim cyan]"
        elif book.format_type == 'ANTHOLOGY' and book.anthology_stories:
            title_display += f"\n[dim cyan]↳ Antología ({len(book.anthology_stories)} cuentos)[/dim cyan]"
        active_loan = book.loan_set.filter(returned=False).first()
        if active_loan:
            status_display = f"[bold yellow]Lent to: {active_loan.friend.name}[/bold yellow]"
        else:
            status_display = "[dim green]In Library[/dim green]"

        table.add_row(
            str(book.id), title_display, author_name,
            book.publisher or "-", book.get_format_type_display(),
            status_display, is_read_status
        )

    console.print(table)
    print("\n")


@book_app.command(name="add")
def add_book():
    """Interactive prompt to add a new book."""
    from catalog.models import Book, Author, Genre

    console.print(
        "\n[bold cyan]📖 Let's add a new book to your library![/bold cyan]\n")

    title = Prompt.ask("Title")
    author_name = Prompt.ask("Author")
    publisher = Prompt.ask("Publisher (Editorial)", default="")

    console.print(
        "[dim]Available formats: NOVEL, COMIC, MANGA, ANTHOLOGY[/dim]")
    format_type = Prompt.ask(
        "Format", choices=["NOVEL", "COMIC", "MANGA", "ANTHOLOGY"], default="NOVEL")

    is_series = False
    total_volumes = None
    owned_volumes = ""

    if format_type in ["COMIC", "MANGA"]:
        is_series = Confirm.ask("Is this a multi-volume series?")
        if is_series:
            total_volumes = IntPrompt.ask(
                "How many total volumes exist currently?", default=0)
            owned_volumes = Prompt.ask(
                "Which volumes do you own? (e.g., 1, 2, 3 or 1-5)")

    author, _ = Author.objects.get_or_create(
        name=author_name.strip()) if author_name else (None, False)

    # --- NUEVA LÓGICA DE ANTOLOGÍAS ---
    anthology_stories = []
    if format_type == "ANTHOLOGY":
        num_stories = IntPrompt.ask(
            "How many stories/tales are in this anthology?", default=0)
        if num_stories > 0:
            console.print("[dim]Please enter the title of each story:[/dim]")
            for i in range(num_stories):
                story_title = Prompt.ask(f"  Story {i+1}")
                if story_title.strip():
                    anthology_stories.append(story_title.strip())

    # Y en el Book.objects.create(), asegúrate de añadir el campo:
    # anthology_stories=anthology_stories

    book = Book.objects.create(
        title=title.strip(), author=author, publisher=publisher,
        format_type=format_type, is_read=is_read,
        is_series=is_series, total_volumes=total_volumes, owned_volumes=owned_volumes, anthology_stories=anthology_stories
    )

    genres_input = Prompt.ask("Genres (comma-separated)")

    if genres_input:
        for g_name in [g.strip() for g in genres_input.split(',') if g.strip()]:
            genre, _ = Genre.objects.get_or_create(name=g_name)
            book.genres.add(genre)

    is_read = Confirm.ask("Have you read this completely?")
    console.print(
        f"\n[bold green]✅ Successfully added '{book.title}'![/bold green]\n")


@book_app.command(name="edit")
def edit_book(book_id: int = typer.Argument(..., help="The ID of the book to edit")):
    """Edit an existing book's details."""
    from catalog.models import Book, Author

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print(
            f"[bold red]❌ Book with ID {book_id} not found.[/bold red]")
        return

    console.print(f"\n[bold cyan]✏️  Editing: {book.title}[/bold cyan]\n")

    new_title = Prompt.ask("Title", default=book.title)
    current_author = book.author.name if book.author else ""
    new_author = Prompt.ask("Author", default=current_author)

    book.title = new_title
    if new_author != current_author:
        author, _ = Author.objects.get_or_create(name=new_author.strip())
        book.author = author

    book.save()
    console.print(
        f"\n[bold green]✅ Book ID {book.id} successfully updated![/bold green]\n")


@book_app.command(name="details")
def show_details(book_id: int = typer.Argument(..., help="The ID of the book/series to inspect")):
    """Shows the complete Technical Data Sheet of a book."""
    from catalog.models import Book

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print("[bold red]❌ Book not found.[/bold red]")
        return

    # 1. Lógica del estado (Préstamo)
    active_loan = book.loan_set.filter(returned=False).first()
    if active_loan:
        status_display = f"[bold yellow]Lent to {active_loan.friend.name}[/bold yellow]"
    else:
        status_display = "[dim green]In Library[/dim green]"

    # 2. Obtener los géneros (ManyToMany)
    genres = [g.name for g in book.genres.all()]
    genres_str = ", ".join(genres) if genres else "Not specified"

    # 3. Construimos el texto interno de la ficha técnica
    content = f"[bold magenta]Title:[/bold magenta] {book.title}\n"

    if book.subtitle:
        content += f"[bold italic cyan]Subtitle:[/bold italic cyan] {book.subtitle}\n"

    content += f"[bold green]Author:[/bold green] {book.author.name if book.author else 'Unknown'}\n"
    content += f"[bold yellow]Publisher:[/bold yellow] {book.publisher or 'Not specified'}\n"

    # --- LA NUEVA INFORMACIÓN AGREGADA ---
    content += f"[bold blue]Format:[/bold blue] {book.get_format_type_display()}\n"
    content += f"[bold blue]Genres:[/bold blue] {genres_str}\n"
    content += f"[bold cyan]Status:[/bold cyan] {status_display}\n"
    # -------------------------------------

    if book.publish_date:
        content += f"[bold]Published:[/bold] {book.publish_date}\n"
    if book.page_count:
        content += f"[bold]Pages:[/bold] {book.page_count} pages\n"

   # Información si es cómic/manga
    if book.is_series:
        content += f"\n[bold cyan]--- Series Info ---[/bold cyan]\n"
        content += f"[bold]Total Volumes Released:[/bold] {book.total_volumes or 'Unknown'}\n"
        content += f"[bold]Volumes Owned:[/bold] {book.owned_volumes or 'None'}\n"

    # Información si es antología
    if book.format_type == 'ANTHOLOGY' and book.anthology_stories:
        content += f"\n[bold cyan]--- Anthology Stories ---[/bold cyan]\n"
        for idx, story in enumerate(book.anthology_stories, 1):
            content += f"[dim]{idx}. {story}[/dim]\n"

    # Agregamos la descripción/sinopsis si existe
    if book.description:
        content += f"\n[bold blue]--- Description ---[/bold blue]\n[dim]{book.description}[/dim]\n"

    # La terminal de WSL2/Windows Terminal soporta hipervínculos con Rich
    if book.cover_url:
        content += f"\n[bold magenta]Cover:[/bold magenta] [link={book.cover_url}]Ctrl+Click here to view cover image[/link]\n"

    # Renderizamos el panel final
    console.print(Panel(
        content,
        title="📚 Ficha Técnica",
        expand=False,
        border_style="cyan",
        padding=(1, 2)
    ))
    print("\n")


@book_app.command(name="fetch")
def fetch_book(isbn: str = typer.Argument(..., help="The ISBN of the book to fetch")):
    """Fetch book details from Google Books API using ISBN."""
    from catalog.models import Book, Author, Genre

    console.print(
        f"\n[bold cyan]🔍 Searching internet for ISBN: {isbn}...[/bold cyan]")

    # Llamamos a nuestro nuevo módulo API
    book_data = fetch_book_by_isbn(isbn)

    if not book_data:
        console.print(
            "[bold red]❌ Book not found or network error.[/bold red]")
        console.print(
            "[dim]Try adding it manually using 'python -m cli.main book add'[/dim]\n")
        return

    # Mostramos un panel con la información encontrada
    preview = (
        f"[bold magenta]Title:[/bold magenta] {book_data['title']}\n"
        f"[bold green]Author:[/bold green] {book_data['author']}\n"
        f"[bold yellow]Publisher:[/bold yellow] {book_data['publisher'] or 'N/A'}\n"
        f"[bold blue]Genres:[/bold blue] {', '.join(book_data['categories']) or 'N/A'}"
    )
    console.print(Panel(preview, title="📖 Book Found!",
                  expand=False, border_style="cyan"))

    # Preguntamos si queremos guardarlo
    if not Confirm.ask("Do you want to save this book to your library?"):
        console.print("[yellow]Operation cancelled.[/yellow]\n")
        return

    # Preguntamos cosas que la API no sabe (si lo leíste y el formato)
    format_type = Prompt.ask(
        "Format", choices=["NOVEL", "COMIC", "MANGA", "ANTHOLOGY"], default="NOVEL")

    # Guardamos en la base de datos con los nuevos campos
    author, _ = Author.objects.get_or_create(name=book_data['author'].strip())

    # --- NUEVA LÓGICA DE ANTOLOGÍAS ---
    anthology_stories = []
    if format_type == "ANTHOLOGY":
        num_stories = IntPrompt.ask(
            "How many stories/tales are in this anthology?", default=0)
        if num_stories > 0:
            console.print("[dim]Please enter the title of each story:[/dim]")
            for i in range(num_stories):
                story_title = Prompt.ask(f"  Story {i+1}")
                if story_title.strip():
                    anthology_stories.append(story_title.strip())

    # Y en el Book.objects.create(), asegúrate de añadir el campo:
    # anthology_stories=anthology_stories

    book = Book.objects.create(
        title=book_data['title'].strip(),
        subtitle=book_data['subtitle'],
        author=author,
        publisher=book_data['publisher'],
        format_type=format_type,
        is_read=is_read,
        page_count=book_data['page_count'] or None,
        publish_date=book_data['publish_date'],
        cover_url=book_data['cover_url'],
        description=book_data['description'],
        anthology_stories=anthology_stories
    )

    # Procesamos los géneros que trajo la API
    for category in book_data['categories']:
        # A veces la API trae géneros largos como "Fiction / Science Fiction / Cyberpunk"
        # Nos quedamos con la última parte para que sea más limpio
        clean_category = category.split('/')[-1].strip()
        genre, _ = Genre.objects.get_or_create(name=clean_category)
        book.genres.add(genre)

    is_read = Confirm.ask("Have you read this book?")

    console.print(
        f"\n[bold green]✅ Successfully auto-imported '{book.title}'![/bold green]\n")


@book_app.command(name="delete")
def delete_book(book_id: int = typer.Argument(..., help="The ID of the book to delete")):
    """Permanently delete a book from your library."""
    from catalog.models import Book

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print("[bold red]❌ Book not found.[/bold red]")
        return

    # Imprimimos una advertencia clara
    console.print(
        f"\n[bold red]⚠️  WARNING: You are about to delete '{book.title}'.[/bold red]")
    console.print(
        "[dim]This action cannot be undone and will erase all loan records for this book.[/dim]\n")

    if Confirm.ask("Are you absolutely sure you want to delete this book?"):
        book.delete()
        console.print(
            "\n[bold green]✅ Book permanently deleted from your library.[/bold green]\n")
    else:
        console.print(
            "\n[yellow]Operation cancelled. Your book is safe.[/yellow]\n")
