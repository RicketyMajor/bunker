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
    """What an import can never prove: the app reaches a painted frame.

    Asserts the Launcher is in the screen STACK, not that it is on top. It was written as
    `app.screen == BunkerLauncherScreen` and that made the gate a coin flip: `app.py:58` pushes
    the Launcher, and the Launcher's own `fetch_dashboard` worker then pushes `BriefingScreen`
    over it when the briefing has not been seen. Whether one `pilot.pause()` is long enough for
    that worker to land is a race — measured at **3 failures in 6 runs on untouched HEAD**, in
    the exact check that exists because the TUI once died on mount for two days.

    The stack answers what the check is actually for: the app reached a painted frame and the
    Launcher is the screen it built. What sits on top of it is a product decision that changes
    with the calendar, and pinning a gate to it makes the gate fail for the wrong reason.
    """
    from cli.tui.app import BunkerApp

    async def arrancar():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            return [type(s).__name__ for s in app.screen_stack]

    pila = asyncio.run(arrancar())
    assert "BunkerLauncherScreen" in pila, f"la pila quedo en {pila}, sin el Launcher"


def test_las_pantallas_de_coleccion_montan():
    """The Launcher gate cannot see these: they mount only when a card is opened.

    `ColeccionScreen` moved four methods out of three screens. A missing widget id, a broken
    class attribute or an MRO mistake shows up on mount and nowhere earlier — the same blind
    spot that left `bunker enter` dead for two days, one screen deeper.
    """
    from cli.tui.app import BunkerApp
    from cli.tui.library_screen import LibraryMainScreen
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.music_screens import MusicMainScreen

    from textual.widgets import DataTable, TabbedContent

    # Estar en la pila NO es haber montado. `push_screen` apila la pantalla antes de que
    # `on_mount` termine, asi que una version anterior de este check salio VERDE con
    # `#movie_annual_table` renombrado en `compose` — el defecto exacto que el mixin puede
    # introducir. Lo que se pregunta ahora es si los ids que cada subclase declara existen
    # de verdad en el arbol de widgets montado.
    ESPERADOS = [("TABLA_PRINCIPAL", DataTable),
                 ("CONTENEDOR_TABS", TabbedContent),
                 ("TABLA_ANUAL", DataTable)]

    async def montar(cls):
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pantalla = cls()
            await app.push_screen(pantalla)
            await pilot.pause()
            resueltos = {}
            for attr, tipo in ESPERADOS:
                selector = getattr(cls, attr)
                try:
                    pantalla.query_one(selector, tipo)
                    resueltos[attr] = "ok"
                except Exception as e:
                    resueltos[attr] = f"{selector} -> {type(e).__name__}"

            # Toda accion que una tecla puede invocar: la pantalla y cada widget montado.
            # `BINDINGS` es atributo de clase, asi que se lee del tipo, no de la instancia.
            acciones = set()
            for nodo in [pantalla, *pantalla.query("*")]:
                for b in getattr(type(nodo), "BINDINGS", []):
                    accion = b[1] if isinstance(b, tuple) else getattr(b, "action", "")
                    # "screen.delete_habit" y "switch_tab('tab_x')" -> delete_habit, switch_tab
                    acciones.add(accion.split("(")[0].split(".")[-1])
            return [type(s).__name__ for s in app.screen_stack], resueltos, acciones

    for cls in (LibraryMainScreen, MovieMainScreen, MusicMainScreen):
        pila, resueltos, acciones = asyncio.run(montar(cls))
        assert cls.__name__ in pila, f"{cls.__name__} no monto: la pila quedo en {pila}"
        rotos = {k: v for k, v in resueltos.items() if v != "ok"}
        assert not rotos, (
            f"{cls.__name__} monto pero sus ids no existen en el arbol de widgets: {rotos}")

        # Que el metodo RESUELVA por el MRO no es que una tecla llegue a el. `MovieTrackerTab`
        # no llevaba `("x", "screen.delete_habit", ...)` — la tenian las otras dos pestañas de
        # Registro — asi que en el Videoclub la tecla no hacia nada mientras revertia un
        # registro en Biblioteca y Disquera, y un check que solo mira el MRO sale VERDE sobre
        # codigo muerto. Se recorren las BINDINGS de la pantalla y de todo widget montado.
        assert len(acciones) > 5, (
            f"{cls.__name__}: solo {len(acciones)} acciones con tecla — el barrido no casa nada")
        for acc in ("toggle_sidebar", "focus_search", "switch_tab", "delete_habit"):
            assert acc in acciones, (
                f"{cls.__name__}: ninguna tecla invoca `{acc}` — el metodo existe y es "
                f"inalcanzable. Teclas vistas: {sorted(acciones)}")


