import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from cli.api import fetch_book_by_isbn

console = Console()
app = typer.Typer(help="Add, edit, or delete books.", no_args_is_help=True)


@app.command(name="add")
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

    # --- CORRECCIÓN DEL ERROR ---
    # Preguntamos por los géneros y si está leído ANTES de crear el libro
    genres_input = Prompt.ask("Genres (comma-separated)")
    is_read = Confirm.ask("Have you read this completely?")
    # ----------------------------

    author, _ = Author.objects.get_or_create(
        name=author_name.strip()) if author_name else (None, False)

    book = Book.objects.create(
        title=title.strip(), author=author, publisher=publisher,
        format_type=format_type, is_read=is_read,
        is_series=is_series, total_volumes=total_volumes,
        owned_volumes=owned_volumes, anthology_stories=anthology_stories
    )

    if genres_input:
        for g_name in [g.strip() for g in genres_input.split(',') if g.strip()]:
            genre, _ = Genre.objects.get_or_create(name=g_name)
            book.genres.add(genre)

    console.print(
        f"\n[bold green]✅ Successfully added '{book.title}'![/bold green]\n")


@app.command(name="edit")
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


@app.command(name="fetch")
def fetch_book(isbn: str = typer.Argument(..., help="The ISBN of the book to fetch")):
    """Fetch book details from internet API using ISBN."""
    from catalog.models import Book, Author, Genre

    console.print(
        f"\n[bold cyan]🔍 Searching internet for ISBN: {isbn}...[/bold cyan]")

    book_data = fetch_book_by_isbn(isbn)

    if not book_data:
        console.print(
            "[bold red]❌ Book not found or network error.[/bold red]")
        console.print(
            "[dim]Try adding it manually using 'python -m cli.main book add'[/dim]\n")
        return

    preview = (
        f"[bold magenta]Title:[/bold magenta] {book_data['title']}\n"
        f"[bold green]Author:[/bold green] {book_data['author']}\n"
        f"[bold yellow]Publisher:[/bold yellow] {book_data['publisher'] or 'N/A'}\n"
        f"[bold blue]Genres:[/bold blue] {', '.join(book_data['categories']) or 'N/A'}"
    )
    console.print(Panel(preview, title="📖 Book Found!",
                  expand=False, border_style="cyan"))

    if not Confirm.ask("Do you want to save this book to your library?"):
        console.print("[yellow]Operation cancelled.[/yellow]\n")
        return

    format_type = Prompt.ask(
        "Format", choices=["NOVEL", "COMIC", "MANGA", "ANTHOLOGY"], default="NOVEL")

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

    is_read = Confirm.ask("Have you read this book?")

    author, _ = Author.objects.get_or_create(name=book_data['author'].strip())

    book = Book.objects.create(
        title=book_data['title'].strip(), subtitle=book_data['subtitle'],
        author=author, publisher=book_data['publisher'],
        format_type=format_type, is_read=is_read,
        page_count=book_data['page_count'] or None,
        publish_date=book_data['publish_date'],
        cover_url=book_data['cover_url'], description=book_data['description'],
        anthology_stories=anthology_stories
    )

    for category in book_data['categories']:
        clean_category = category.split('/')[-1].strip()
        genre, _ = Genre.objects.get_or_create(name=clean_category)
        book.genres.add(genre)

    console.print(
        f"\n[bold green]✅ Successfully auto-imported '{book.title}'![/bold green]\n")


@app.command(name="delete")
def delete_book(book_id: int = typer.Argument(..., help="The ID of the book to delete")):
    """Permanently delete a book from your library."""
    from catalog.models import Book

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print("[bold red]❌ Book not found.[/bold red]")
        return

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
