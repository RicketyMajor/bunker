"""Standalone checks for the consultation surface `/panel/`.

`/api/panel/` and its four blocks — prestige, habits, achievements, the session log — were
entirely Posada and left with it on 2026-08-27, and the four checks that drove them left too.
What remains is what was never about Posada: that these GETs do not write, and that no new
empty `catch` appears in the panel's JavaScript.

Run: docker compose exec web python -m tests.test_panel

Everything here is PLANTED. On this machine the live database holds 1 `PrestigeEntry`, 0
`DailyHabit` and 0 unlocked `Achievement`, so an assertion against what is already there is an
assertion about nothing — the panel's EMPTY state is the default path and the populated one is
the one at risk of never being exercised. Every check below plants its rows first.

Every check runs inside a transaction that is rolled back, so it is safe against live data.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test import Client  # noqa: E402

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _exige_rollback():
    """These checks write to the LIVE database and are safe only inside `run_tests()`, which
    wraps them in `transaction.atomic()` with a forced rollback. The functions are plain
    module-level `test_*` names: importing one and calling it, or any future collector, would
    leave planted rows behind for good."""
    assert connection.in_atomic_block, (
        "este check escribe en la base VIVA y solo es seguro dentro de "
        "transaction.atomic() con rollback forzado — úsalo vía run_tests()")


def _panel():
    respuesta = Client().get('/api/panel/')
    assert respuesta.status_code == 200, f"/api/panel/ devolvió {respuesta.status_code}"
    return respuesta.json()


def test_el_panel_no_escribe_nada():
    """Drive the panel's endpoints and assert the database did not move.

    The spec prescribes a weaker check — "no POST/PUT/PATCH/DELETE route is reachable" — and
    `/api/briefing/` was a GET that WROTE, so that check would have passed while the criterion
    was violated. This one counts rows in every table.

    The `status_code == 200` assertions are what stop it being vacuous: a 404 leaves the census
    unchanged and the check green. Keep them.
    """
    _exige_rollback()
    from django.apps import apps

    def censo():
        return {m._meta.label: m.objects.count() for m in apps.get_models()}

    cliente = Client()
    antes = censo()
    # `/panel/` se pide SIN cabecera y `/api/…` CON ella, y esa asimetria es el diseño, no un
    # descuido: `bunker_core.auth.TokenDeBunker` guarda `/api/`, y `/panel/` tiene que seguir
    # cargandose sin token para que la pagina pueda PEDIRLO. En el navegador lo manda
    # `estado.js:cabeceras()`; aqui se manda a mano lo mismo.
    import os
    cabecera = {'X-Bunker-Api-Token': os.environ['BUNKER_API_TOKEN']}
    for url, cab in (('/panel/', {}), ('/api/stats/timeline/?module=books', cabecera)):
        respuesta = cliente.get(url, headers=cab)
        check(respuesta.status_code == 200,
              f"{url} responde 200, dio {respuesta.status_code}")
    # Y la otra direccion, que es la que este fichero no podia ver antes de que hubiera guardia:
    # sin cabecera, esa misma ruta NO debe servir la serie.
    check(cliente.get('/api/stats/timeline/?module=books').status_code == 403,
          "sin cabecera, /api/stats/timeline/ responde 403")
    despues = censo()
    movidas = {k: (antes[k], despues[k]) for k in antes if antes[k] != despues[k]}
    check(not movidas, f"el panel escribió: {movidas}")


# Los `catch` que se tragan el error y NO producen estado visible, inventariados de UNA en UNA.
#
# No es una lista de pecados: los tres son correctos y el comentario de cada uno dice por qué.
# Es un trinquete — un `catch` vacío NUEVO no está en la lista y pone el check rojo. La clave es
# (fichero, primeras palabras del comentario) y no el número de línea, que se mueve solo.
TRAGADORES_CONOCIDOS = {
    ("app.js", "quota or private mode"),
    ("app.js", "no decodable frame this tick"),
    ("queue.js", "the body was not JSON"),
}


def _cuerpos_de_catch(texto):
    """Yield (indice, cuerpo) for every `catch` block, matching braces instead of lines.

    A line-by-line regex — which is what the plan prescribed — cannot see a catch whose body
    spans two lines, and does not see one whose body is a COMMENT either: `catch (_) { /* … */ }`
    has a body that is not `}` and not a `console.*` call, so the prescribed pattern scores zero
    hits on this codebase while three real swallows sit in it. Measured before this was written.
    """
    i = 0
    while (i := texto.find('catch', i)) != -1:
        abre = texto.find('{', i)
        if abre == -1:
            break
        profundidad, j = 0, abre
        while j < len(texto):
            if texto[j] == '{':
                profundidad += 1
            elif texto[j] == '}':
                profundidad -= 1
                if profundidad == 0:
                    break
            j += 1
        yield i, texto[abre + 1:j]
        i = j + 1


def _sin_comentarios(cuerpo):
    import re
    cuerpo = re.sub(r'/\*.*?\*/', '', cuerpo, flags=re.S)
    cuerpo = re.sub(r'//[^\n]*', '', cuerpo)
    return cuerpo.strip()


def test_ningun_catch_nuevo_se_traga_el_error():
    """No catch in the mobile sources may swallow an error without producing a visible state.

    The spec's criterion, made behavioural: a body that is empty once its comments are removed
    swallows, whatever it is written like. `estado.js` is NOT allowlisted wholesale — its one
    deliberate `catch { detalle = ''; }` assigns, so it is not a swallow and does not need to be.
    """
    from pathlib import Path
    import re

    raiz = Path(__file__).resolve().parent.parent / "bunker_core/static/movil"
    encontrados = set()
    for fuente in sorted(raiz.glob("*.js")):        # glob no desciende: `dist/` queda fuera
        texto = fuente.read_text()
        for indice, cuerpo in _cuerpos_de_catch(texto):
            if _sin_comentarios(cuerpo):
                continue                            # hace algo: no se lo traga
            linea = texto.count('\n', 0, indice) + 1
            comentario = ' '.join(re.sub(r'[/*]', ' ', cuerpo).split())
            clave = next((c for c in TRAGADORES_CONOCIDOS
                          if c[0] == fuente.name and c[1] in comentario), None)
            check(clave is not None,
                  f"{fuente.name}:{linea} es un catch NUEVO que se traga el error "
                  f"sin producir estado: «{comentario[:60]}»")
            encontrados.add(clave)

    check(encontrados == TRAGADORES_CONOCIDOS,
          f"el inventario dejó de coincidir; ya no están: "
          f"{TRAGADORES_CONOCIDOS - encontrados}")


def run_tests():
    global _checks
    pruebas = [
        test_el_panel_no_escribe_nada,
        test_ningun_catch_nuevo_se_traga_el_error,
    ]
    with transaction.atomic():
        for prueba in pruebas:
            print(prueba.__name__)
            prueba()
        transaction.set_rollback(True)
    print(f"\ntest_panel: {len(pruebas)} pruebas, {_checks} checks")


if __name__ == "__main__":
    run_tests()
