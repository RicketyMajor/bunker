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
                    # "screen.revert_record" y "switch_tab('tab_x')" -> revert_record, switch_tab
                    acciones.add(accion.split("(")[0].split(".")[-1])
            return [type(s).__name__ for s in app.screen_stack], resueltos, acciones

    for cls in (LibraryMainScreen, MovieMainScreen, MusicMainScreen):
        pila, resueltos, acciones = asyncio.run(montar(cls))
        assert cls.__name__ in pila, f"{cls.__name__} no monto: la pila quedo en {pila}"
        rotos = {k: v for k, v in resueltos.items() if v != "ok"}
        assert not rotos, (
            f"{cls.__name__} monto pero sus ids no existen en el arbol de widgets: {rotos}")

        # Que el metodo RESUELVA por el MRO no es que una tecla llegue a el. `MovieTrackerTab`
        # no llevaba `("x", "screen.revert_record", ...)` — la tenian las otras dos pestañas de
        # Registro — asi que en el Videoclub la tecla no hacia nada mientras revertia un
        # registro en Biblioteca y Disquera, y un check que solo mira el MRO sale VERDE sobre
        # codigo muerto. Se recorren las BINDINGS de la pantalla y de todo widget montado.
        assert len(acciones) > 5, (
            f"{cls.__name__}: solo {len(acciones)} acciones con tecla — el barrido no casa nada")
        for acc in ("toggle_sidebar", "focus_search", "switch_tab", "revert_record"):
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
                "action_switch_tab", "action_revert_record"]
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
    `("x", "screen.revert_record", ...)` entirely — the MRO check was green over a method no key
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
            pantalla.action_revert_record = lambda: disparos.append("x")
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
            f"{cls.__name__}: 'x' no invoco revert_record en la pestaña Registro")


def test_ctrl_g_vuelve_al_launcher():
    """The global shortcut back to the command centre, and why it is NOT `ctrl+h`.

    The backlog proposed `ctrl+h`. Measured on Textual 8.2.1: most terminals send 0x08 when ctrl+h
    is pressed and `_ansi_sequences.py` translates it to `Keys.Backspace`, so that binding would
    never fire — and if it did, it would swallow deletion in every `Input`. Same for `ctrl+i`
    (tab), `ctrl+m` (enter) and `ctrl+j`. `ctrl+g` is used, which arrives as itself.

    The KEY is pressed, the action is not called: a correct `action_al_launcher` that no key
    reaches is exactly the defect `a1eed5d` fixed in this TUI's BINDINGS — a BINDINGS string is
    text, not a symbol.

    And it is checked over a stack of TWO screens above the Launcher, because the single-screen
    version cannot tell "goes back to the Launcher" from "does one pop".
    """
    from cli.tui.app import BunkerApp
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.music_screens import MusicMainScreen
    from cli.tui.screens import BunkerLauncherScreen

    async def ir_y_volver():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(MovieMainScreen())
            await pilot.pause()
            await app.push_screen(MusicMainScreen())
            await pilot.pause()
            antes = type(app.screen).__name__
            await pilot.press("ctrl+g")
            await pilot.pause()
            return antes, type(app.screen).__name__, len(app.screen_stack)

    antes, despues, altura = asyncio.run(ir_y_volver())
    assert antes != "BunkerLauncherScreen", (
        f"the test is vacuous: we were already on the Launcher before pressing ({antes})")
    assert despues == "BunkerLauncherScreen", (
        f"ctrl+g left the TUI on {despues}, not on the command centre")
    assert altura >= 1, "the stack emptied: pop_screen overshot"


def test_ctrl_g_no_vacia_una_pila_sin_launcher():
    """The loop's guard. With no Launcher in the stack, the action must do NOTHING.

    Without it the `while` would pop until the app sits on the base screen — blank and with no
    keys — and no other check would see that: the TUI would still be "alive".
    """
    from cli.tui.app import BunkerApp
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.screens import BunkerLauncherScreen

    async def sin_launcher():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # The Launcher is taken out of the stack on purpose: it is the state the guard covers.
            while any(isinstance(p, BunkerLauncherScreen) for p in app.screen_stack):
                app.pop_screen()
            await app.push_screen(MovieMainScreen())
            await pilot.pause()
            altura_antes = len(app.screen_stack)
            app.action_al_launcher()
            await pilot.pause()
            return altura_antes, len(app.screen_stack), type(app.screen).__name__

    antes, despues, arriba = asyncio.run(sin_launcher())
    assert antes == despues, (
        f"with no Launcher in the stack the action popped {antes - despues} screens (ended on {arriba})")


