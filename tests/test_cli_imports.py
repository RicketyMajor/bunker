"""Guard against broken imports in the `cli` package.

`bunker enter` died with `ModuleNotFoundError: No module named 'config'` because five files
imported `from config import BASE_URL` — a top-level name that only resolves when `cli/` itself
is on sys.path, not when the installed `cli` package is imported. Nothing caught it until the
entry point was run by hand.

Run: python -m tests.test_cli_imports
"""
import importlib
import pkgutil

import cli


def test_every_cli_module_imports():
    failures = []
    for module in pkgutil.walk_packages(cli.__path__, "cli."):
        try:
            importlib.import_module(module.name)
        except Exception as exc:  # noqa: BLE001 - we want the whole failure list, not the first one
            failures.append(f"{module.name}: {type(exc).__name__}: {exc}")
    assert not failures, "modules failed to import:\n" + "\n".join(failures)


def test_entry_point_is_importable():
    """This is exactly what /usr/local/bin/bunker does on startup."""
    from cli.main import app
    assert app is not None


def test_cargar_serie_nunca_lanza():
    """`cargar_serie` runs inside workers that load other things after it — the wishlist in
    two of the three screens. An exception escaping it drops all of them in silence, so the
    tab just stays empty and nothing is reported. Every failure mode is exercised here:
    the endpoint unreachable, the app refusing `call_from_thread`, and the widget gone.
    """
    from cli.tui.tabs import _pintar_en, cargar_serie

    class AppMuerta:
        def call_from_thread(self, *a, **k):
            raise RuntimeError("la app se está cerrando")

    class PantallaMuerta:
        app = AppMuerta()

        def query_one(self, *a, **k):
            raise LookupError("NoMatches: la pantalla ya no está")

    pantalla = PantallaMuerta()
    # Sin backend alcanzable y con la app rechazando el salto de hilo.
    cargar_serie(pantalla, "#no_existe", "books", "Prueba")
    # Y el pintado en sí, con el widget desaparecido.
    _pintar_en(pantalla, "#no_existe", [], "Prueba")


if __name__ == "__main__":
    test_every_cli_module_imports()
    test_entry_point_is_importable()
    test_cargar_serie_nunca_lanza()
    print("OK: every cli module imports, the bunker entry point resolves, "
          "and cargar_serie swallows every failure")
