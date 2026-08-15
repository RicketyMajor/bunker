"""One command that answers "is anything broken?".

The project has a pile of assert-based scripts and no runner, so a human needs one command per
script and a mental note of which ones live inside the container. This is that runner, plus the
reachability checks the Transmisor made necessary.

No count is written here on purpose. The number lived in this docstring and went stale one
commit after it was written; it is the fifth prose count to drift in this project. Read
CHECKS_IN_CONTAINER — registering a script there is the only step.
"""
import subprocess
import sys

import httpx
import typer
from rich.console import Console

from cli.config import BASE_URL, project_root

console = Console()

# These import Django models, so they only run inside `web`.
CHECKS_IN_CONTAINER = (
    "test_posada_skills.py",
    "test_achievements.py",
    "test_capture_dates.py",
    "test_reading_progress.py",
    "test_movil_estado.py",
    "test_inbox_idempotente.py",
    "test_insights.py",
    "test_guild_contract.py",
)


def _run(label, argv):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=180,
                              cwd=project_root)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        console.print(f"  [red]✗[/red] {label}: {exc}")
        return False
    ok = proc.returncode == 0
    console.print(f"  [green]✓[/green] {label}" if ok else f"  [red]✗[/red] {label}")
    if not ok:
        console.print(f"[dim]{(proc.stdout + proc.stderr).strip()[-500:]}[/dim]")
    return ok


def _reachable(label, url, timeout=5):
    try:
        r = httpx.get(url, timeout=timeout)
    except Exception as exc:
        console.print(f"  [red]✗[/red] {label} inalcanzable: {exc}")
        return False
    ok = r.status_code == 200
    console.print(f"  [green]✓[/green] {label} → {r.status_code}" if ok
                  else f"  [red]✗[/red] {label} → {r.status_code}")
    return ok


def doctor():
    """Revisa que el Búnker esté sano: API, migraciones, checks y alcance del Transmisor."""
    fallos = 0

    console.print("\n[bold cyan]API[/bold cyan]")
    if not _reachable("/api/health/", f"{BASE_URL}/api/health/"):
        fallos += 1

    console.print("\n[bold cyan]Transmisor[/bold cyan]")
    if not _reachable("/movil/", f"{BASE_URL}/movil/"):
        fallos += 1
    # Its twelve assertions run in the browser: from here only its reachability is checkable.
    if not _reachable("/movil/selftest/ (alcanzable; ábrelo en el móvil para correrlo)",
                      f"{BASE_URL}/movil/selftest/"):
        fallos += 1

    console.print("\n[bold cyan]Migraciones[/bold cyan]")
    if not _run("sin migraciones pendientes",
                ["docker", "compose", "exec", "-T", "web",
                 "python", "manage.py", "migrate", "--check"]):
        fallos += 1

    console.print("\n[bold cyan]Checks[/bold cyan]")
    for script in CHECKS_IN_CONTAINER:
        if not _run(script, ["docker", "compose", "exec", "-T", "web", "python", script]):
            fallos += 1
    if not _run("test_cli_imports.py", [sys.executable, "test_cli_imports.py"]):
        fallos += 1

    if fallos:
        console.print(f"\n[bold red]{fallos} problema(s).[/bold red]\n")
    else:
        console.print("\n[bold green]Todo en orden.[/bold green]\n")
    raise typer.Exit(code=1 if fallos else 0)
