"""Standalone checks for `GET /api/panel/`, the consultation surface's only data source.

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

from datetime import timedelta  # noqa: E402

from django.db import connection, transaction  # noqa: E402
from django.test import Client  # noqa: E402
from django.utils import timezone  # noqa: E402

from posada.models import (Achievement, DailyHabit, DeepWorkSession,  # noqa: E402
                           GuildProfile, PrestigeEntry)

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


def test_prestigio_sale_del_ledger_no_del_saldo():
    """The panel's total must be SUM(PrestigeEntry), never `GuildProfile.prestige`.

    The two numbers are made to DISAGREE on purpose. With the balance equal to the sum — which
    is the invariant the rest of the project maintains — a panel reading the wrong field passes
    the check, and this is exactly the confusion `PrestigeEntry` was created to end.
    """
    _exige_rollback()
    gremio = GuildProfile.objects.get(id=1)
    gremio.prestige = 7
    gremio.save()
    PrestigeEntry.objects.create(amount=50, source='diario', detail='Asiento del check del panel')

    total_ledger = sum(PrestigeEntry.objects.values_list('amount', flat=True))
    check(total_ledger != gremio.prestige,
          f"el check exige que difieran: ledger {total_ledger} vs saldo {gremio.prestige}")

    reportado = _panel()['prestigio']['total']
    check(reportado == total_ledger,
          f"el panel reporta {reportado}, el ledger suma {total_ledger}")
    check(reportado != gremio.prestige,
          f"el panel está leyendo GuildProfile.prestige ({gremio.prestige}), no el ledger")


def test_los_habitos_son_los_de_hoy_hechos_incluidos():
    """The panel lists today's habits WITH their done flag, and never a habit off its schedule.

    Three planted rows separate three things a weaker check collapses: one due and pending, one
    due and already done, one scheduled for a different weekday. A panel that simply lists every
    `DailyHabit` passes an assertion that only counts, so this one names them.
    """
    _exige_rollback()
    hoy = timezone.localdate()
    otro_dia = (hoy.weekday() + 3) % 7

    DailyHabit.objects.create(name='AAA pendiente de hoy',
                              valid_days=str(hoy.weekday()))
    DailyHabit.objects.create(name='BBB hecho hoy',
                              valid_days=str(hoy.weekday()), last_completed_date=hoy)
    DailyHabit.objects.create(name='CCC de otro día', valid_days=str(otro_dia))

    habitos = {h['nombre']: h for h in _panel()['habitos']}
    check('AAA pendiente de hoy' in habitos, f"falta el hábito pendiente de hoy: {list(habitos)}")
    check('BBB hecho hoy' in habitos,
          "el panel esconde los hábitos ya hechos; muestra 'cómo voy', no 'qué falta'")
    check('CCC de otro día' not in habitos,
          "el panel ofrece un hábito que hoy NO toca — eso paga un día que el motor no puntúa")
    check(habitos['AAA pendiente de hoy']['hecho'] is False, "el pendiente aparece como hecho")
    check(habitos['BBB hecho hoy']['hecho'] is True, "el hecho aparece como pendiente")


def test_los_logros_son_los_desbloqueados_mas_recientes():
    """Only unlocked achievements, newest first. `unlocked_at IS NULL` means locked."""
    _exige_rollback()
    ahora = timezone.now()
    Achievement.objects.create(key='chk-viejo', name='Logro viejo', metric='x',
                               unlocked_at=ahora - timedelta(days=30))
    Achievement.objects.create(key='chk-nuevo', name='Logro nuevo', metric='x',
                               unlocked_at=ahora - timedelta(days=1))
    Achievement.objects.create(key='chk-bloqueado', name='Logro bloqueado', metric='x')

    nombres = [l['nombre'] for l in _panel()['logros']]
    check('Logro bloqueado' not in nombres, f"el panel muestra un logro BLOQUEADO: {nombres}")
    check('Logro nuevo' in nombres and 'Logro viejo' in nombres,
          f"faltan logros desbloqueados: {nombres}")
    check(nombres.index('Logro nuevo') < nombres.index('Logro viejo'),
          f"los logros no vienen del más reciente al más viejo: {nombres}")


def test_la_bitacora_es_la_ultima_sesion_y_no_reejecuta_nada():
    """The last session's persisted `event_log`, read and never regenerated.

    The rollback guard plus this check's own census are what prove the block cannot pay: reading
    a JSONField cannot mint prestige, and if some future version regenerated the log it would
    route through the engine and the ledger would move. So the ledger is counted across the call.
    """
    _exige_rollback()
    antes = PrestigeEntry.objects.count()
    sesion = DeepWorkSession.objects.create(
        duration_minutes=50, category='CHK categoría de la bitácora', completed=True,
        survived_minutes=37, event_log=['CHK primer evento', 'CHK segundo evento'],
        start_time=timezone.now() + timedelta(minutes=5))   # la más reciente, a propósito

    bitacora = _panel()['bitacora']
    check(bitacora is not None, "el panel no trae bitácora habiendo una sesión")
    check(bitacora['categoria'] == sesion.category,
          f"la bitácora no es la última sesión: {bitacora['categoria']}")
    check(bitacora['eventos'] == ['CHK primer evento', 'CHK segundo evento'],
          f"el event_log no llegó entero: {bitacora['eventos']}")
    check(bitacora['minutos'] == 37,
          f"minutos debe ser lo SOBREVIVIDO (37), no el objetivo (50): {bitacora['minutos']}")
    check(PrestigeEntry.objects.count() == antes,
          "leer el panel movió el ledger — la bitácora está re-ejecutando el motor")


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
    for url in ('/panel/', '/api/panel/', '/api/stats/timeline/?module=books'):
        respuesta = cliente.get(url)
        check(respuesta.status_code == 200,
              f"{url} responde 200, dio {respuesta.status_code}")
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
        test_prestigio_sale_del_ledger_no_del_saldo,
        test_los_habitos_son_los_de_hoy_hechos_incluidos,
        test_los_logros_son_los_desbloqueados_mas_recientes,
        test_la_bitacora_es_la_ultima_sesion_y_no_reejecuta_nada,
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