def test_las_exclusiones_llegan_de_la_TUI_a_la_API():
    """The `WatcherModal`'s new field and the THREE writers that forward it.

    Both halves are tested because one alone says nothing: a modal that collects `exclusiones` and
    three `process_add_watcher` that throw them away leaves the field exactly as unreachable as
    when it lived only in `/admin/`. Here the WRITER is interrogated — the body that goes out
    through `sede.post` — which is the half that gets forgotten.

    `sede.post` is replaced by a spy: this test must not write to the live board, and what is
    asked is what the TUI SENDS, not what the server does with it (that is covered by
    `tests/test_fuentes.py`, which drives the real view).
    """
    from cli import sede
    from cli.tui.library_screen import LibraryMainScreen
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.music_screens import MusicMainScreen
    from cli.tui.modals import WatcherModal

    # -- half 1: the modal RETURNS the exclusions
    from cli.tui.app import BunkerApp
    from textual.widgets import Input, Button

    async def rellenar():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            devuelto = {}
            modal = WatcherModal("Vigilar", "Ej: X")
            app.push_screen(modal, lambda r: devuelto.update({"r": r}))
            await pilot.pause()
            modal.query_one("#inp_keyword", Input).value = "Kavinsky"
            modal.query_one("#inp_exclusiones", Input).value = "M!das, Mdas"
            modal.query_one("#btn_add", Button).press()
            await pilot.pause()
            return devuelto.get("r")

    devuelto = asyncio.run(rellenar())
    assert isinstance(devuelto, dict), f"el modal devolvio {devuelto!r}, no un dict"
    assert devuelto.get("keyword") == "Kavinsky", devuelto
    assert devuelto.get("exclusiones") == "M!das, Mdas", devuelto

    # And with no keyword NOTHING comes out: a POST with an empty `keyword` is a junk row that
    # then has to be deleted from the admin that is no longer mounted.
    async def vacio():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            devuelto = {}
            modal = WatcherModal("Vigilar", "Ej: X")
            app.push_screen(modal, lambda r: devuelto.update({"r": r}))
            await pilot.pause()
            modal.query_one("#inp_exclusiones", Input).value = "solo exclusiones"
            modal.query_one("#btn_add", Button).press()
            await pilot.pause()
            return devuelto.get("r", "SIN LLAMAR")

    assert asyncio.run(vacio()) is None, "the modal accepted a watcher with no keyword"

    # -- half 2: the THREE writers forward it. Three and not one: the missing consumer is always
    # the one that writes, and here three write the same thing down different paths.
    class _Resp:
        status_code = 201

    enviados = []
    original = sede.post
    sede.post = lambda url, **kw: (enviados.append((url, kw.get("json"))), _Resp())[1]
    try:
        for cls in (LibraryMainScreen, MovieMainScreen, MusicMainScreen):
            # The screen is NOT instantiated: `Screen.app` is a property with no setter, and
            # really mounting it would drag the whole app in to interrogate four lines. The
            # worker's body only touches `self.app`, so a double with that attribute is subject
            # enough.
            #
            # `@work` wraps the method and exposes the original as `__wrapped__`; that is what is
            # called, so as not to depend on Textual's scheduler, which does not exist outside a
            # running app. If `work` ever stopped setting `__wrapped__`, this would blow up with
            # AttributeError — loud, not silent.
            cls.process_add_watcher.__wrapped__(
                _PantallaFalsa(), {"keyword": "ZZPrueba", "exclusiones": "ZZExcluido"})
    finally:
        sede.post = original

    assert len(enviados) == 3, f"3 writers expected, {len(enviados)} wrote"
    for url, cuerpo in enviados:
        assert cuerpo.get("exclusiones") == "ZZExcluido", (
            f"{url} sent {cuerpo!r}: it lost the exclusions on the way")
        assert cuerpo.get("keyword") == "ZZPrueba", f"{url} sent {cuerpo!r}"
        assert cuerpo.get("is_active") is True, f"{url} sent {cuerpo!r}"


class _AppFalsa:
    """The minimum `process_add_watcher` touches: `call_from_thread` and `notify`."""

    def call_from_thread(self, fn, *a, **kw):
        return fn(*a, **kw)

    def notify(self, *a, **kw):
        pass


class _PantallaFalsa:
    """A `self` with `.app`, which is all the worker's body uses."""

    def __init__(self):
        self.app = _AppFalsa()


