"""One command that answers "is anything broken?".

The project has a pile of assert-based scripts and no runner, so a human needs one command per
script and a mental note of which ones live inside the container. This is that runner, plus the
reachability checks the Transmisor made necessary.

No count is written here on purpose. The number lived in this docstring and went stale one
commit after it was written; it is the fifth prose count to drift in this project. Read
CHECKS_IN_CONTAINER — registering a script there is the only step.
"""
import os
import shutil
import subprocess
import sys

import httpx
import typer
from rich.console import Console
from rich.markup import escape

from cli.config import BASE_URL, project_root

console = Console()

# These import Django models, so they only run inside `web`.
#
# Module paths, not file paths, and `python -m`: run as `python tests/test_x.py`, Python puts
# `tests/` on sys.path instead of the project root and every one of these dies on
# `ModuleNotFoundError: No module named 'bunker_core'`. `-m` puts the CWD on sys.path, which is
# what django.setup() needs. The label is the exact thing to type to run one by hand.
CHECKS_IN_CONTAINER = (
    "tests.test_posada_skills",
    "tests.test_achievements",
    "tests.test_capture_dates",
    "tests.test_reading_progress",
    "tests.test_movil_estado",
    "tests.test_inbox_idempotente",
    "tests.test_insights",
    "tests.test_guild_contract",
    "tests.test_session_record",
    "tests.test_briefing",
    "tests.test_timeline",
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
    # Its assertions run in the browser: from here only its reachability is checkable. The
    # count that used to sit in this line said twelve and the page prints thirteen — the
    # sixth prose count to drift in this project, so it is not written down any more.
    if not _reachable("/movil/selftest/ (alcanzable; ábrelo en el móvil para correrlo)",
                      f"{BASE_URL}/movil/selftest/"):
        fallos += 1

    # Informational only: a machine that just runs the server has no SDK, and that is not a
    # failure. ANDROID_HOME is checked as a directory, not as a string, so a stale export from
    # a deleted SDK reads as absent instead of green.
    #
    # And `which` alone is not enough for the other half: cron and systemd run with a PATH that
    # carries no platform-tools — `bunker_crontab` resets it to /usr/local/bin:/usr/bin:/bin, and
    # `scripts/ronda_doze.sh` hardcodes the absolute adb path for exactly this reason. A `which`
    # miss is therefore not evidence that adb is absent; the SDK's own copy is the second look.
    console.print("\n[bold cyan]Android[/bold cyan]")
    sdk = os.environ.get("ANDROID_HOME", "")
    hay_sdk = os.path.isdir(sdk)
    hay_adb = bool(shutil.which("adb")) or (
        hay_sdk and os.path.isfile(os.path.join(sdk, "platform-tools", "adb")))
    falta = [nombre for nombre, ok in (("adb", hay_adb), ("ANDROID_HOME", hay_sdk)) if not ok]
    if falta:
        console.print(f"  [yellow]○[/yellow] sin {' ni '.join(falta)}: el APK se construye a mano")
    else:
        # escape(): Rich reads [...] as markup, so an unescaped path with brackets prints as
        # /opt//x — a green line showing the wrong value, which is worse than a red one.
        console.print(f"  [green]✓[/green] adb · ANDROID_HOME {escape(sdk)}")

    console.print("\n[bold cyan]Migraciones[/bold cyan]")
    if not _run("sin migraciones pendientes",
                ["docker", "compose", "exec", "-T", "web",
                 "python", "manage.py", "migrate", "--check"]):
        fallos += 1

    console.print("\n[bold cyan]Checks[/bold cyan]")
    for modulo in CHECKS_IN_CONTAINER:
        if not _run(modulo, ["docker", "compose", "exec", "-T", "web",
                             "python", "-m", modulo]):
            fallos += 1
    if not _run("tests.test_cli_imports",
                [sys.executable, "-m", "tests.test_cli_imports"]):
        fallos += 1

    if fallos:
        console.print(f"\n[bold red]{fallos} problema(s).[/bold red]\n")
    else:
        console.print("\n[bold green]Todo en orden.[/bold green]\n")
    raise typer.Exit(code=1 if fallos else 0)
