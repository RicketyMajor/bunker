"""The mobile bundle must exist, wire its globals, and match its sources.

    python -m tests.test_bundle          # from the repo root, on the HOST

Runs on the host and not in `web`: it shells out to esbuild, which lives in `node_modules/`
on this machine and not in the container.

**Why a rebuild and not an mtime comparison.** The spec asks for "present and newer than its
sources", and mtime is a proxy for the thing that matters: whether the bundle is what these
sources produce. mtime cannot see a bundle built from *different* source and touched afterwards,
and a `git checkout` rewrites it for reasons unrelated to staleness. esbuild is deterministic —
measured 2026-08-21, two builds of `main.js` byte-identical at 17830 bytes — so building into a
temp directory and comparing bytes answers the real question exactly, in about six milliseconds.
The deviation from the spec's wording is deliberate and strictly stronger.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MOVIL = RAIZ / "bunker_core/static/movil"
DIST = MOVIL / "dist"

# Entry point -> the globals its bundle must wire. The second half is what stops this check from
# passing against a bundle that is merely PRESENT and CURRENT: an entry point emptied to
# `export {}` rebuilds to a few bytes, matches itself perfectly, and serves a page that renders
# and runs nothing — the exact failure `copiarAssets` documents. These names survive minification
# because they are property accesses on `window`, not bindings esbuild is free to rename.
ENTRADAS = {
    "main.js": ("window.Cola", "window.App", "window.Panel"),
    "selftest.js": ("window.Cola",),
}

_fallos = []


def check(condicion, etiqueta):
    if condicion:
        print(f"  ok  {etiqueta}")
    else:
        _fallos.append(etiqueta)
        print(f"  FALLO  {etiqueta}")


def _construir(entrada, destino):
    """Build one entry point into `destino`. The flags MUST match package.json's `build`
    script: a difference there makes every comparison below fail for the wrong reason."""
    return subprocess.run(
        ["npx", "esbuild", str(MOVIL / entrada), "--bundle", "--minify",
         "--format=iife", "--target=es2020", f"--outfile={destino}"],
        cwd=RAIZ, capture_output=True, text=True, timeout=120)


def _comprobar_shell_del_sw():
    """Every file the service worker precaches must be one the page actually loads.

    Measured 2026-08-24: SHELL named `/static/movil/app.js` and `/static/movil/queue.js` --
    the unbundled ES modules -- while `app.html` has loaded `movil/dist/main.js` since esbuild
    landed on 2026-08-21. All three URLs answer 200, so nothing looked broken. The fetch
    handler is network-first and caches what it fetches, so an install that has been online
    once is unaffected; the case this list exists for is the install that goes OFFLINE FIRST,
    and that one had the shell and no JavaScript.

    Asserted against the template's own <script src>, not against a literal, so the two cannot
    drift apart again.
    """
    sw = (RAIZ / "bunker_core/templates/movil/sw.js").read_text()
    html = (RAIZ / "bunker_core/templates/movil/app.html").read_text()

    m = re.search(r"const SHELL = \[(.*?)\];", sw, re.S)
    check(m is not None, "sw.js declara un SHELL que se puede leer")
    if not m:
        return
    shell = set(re.findall(r"'([^']+)'", m.group(1)))

    cargados = {f"/static/movil/{r}" for r in re.findall(r"{% static 'movil/([^']+)' %}", html)}
    check(cargados, f"app.html carga al menos un asset estatico; encontrados {cargados}")

    faltan = cargados - shell
    check(not faltan,
          f"el SHELL del service worker precachea todo lo que app.html carga; faltan {faltan}")

    sobran = {u for u in shell - cargados if u.startswith("/static/")}
    check(not sobran,
          f"y no precachea estaticos que la pagina nunca pide; sobran {sobran}")


def main():
    # Before the npx guard: this one reads two templates and needs no toolchain, so putting it
    # after the early return meant it never ran on a machine without Node -- which is the same
    # machine that cannot rebuild the bundle and therefore needs the check most.
    _comprobar_shell_del_sw()

    if shutil.which("npx") is None:
        # Not a skip. Node became a hard dependency of this project on 2026-08-21 and a gate
        # that goes green because it could not run is the failure this project keeps finding.
        check(False, "npx no está en el PATH; `npm run build` no puede correr y el APK tampoco")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        for entrada, globals_esperados in ENTRADAS.items():
            construido = DIST / entrada
            check(construido.exists(),
                  f"{entrada}: el bundle existe en dist/ (corre `npm run build`)")
            if not construido.exists():
                continue

            contenido = construido.read_bytes()
            for nombre in globals_esperados:
                check(nombre.encode() in contenido,
                      f"{entrada}: el bundle expone {nombre}")

            fresco = Path(tmp) / entrada
            proc = _construir(entrada, fresco)
            check(proc.returncode == 0,
                  f"{entrada}: esbuild reconstruye sin error"
                  + (f" — {proc.stderr.strip()[-200:]}" if proc.returncode else ""))
            if proc.returncode != 0:
                continue

            frescos = fresco.read_bytes()
            # La etiqueta afirma la PROPIEDAD, no el fallo: un check que se lee "ok, está
            # rancio" es un check que nadie relee cuando se pone rojo.
            check(frescos == contenido,
                  f"{entrada}: el bundle en dist/ es lo que producen sus fuentes"
                  + ("" if frescos == contenido else
                     f" — RANCIO: {len(contenido)} bytes en dist/ vs {len(frescos)} "
                     f"recién construidos; corre `npm run build`"))

    print(f"\ntest_bundle: {len(ENTRADAS)} entradas · {len(_fallos)} fallos")
    return 1 if _fallos else 0


if __name__ == "__main__":
    sys.exit(main())
