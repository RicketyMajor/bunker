"""One command that answers "is anything broken?".

The project has a pile of assert-based scripts and no runner, so a human needs one command per
script and a mental note of which ones live inside the container. This is that runner, plus the
reachability checks the Transmisor made necessary.

No count is written here on purpose. The number lived in this docstring and went stale one
commit after it was written; it is the fifth prose count to drift in this project. Read
CHECKS_IN_CONTAINER — registering a script there is the only step. A check that must run on
the HOST — because it needs the repo tree, `npx` or the venv rather than Django models —
goes inline further down instead, beside `tests.test_cli_imports` and `tests.test_bundle`.
"""
import os
import pathlib
import shutil
import subprocess
import sys

from cli import sede
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
    "tests.test_capture_dates",
    "tests.test_reading_progress",
    "tests.test_movil_estado",
    "tests.test_inbox_idempotente",
    "tests.test_insights",
    "tests.test_briefing",
    "tests.test_dedup",
    "tests.test_fuentes",
    "tests.test_timeline",
    "tests.test_backup_apps",
    "tests.test_panel",
    "tests.test_secretos",
    # Recorre el RESOLVEDOR de Django, no una lista a mano: 50 rutas concretas bajo /api/, y las
    # 49 que no estan en la allowlist tienen que responder 403 sin la cabecera.
    "tests.test_auth_api",
)


def _run(label, argv, stdin_file=None, timeout=180):
    """`stdin_file` feeds a script to an interpreter that cannot see it on disk — the scraper
    containers bind-mount only `./scraper:/app`, so `tests/` never reaches them.

    `timeout` is per-check because one of them is not like the others: everything here answers in
    seconds, but a Gradle daemon that has just died recompiles the whole module first."""
    try:
        entrada = stdin_file.read_text(encoding="utf-8") if stdin_file else None
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              cwd=project_root, input=entrada)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        console.print(f"  [red]✗[/red] {label}: {exc}")
        return False
    ok = proc.returncode == 0
    console.print(f"  [green]✓[/green] {label}" if ok else f"  [red]✗[/red] {label}")
    if not ok:
        # 1200 and not 500: Gradle ends a failing run with ~400 characters of boilerplate
        # ("See the report at", "Try: Run with --scan"), so a 500-character tail showed the
        # count and cut every failing test NAME. More tail helps every check here — the
        # Python ones end in a traceback, where more is also better.
        console.print(f"[dim]{(proc.stdout + proc.stderr).strip()[-1200:]}[/dim]")
    return ok


