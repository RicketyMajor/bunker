"""Guard that `bunker enter` actually starts.

`37a9359` deleted a helper method and its hunk ended one line late, swallowing the
`@work(thread=True)` that belonged to the NEXT method, `fetch_dashboard`. From that commit on,
`bunker enter` died on mount with `RuntimeError: The call_from_thread method must run in a
different thread from the app` — Textual's `_handle_exception` always exits the app, so the TUI
never painted a frame.

Nothing caught it for two days. `bunker doctor` ran twelve suites and `test_cli_imports` walks
every module in `cli.`, but importing a Screen class is not mounting it: the defect lives in
`on_mount`, which an import never reaches. Every gate this project had was an import gate.

Two checks, because neither covers the other:

- `test_call_from_thread_solo_en_workers` is the ROOT-CAUSE check. `call_from_thread` exists to
  cross a thread boundary, so calling it from a method that is not a thread worker is always
  wrong, in any screen. It reads the AST, so it costs nothing and it fails on the sibling defect
  that has not been written yet.
- `test_la_tui_monta` drives the real app headless. The static check cannot see a broken
  `compose()`, a missing widget id or a CSS error — those only appear when something mounts.

Run: python -m tests.test_tui_arranca
"""
import ast
import asyncio
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "cli" / "tui"


def _metodos_que_cruzan_hilos():
    """Every method calling `call_from_thread`, with whether it is a thread worker.

    Returns (nombre, es_worker) pairs. `@work(thread=True)` and a bare `@work` both count:
    the point is that the method does not run on the app's own thread.
    """
    encontrados = []
    ficheros = sorted(RAIZ.glob("*.py"))
    # A directory that moved contributes zero methods in silence, and "no offenders" over an
    # empty sweep is true and meaningless. Assert the sweep found files before believing it.
    assert ficheros, f"no hay .py en {RAIZ}: el barrido no miro nada"
    for p in ficheros:
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        for clase in (n for n in ast.walk(arbol) if isinstance(n, ast.ClassDef)):
            for f in clase.body:
                if not isinstance(f, ast.FunctionDef):
                    continue
                cruza = any(isinstance(n, ast.Attribute) and n.attr == "call_from_thread"
                            for n in ast.walk(f))
                if not cruza:
                    continue
                es_worker = any(
                    (isinstance(d, ast.Call) and getattr(d.func, "id", "") == "work")
                    or getattr(d, "id", "") == "work"
                    for d in f.decorator_list)
                encontrados.append((f"{p.name}:{f.lineno} {clase.name}.{f.name}", es_worker))
    return encontrados


def test_call_from_thread_solo_en_workers():
    metodos = _metodos_que_cruzan_hilos()
    # Same vacuity trap one level down: if nobody calls `call_from_thread` any more the loop
    # below passes over an empty list. The count is deliberately NOT today's 60 — pinning it
    # would turn any legitimate refactor into a red with the wrong message.
    assert len(metodos) > 20, f"solo {len(metodos)} metodos cruzan hilos: el barrido no casa nada"
    sin_worker = [nombre for nombre, es_worker in metodos if not es_worker]
    assert not sin_worker, (
        "`call_from_thread` fuera de un worker de hilo — la app muere al montar:\n  "
        + "\n  ".join(sin_worker))


def test_la_tui_monta():
    """What an import can never prove: the app reaches a painted frame."""
    from cli.tui.app import BunkerApp

    async def arrancar():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            return type(app.screen).__name__

    pantalla = asyncio.run(arrancar())
    assert pantalla == "BunkerLauncherScreen", f"monto {pantalla}, no el Launcher"


if __name__ == "__main__":
    test_call_from_thread_solo_en_workers()
    test_la_tui_monta()
    print(f"OK: {len(_metodos_que_cruzan_hilos())} metodos cruzan hilos, todos en workers, "
          "y la TUI monta el Launcher")