def test_el_mixin_resuelve_sus_cuatro_acciones():
    """Textual resolves an action by `getattr(screen, f"action_{name}")`. A binding naming a
    method the MRO does not reach fails at KEYPRESS, not at mount — so mounting the screens
    proves nothing about the four methods `ColeccionScreen` now owns.
    """
    from cli.tui.coleccion_screen import ColeccionScreen
    from cli.tui.library_screen import LibraryMainScreen
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.music_screens import MusicMainScreen

    acciones = ["action_toggle_sidebar", "action_focus_search",
                "action_switch_tab", "action_delete_habit"]
    atributos = ["TABLA_PRINCIPAL", "CONTENEDOR_TABS", "TABLA_ANUAL", "MSG_REVERTIR"]
    pantallas = (LibraryMainScreen, MovieMainScreen, MusicMainScreen)

    for cls in pantallas:
        assert issubclass(cls, ColeccionScreen), f"{cls.__name__} no hereda del mixin"
        for a in acciones:
            assert getattr(cls, a, None) is getattr(ColeccionScreen, a), (
                f"{cls.__name__}.{a} no resuelve al mixin — hay una copia superviviente")
        for attr in atributos:
            valor = getattr(cls, attr, None)
            assert valor, f"{cls.__name__} no define {attr}"
            if attr != "MSG_REVERTIR":
                assert valor.startswith("#"), (
                    f"{cls.__name__}.{attr} = {valor!r}: un id de widget empieza por '#'")
        assert "{title}" in cls.MSG_REVERTIR, (
            f"{cls.__name__}.MSG_REVERTIR no tiene el hueco {{title}}: el dialogo saldria "
            "sin nombrar la obra")

    # Cada pantalla apunta a SUS widgets. Dos que compartan ids es un copy-paste a medias que
    # monta bien y falla al pulsar la tecla, en la pantalla equivocada.
    ids = {cls.__name__: (cls.TABLA_PRINCIPAL, cls.CONTENEDOR_TABS, cls.TABLA_ANUAL)
           for cls in pantallas}
    assert len(set(ids.values())) == 3, f"dos pantallas comparten ids de widget: {ids}"


def test_la_tecla_x_revierte_en_las_tres():
    """The strongest form: press the key and see the action fire.

    Neither check above could see the two defects this one found. `MovieTrackerTab` was missing
    `("x", "screen.delete_habit", ...)` entirely — the MRO check was green over a method no key
    could reach. And the Biblioteca HAD the binding and was still dead: its
    `on_tabbed_content_tab_activated` focused the first `DataTable` **or Markdown**, `TrackerTab`
    yields its `Markdown` first, `Markdown.can_focus` is False, so `.focus()` did nothing, the
    loop broke, and a pane with no focus does not apply its `TabPane` BINDINGS.

    Being MORE general is what broke it, which is why this check presses the key instead of
    reading the bindings: the binding was there and correct the whole time.

    The Briefing must be dismissed first. `BunkerApp` mounts the Launcher, whose `fetch_dashboard`
    worker pushes `BriefingScreen` on top, and it eats every keypress — any `Pilot` test in this
    app inherits that race.
    """
    from textual.widgets import TabbedContent

    from cli.tui.app import BunkerApp
    from cli.tui.library_screen import LibraryMainScreen
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.music_screens import MusicMainScreen

    async def pulsar(cls):
        app = BunkerApp()
        disparos = []
        async with app.run_test() as pilot:
            await pilot.pause()
            pantalla = cls()
            await app.push_screen(pantalla)
            await pilot.pause()
            for _ in range(5):
                if app.screen is pantalla:
                    break
                app.pop_screen()
                await pilot.pause()
            assert app.screen is pantalla, (
                f"{cls.__name__} no llego a ser la pantalla activa: "
                f"{type(app.screen).__name__} se queda con las teclas")
            pantalla.action_delete_habit = lambda: disparos.append("x")
            await pilot.press("4")
            await pilot.pause()
            activa = pantalla.query_one(cls.CONTENEDOR_TABS, TabbedContent).active
            enfocado = app.focused is not None
            await pilot.press("x")
            await pilot.pause()
        return activa, enfocado, disparos

    for cls in (LibraryMainScreen, MovieMainScreen, MusicMainScreen):
        activa, enfocado, disparos = asyncio.run(pulsar(cls))
        assert activa == "tab_tracker", (
            f"{cls.__name__}: '4' dejo la pestaña en {activa!r}, no en Registro")
        assert enfocado, (
            f"{cls.__name__}: la pestaña Registro quedo SIN FOCO, y sin foco no aplican las "
            "BINDINGS del TabPane")
        assert disparos, (
            f"{cls.__name__}: 'x' no invoco delete_habit en la pestaña Registro")


if __name__ == "__main__":
    test_call_from_thread_solo_en_workers()
    test_la_tui_monta()
    test_las_pantallas_de_coleccion_montan()
    test_el_mixin_resuelve_sus_cuatro_acciones()
    test_la_tecla_x_revierte_en_las_tres()
    print(f"OK: {len(_metodos_que_cruzan_hilos())} metodos cruzan hilos, todos en workers; "
          "la TUI monta el Launcher; las tres pantallas de coleccion montan, sus cuatro "
          "acciones resuelven al mixin, y 'x' revierte en las tres")