def _reachable(label, url, timeout=5):
    try:
        r = sede.get(url, timeout=timeout)
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
    # And `which` alone is not enough for the other half: a systemd timer runs with a PATH
    # that carries no platform-tools, which is why `scripts/ronda_doze.sh` hardcodes the
    # absolute adb path. A `which`
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

    # The suite is a gate, but only where there is a toolchain to run it: a machine that just
    # serves the Búnker has no SDK, and that is not a defect — same reason the lines above are
    # informational. Where the SDK IS present this is not optional, because the suite went RED
    # for three days in August 2026 with nothing watching it (`668a62c` renamed the assets and
    # `AssetStoreTest` did not follow), and it was found by hand.
    #
    # `-p android`: the wrapper resolves its own jar from its own directory, so it runs from the
    # project root with no `cd` and `_run`'s cwd stays the same as every other check.
    #
    # `--offline` on purpose. Every dependency is already in the Gradle cache, and a gate that
    # reaches the network goes red when the network does — which is a false red, the worst kind.
    # A genuinely cold cache fails naming the artifact it could not resolve; drop the flag once
    # by hand to refill it.
    #
    # 420 s and not the default 180: measured at 16 s warm and 31 s with `--rerun-tasks`, but the
    # first run after a reboot has no daemon and compiles the module before testing anything.
    _gradlew = project_root / "android" / "gradlew"
    if hay_sdk and _gradlew.is_file():
        if not _run("android · testDebugUnitTest",
                    [str(_gradlew), "-p", "android", "testDebugUnitTest", "--offline"],
                    timeout=420):
            fallos += 1
    elif hay_sdk:
        console.print("  [yellow]○[/yellow] falta android/gradlew: la suite no puede correr")

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
    # On the HOST: no database, no container — it stabs `httpx` on `cli.sede` itself. Guards the
    # CLI's single HTTP seat, which is the only reason 111 call sites can send one auth header.
    # Its last check also pins that `cli/api.py` is still the ISBN oracle `books/views.py` imports:
    # the plan wanted the seat AT that path, and writing it there would have deleted the oracle.
    if not _run("tests.test_cli_sede",
                [sys.executable, "-m", "tests.test_cli_sede"]):
        fallos += 1
    # On the HOST: it mounts the real Textual app, which needs `cli.tui` and its terminal
    # machinery, neither of which the container installs. `test_cli_imports` above proves the
    # modules import; this one proves `bunker enter` reaches a painted frame — the gap that let
    # 37a9359 ship a TUI that died on mount and stayed dead for two days.
    if not _run("tests.test_tui_arranca",
                [sys.executable, "-m", "tests.test_tui_arranca"]):
        fallos += 1
    # On the HOST and not in `web`: it shells out to esbuild, which lives in `node_modules/`
    # here and is not installed in the container.
    if not _run("tests.test_bundle",
                [sys.executable, "-m", "tests.test_bundle"]):
        fallos += 1
    # On the HOST: it reads `install.sh` and `install.ps1` as text, so it needs neither a
    # database nor a container. It is the mitigation of a decision, not decoration — two native
    # installers were chosen over one in Python on 2026-08-31, and two files that do the same
    # thing drift. Nothing here can prove the PowerShell one RUNS; this proves both declare the
    # same steps in the same order.
    if not _run("tests.test_instaladores",
                [sys.executable, "-m", "tests.test_instaladores"]):
        fallos += 1
    # Node, and INSIDE `scraper-movies`: the two radars share one body since the three cuts, and
    # the only thing the merge could silently change is which extra fields each one attaches
    # before POSTing. `MovieWishlist` has `priority`/`added_by`; `MusicWishlist` has neither.
    # It drives `barrer()` for real, so it needs `axios` — and `scraper/node_modules` is empty on
    # the host (compose supplies it as an anonymous volume). Piped through stdin because the
    # container bind-mounts `./scraper:/app` and never sees `tests/`.
    _radar = pathlib.Path(__file__).resolve().parent.parent / "tests" / "test_radar.js"
    if not _run("tests/test_radar.js",
                ["docker", "compose", "exec", "-T", "scraper-movies", "node"],
                stdin_file=_radar):
        fallos += 1

    # Node, on the HOST: app.js imports only './queue.js', so it needs no node_modules at all.
    # It drives the real `cargarEstado()` against a stubbed bridge, because the one thing the
    # APK does that no browser does is replace `estado` wholesale with the native snapshot —
    # which used to discard the page advance the capture had just made.
    if not _run("tests/test_avance.js", ["node", "tests/test_avance.js"]):
        fallos += 1

    # Node, on the HOST, same reason: `panel.js` imports only './estado.js', which touches no DOM
    # at load. Guards the panel's dominant figure — the one that replaced the prestige total when
    # it left with the Posada split, and whose `.p-cifra`/`.p-delta` rules sat in app.html with
    # zero consumers for four days before anything used them again.
    if not _run("tests/test_cifra.js", ["node", "tests/test_cifra.js"]):
        fallos += 1

    # Node, on the HOST: estado.js, queue.js and app.js touch no DOM at load. Guards the token
    # across the PWA's THREE HTTP exits — the plan named only `pedir()`, and the one it left out
    # (`queue.js:vaciar`) is the one that WRITES the captures. Without it, Task 5's middleware
    # would 403 every capture, re-queue it, and pin the chip at "N SIN TRANSMITIR" for ever.
    if not _run("tests/test_token_pwa.js", ["node", "tests/test_token_pwa.js"]):
        fallos += 1

    # Node, on the HOST, and it EXECUTES `dist/main.js` in a vm against a DOM shim rather than
    # reading the source. `main.js` is the entry point: no test imports it, so its one piece of
    # logic — open the dialog when there is no token, and NEVER inside the APK — was pinned only
    # by a regex over the file. This project has shipped a green suite over a blank screen three
    # times; `37a9359` was a TUI that died on mount and stayed dead two days. It also proves the
    # BUILD carried the wiring, which a source-level check cannot see.
    if not _run("tests/test_dialogo_token.js", ["node", "tests/test_dialogo_token.js"]):
        fallos += 1

    if fallos:
        console.print(f"\n[bold red]{fallos} problema(s).[/bold red]\n")
    else:
        console.print("\n[bold green]Todo en orden.[/bold green]\n")
    raise typer.Exit(code=1 if fallos else 0)
