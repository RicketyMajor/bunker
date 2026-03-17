import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box

# Inicializamos el grupo y la consola
loan_app = typer.Typer(
    help="Manage book loans to friends.", no_args_is_help=True)
console = Console()


@loan_app.command(name="lend")
def lend_book():
    """Lend a book to a friend."""
    from catalog.models import Book, Friend, Loan

    console.print("\n[bold cyan]🤝 Lend a Book[/bold cyan]\n")

    book_id = typer.prompt("Enter the Book ID you want to lend", type=int)
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        console.print("[bold red]❌ Book not found.[/bold red]")
        return

    friend_name = Prompt.ask("Friend's Name")

    friend, _ = Friend.objects.get_or_create(name=friend_name.strip())
    Loan.objects.create(book=book, friend=friend)

    console.print(
        f"\n[bold green]✅ '{book.title}' has been lent to {friend.name}![/bold green]")
    console.print("[dim]They have 30 days to return it.[/dim]\n")


@loan_app.command(name="status")
def loan_status():
    """View all active loans and due dates."""
    from catalog.models import Loan
    from django.utils import timezone

    active_loans = Loan.objects.filter(returned=False).order_by('due_date')

    if not active_loans:
        console.print(
            "[bold green]No active loans. All your books are safely home![/bold green]")
        return

    table = Table(title="🤝 Active Loans", box=box.ROUNDED,
                  header_style="bold cyan")
    table.add_column("Loan ID", justify="right", style="cyan")
    table.add_column("Book", style="magenta")
    table.add_column("Friend", style="green")
    table.add_column("Due Date", justify="center")
    table.add_column("Status", justify="center")

    today = timezone.now().date()

    for loan in active_loans:
        if loan.due_date < today:
            status = "[bold red]OVERDUE![/bold red]"
            due_str = f"[bold red]{loan.due_date}[/bold red]"
        else:
            status = "[green]On time[/green]"
            due_str = str(loan.due_date)

        table.add_row(str(loan.id), loan.book.title,
                      loan.friend.name, due_str, status)

    console.print(table)
    print("\n")


@loan_app.command(name="return")
def return_book(loan_id: int = typer.Argument(..., help="The ID of the loan to mark as returned")):
    """Mark a lent book as returned."""
    from catalog.models import Loan

    try:
        loan = Loan.objects.get(id=loan_id)
        if loan.returned:
            console.print(
                "[bold yellow]This book was already returned.[/bold yellow]")
            return

        loan.returned = True
        loan.save()
        console.print(
            f"[bold green]✅ Awesome! '{loan.book.title}' has been returned by {loan.friend.name}.[/bold green]")

    except Loan.DoesNotExist:
        console.print("[bold red]❌ Loan ID not found.[/bold red]")
