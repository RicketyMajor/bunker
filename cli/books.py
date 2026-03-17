import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

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

        title_display = f"[bold]{book.title}[/bold]"
        if book.is_series:
            title_display += f"\n[dim cyan]↳ Serie (Vols: {book.owned_volumes or 'N/A'})[/dim cyan]"

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

    genres_input = Prompt.ask("Genres (comma-separated)")
    is_read = Confirm.ask("Have you read this completely?")

    author, _ = Author.objects.get_or_create(
        name=author_name.strip()) if author_name else (None, False)

    book = Book.objects.create(
        title=title.strip(), author=author, publisher=publisher,
        format_type=format_type, is_read=is_read,
        is_series=is_series, total_volumes=total_volumes, owned_volumes=owned_volumes
    )

    if genres_input:
        for g_name in [g.strip() for g in genres_input.split(',') if g.strip()]:
            genre, _ = Genre.objects.get_or_create(name=g_name)
            book.genres.add(genre)

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
    """Shows specific details and owned volumes of a comic/manga."""
    from catalog.models import Book

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print("[bold red]❌ Book not found.[/bold red]")
        return

    console.print(f"\n[bold magenta]Title:[/bold magenta] {book.title}")
    console.print(
        f"[bold magenta]Author:[/bold magenta] {book.author.name if book.author else 'Unknown'}")
    console.print(
        f"[bold magenta]Publisher:[/bold magenta] {book.publisher or 'Not specified'}")

    if book.is_series:
        console.print(
            f"[bold cyan]Total Volumes Released:[/bold cyan] {book.total_volumes or 'Unknown'}")
        console.print(
            f"[bold green]Volumes Owned:[/bold green] {book.owned_volumes or 'None'}")
    print("\n")
