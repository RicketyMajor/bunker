import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

console = Console()
# Creamos un typer que luego uniremos en el principal
app = typer.Typer(help="View and search your library.", no_args_is_help=True)


@app.command(name="list")
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


@app.command(name="details")
def show_details(book_id: int = typer.Argument(..., help="The ID of the book/series to inspect")):
    """Shows the complete Technical Data Sheet of a book."""
    from catalog.models import Book

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print("[bold red]❌ Book not found.[/bold red]")
        return

    active_loan = book.loan_set.filter(returned=False).first()
    if active_loan:
        status_display = f"[bold yellow]Lent to {active_loan.friend.name}[/bold yellow]"
    else:
        status_display = "[dim green]In Library[/dim green]"

    genres = [g.name for g in book.genres.all()]
    genres_str = ", ".join(genres) if genres else "Not specified"

    content = f"[bold magenta]Title:[/bold magenta] {book.title}\n"

    if book.subtitle:
        content += f"[bold italic cyan]Subtitle:[/bold italic cyan] {book.subtitle}\n"

    content += f"[bold green]Author:[/bold green] {book.author.name if book.author else 'Unknown'}\n"
    content += f"[bold yellow]Publisher:[/bold yellow] {book.publisher or 'Not specified'}\n"

    content += f"[bold blue]Format:[/bold blue] {book.get_format_type_display()}\n"
    content += f"[bold blue]Genres:[/bold blue] {genres_str}\n"
    content += f"[bold cyan]Status:[/bold cyan] {status_display}\n"

    if book.publish_date:
        content += f"[bold]Published:[/bold] {book.publish_date}\n"
    if book.page_count:
        content += f"[bold]Pages:[/bold] {book.page_count} pages\n"

    if book.is_series:
        content += f"\n[bold cyan]--- Series Info ---[/bold cyan]\n"
        content += f"[bold]Total Volumes Released:[/bold] {book.total_volumes or 'Unknown'}\n"
        content += f"[bold]Volumes Owned:[/bold] {book.owned_volumes or 'None'}\n"

    if book.format_type == 'ANTHOLOGY' and book.anthology_stories:
        content += f"\n[bold cyan]--- Anthology Stories ---[/bold cyan]\n"
        for idx, story in enumerate(book.anthology_stories, 1):
            content += f"[dim]{idx}. {story}[/dim]\n"

    if book.description:
        content += f"\n[bold blue]--- Description ---[/bold blue]\n[dim]{book.description}[/dim]\n"

    if book.cover_url:
        content += f"\n[bold magenta]Cover:[/bold magenta] [link={book.cover_url}]Ctrl+Click here to view cover image[/link]\n"

    console.print(Panel(
        content,
        title="📚 Ficha Técnica",
        expand=False,
        border_style="cyan",
        padding=(1, 2)
    ))
    print("\n")
