"""No HTTP call in the TUI runs on the interface thread.

Run: .venv/bin/python -m tests.test_hilo_ui   (host: reads the tree, does not import Django)

Textual dispatches key handlers and `push_screen` callbacks on the UI THREAD. `cli/sede.py` is
SYNCHRONOUS httpx, so one of those there freezes the whole interface until the server answers or
`timeout=5.0` expires. The correct pattern was already in the project — `@work(thread=True)` plus
`call_from_thread` to touch widgets — and `library_screen.py` (37 calls), `movie_screens.py` (29),
`screens.py` (6) and `modals.py` (1) all followed it.

WHAT THIS CAUGHT WHEN IT WAS WRITTEN, on 2026-09-02: `music_screens.py` had **12 of its 29 calls
on the UI thread**. The worst, `action_clear_wishlist`, did a GET and then **one PATCH per row of
the board, serially** — with music's 75 live rows that is the TUI blocked for 76 requests. Several
also had no `try/except`: a network exception inside a modal callback, not inside the worker that
catches it.

It surfaced while measuring the "unify movie_screens and music_screens" debt. The duplication was
not the defect: it was what hid it. The two copies did not diverge in naming, they diverged in
WHERE the request runs.

NOT THE SAME AS `tests/test_tui_arranca.py:test_call_from_thread_solo_en_workers`, and both are
needed: that one requires whoever calls `call_from_thread` to be a worker (otherwise the app DIES
on mount); this one requires whoever calls `sede.*` to be one (otherwise the app FREEZES). The 12
music calls never touched `call_from_thread` — precisely because they ran on the UI thread — so
that check was green over every one of them. Two halves of the same contract, neither implying
the other.

⚠ WHAT THIS CHECK CANNOT SEE, and it has to be said because its first version produced a false
positive: it walks the NESTED-function stack, not the CALL stack. A module-level function calling
`sede.*` comes out clean even if a handler invokes it — that is `cli/tui/tabs.py:cargar_serie`,
which runs inside a worker and whose docstring says so. That is why only METHODS of a class are
judged: those are what Textual dispatches. `cli/main.py` and `cli/doctor.py` are outside the sweep
on purpose: they are console commands, with no event loop, and blocking there is correct.
"""
import ast
import pathlib
import sys

TUI = pathlib.Path(__file__).resolve().parent.parent / 'cli' / 'tui'

fallos = 0


def check(cond, etiqueta):
    global fallos
    print(f'  {"ok  " if cond else "FALLA"} {etiqueta}')
    if not cond:
        fallos += 1


def _en_hilo_de_ui(ruta):
    """Returns (total sede.* calls, [those running on the UI thread])."""
    arbol = ast.parse(ruta.read_text(encoding='utf-8'))
    padre = {h: n for n in ast.walk(arbol) for h in ast.iter_child_nodes(n)}

    def anidadas(n):
        out = []
        while n in padre:
            n = padre[n]
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append(n)
        return out

    total, malas = 0, []
    for n in ast.walk(arbol):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == 'sede'):
            continue
        total += 1
        pila = anidadas(n)
        if not pila:
            continue
        externa = pila[-1]
        # METHODS only: a module-level function is called by whoever, and that may be a worker.
        if not isinstance(padre.get(externa), ast.ClassDef):
            continue
        if any('work' in ast.dump(d) for d in externa.decorator_list):
            continue
        malas.append(f"{ruta.name}:{n.lineno} sede.{n.func.attr} en "
                     f"{'/'.join(f.name for f in reversed(pila))}")
    return total, malas


ficheros = sorted(p for p in TUI.glob('*.py') if p.name != '__init__.py')
check(len(ficheros) >= 6, f'the sweep finds the TUI modules ({len(ficheros)})')

total, sucias = 0, []
for p in ficheros:
    n, malas = _en_hilo_de_ui(p)
    total += n
    sucias += malas

# VACUITY FIRST: with no calls to judge, the check below is vacuously true and this file would
# report the TUI clean without having looked at a single line.
check(total >= 80, f'there are sede.* calls to judge: {total} (102 measured 2026-09-02)')
check(not sucias,
      f'no sede.* call runs on the UI thread; {len(sucias)} got through: {sucias[:6]}')

print(f"\ntest_hilo_ui: {total} llamadas · {'0 fallos' if not fallos else f'{fallos} FALLOS'}")
raise SystemExit(1 if fallos else 0)