def test_los_workers_de_musica_avisan_de_un_codigo_malo():
    """Un 403, un 400 o un 404 tienen que LLEGAR AL USUARIO, no dejar la TUI muda.

    Los siete workers que esta sesión le dio a música eran `if resp.status_code == N:` sin `else`,
    y `except` sólo atrapa errores de transporte. Un 403 —un `BUNKER_API_TOKEN` caducado, y el
    middleware guarda TODA ruta bajo `/api/` desde el 2026-08-31— no producía ni aviso ni recarga:
    el usuario pulsaba la tecla, confirmaba el diálogo, y no pasaba nada en absoluto. Encontrado
    por `/code-review` el 2026-09-02.

    Se interroga el AVISO, no el código de estado: comprobar que el `else` existe leyendo el
    fuente no dice si el mensaje sale por `call_from_thread`.
    """
    from cli import sede
    from cli.tui.music_screens import MusicMainScreen

    class _Resp:
        def __init__(self, code, cuerpo):
            self.status_code = code
            self._cuerpo = cuerpo
            self.text = str(cuerpo)

        def json(self):
            return self._cuerpo

    avisos = []

    class _App:
        def call_from_thread(self, fn, *a, **kw):
            return fn(*a, **kw)

        def notify(self, mensaje, **kw):
            avisos.append((mensaje, kw.get("severity")))

    class _Pantalla:
        def __init__(self):
            self.app = _App()

        def load_data(self):
            avisos.append(("RECARGA", None))

    originales = (sede.delete, sede.post, sede.patch)
    sede.delete = lambda *a, **k: _Resp(403, {"error": "Acceso denegado."})
    sede.post = lambda *a, **k: _Resp(400, {"keyword": ["This field may not be blank."]})
    sede.patch = lambda *a, **k: _Resp(404, {"detail": "No encontrado."})
    try:
        MusicMainScreen.process_delete_inbox.__wrapped__(_Pantalla(), "9")
        MusicMainScreen.process_add_watcher.__wrapped__(
            _Pantalla(), {"keyword": "", "exclusiones": ""})
        MusicMainScreen.process_delete_wishlist.__wrapped__(_Pantalla(), "7")
    finally:
        sede.delete, sede.post, sede.patch = originales

    assert len(avisos) == 3, f"tres códigos malos produjeron {len(avisos)} avisos: {avisos}"
    for mensaje, severidad in avisos:
        assert severidad == "error", f"{mensaje!r} no se avisó como error, sino como {severidad!r}"
    # El código de estado tiene que VIAJAR en el mensaje: "algo falló" sin el número obliga a
    # adivinar si es el token, la fila o el servidor.
    codigos = [c for c in ("403", "400", "404") if any(c in m for m, _ in avisos)]
    assert codigos == ["403", "400", "404"], (
        f"los avisos no nombran los tres códigos, sólo {codigos}: {avisos}")
    # Y NINGUNO recarga: una recarga tras un fallo repinta la fila sin cambiar y parece un éxito.
    assert not any(m == "RECARGA" for m, _ in avisos), f"un fallo disparó load_data(): {avisos}"


def test_ctrl_g_no_atraviesa_un_modal():
    """Y NO llega desde un `ModalScreen`. Se fija porque la afirmación contraria estaba escrita.

    `Screen._modal_binding_chain` corta la cadena en el primer nodo `is_modal`, así que las
    `BINDINGS` de la App son inalcanzables con un diálogo encima. El docstring de
    `action_al_launcher` decía "modals included" y el README "desde cualquier pantalla": las dos
    eran falsas, y `test_ctrl_g_vuelve_al_launcher` no podía verlo porque sólo apila pantallas
    normales. Lo encontró `/code-review` el 2026-09-02.

    Se deja como Textual lo diseña —un modal tiene una respuesta pendiente— y se ancla aquí para
    que un cambio de comportamiento se vea, en la dirección que sea.
    """
    from cli.tui.app import BunkerApp
    from cli.tui.movie_screens import MovieMainScreen
    from cli.tui.modals import WatcherModal

    async def con_modal():
        app = BunkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(MovieMainScreen())
            await pilot.pause()
            app.push_screen(WatcherModal("Vigilar", "Ej: X"))
            await pilot.pause()
            antes = type(app.screen).__name__
            altura = len(app.screen_stack)
            await pilot.press("ctrl+g")
            await pilot.pause()
            return antes, altura, type(app.screen).__name__, len(app.screen_stack)

    antes, altura_antes, despues, altura = asyncio.run(con_modal())
    assert antes == "WatcherModal", f"la prueba es vacua: el modal no llegó a la cima ({antes})"
    assert despues == "WatcherModal", (
        f"ctrl+g ATRAVESÓ el modal y dejó la TUI en {despues}. Si eso es lo que se quiere ahora, "
        "arregla también el docstring de `action_al_launcher` y el README, que dicen lo contrario")
    assert altura == altura_antes, f"la pila cambió de {altura_antes} a {altura}"


if __name__ == "__main__":
    test_call_from_thread_solo_en_workers()
    test_la_tui_monta()
    test_las_pantallas_de_coleccion_montan()
    test_el_mixin_resuelve_sus_cuatro_acciones()
    test_la_tecla_x_revierte_en_las_tres()
    test_ctrl_g_vuelve_al_launcher()
    test_ctrl_g_no_vacia_una_pila_sin_launcher()
    test_ctrl_g_no_atraviesa_un_modal()
    test_las_exclusiones_llegan_de_la_TUI_a_la_API()
    test_los_workers_de_musica_avisan_de_un_codigo_malo()
    print(f"OK: {len(_metodos_que_cruzan_hilos())} metodos cruzan hilos, todos en workers; "
          "la TUI monta el Launcher; las tres pantallas de coleccion montan, sus cuatro "
          "acciones resuelven al mixin, 'x' revierte en las tres, y ctrl+g vuelve al "
          "centro de mando sin vaciar una pila que no lo tiene; y las exclusiones "
          "salen del modal y las mandan los tres escritores")
