"""Guard against broken imports in the `cli` package.

`bunker enter` died with `ModuleNotFoundError: No module named 'config'` because five files
imported `from config import BASE_URL` — a top-level name that only resolves when `cli/` itself
is on sys.path, not when the installed `cli` package is imported. Nothing caught it until the
entry point was run by hand.

Run: python test_cli_imports.py
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


if __name__ == "__main__":
    test_every_cli_module_imports()
    test_entry_point_is_importable()
    print("OK: every cli module imports and the bunker entry point resolves")
