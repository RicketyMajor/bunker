"""Checks for the prestige ledger. Runs inside the container:

    docker compose exec -T web python -m tests.test_prestige_ledger

`GuildProfile.prestige` is a BALANCE, not a running total — `add_prestige()` subtracts
`prestige_meta` on every level-up — so nothing about a period was recoverable from it.
`PrestigeEntry` is the history that fixes that, and this file is what keeps it honest.

THE INVARIANT IS THE WHOLE POINT: SUM(PrestigeEntry.amount) == GuildProfile.prestige.
It is the one assertion that goes red when someone adds a payer that does not route through
`posada.prestige.registrar_prestigio` — which is exactly how the relapse at `views.py:663`
escaped `add_prestige()` for the entire life of the project before this ledger existed.

Everything that writes runs inside `transaction.atomic()` with a forced rollback, so this
check leaves the live database exactly as it found it.
"""
import os
import pathlib

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402
from django.db.models import Sum  # noqa: E402

from django.test import Client  # noqa: E402

from posada.models import DailyHabit, GuildProfile, PrestigeEntry  # noqa: E402

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _exige_rollback():
    """These checks drive endpoints that DELETE live rows — `reset_guild` wipes every
    adventurer, inventory and upgrade — and are safe only because `run_tests()` wraps them in
    `transaction.atomic()` with a forced rollback. Nothing in the module enforced that, and
    the functions are plain module-level `test_*` names: importing one and calling it, or any
    future runner that collects `test_*`, would wipe the guild irreversibly. Cheap guard, and
    the failure it prevents is not recoverable."""
    from django.db import connection
    assert connection.in_atomic_block, (
        "este check escribe en la base VIVA y solo es seguro dentro de "
        "transaction.atomic() con rollback forzado — úsalo vía run_tests()")


def test_invariante():
    """SUM(ledger) == GuildProfile.prestige, exactly.

    Read as a function so the inversion in the plan can call it in isolation against a
    deliberately broken balance and watch it fail BY NAME, at the assert.
    """
    total = PrestigeEntry.objects.aggregate(s=Sum('amount'))['s'] or 0
    saldo = GuildProfile.objects.get(id=1).prestige
    check(total == saldo,
          f"SUM(ledger)={total} debe igualar GuildProfile.prestige={saldo}")


def test_saldo_inicial_existe():
    """The opening entry the migration wrote. Without it the two numbers start 102 apart
    with nothing to explain the gap, and the invariant above could never hold."""
    filas = PrestigeEntry.objects.filter(source=PrestigeEntry.SALDO_INICIAL)
    check(filas.count() == 1,
          f"debe haber exactamente 1 asiento de saldo inicial, hay {filas.count()}")


def test_constraint_rechaza_cero():
    """A zero entry carries no information and hides a confused caller. The CHECK
    constraint is what makes that a database-level guarantee rather than a convention."""
    from django.db.utils import IntegrityError
    try:
        with transaction.atomic():
            PrestigeEntry.objects.create(amount=0, source='diario', detail='cero')
    except IntegrityError:
        check(True, "la base de datos rechaza un asiento de monto cero")
    else:
        check(False, "un asiento de monto cero fue aceptado y no debería")


def test_recaida_escribe_negativo():
    """A relapse, driven through the REAL endpoint, writes exactly one negative entry.

    Deliberately NOT a direct call to `registrar_prestigio`: that would pass even if
    `views.py` went back to writing `guild.prestige -= penalty` by hand, which is the exact
    regression this check exists to catch. Aiming a check where the defect cannot appear
    proves nothing — the rule this project paid for twice, in handoffs 021 and 022.

    The habit is created here because the live database has ZERO habits defined (measured
    2026-08-20), so there is nothing to relapse on and the endpoint could never be exercised
    by whatever happens to be stored.
    """
    _exige_rollback()
    habito = DailyHabit.objects.create(
        name='Recaída de prueba', is_bad_habit=True, difficulty='B', valid_days='0123456')
    saldo_antes = GuildProfile.objects.get(id=1).prestige
    antes = PrestigeEntry.objects.count()

    resp = Client().post('/posada/api/habits/complete/',
                         {'habit_id': habito.id}, content_type='application/json')
    check(resp.status_code == 200,
          f"el endpoint de recaída responde 200, respondió {resp.status_code}")

    check(PrestigeEntry.objects.count() == antes + 1,
          f"una recaída escribe exactamente un asiento, escribió "
          f"{PrestigeEntry.objects.count() - antes}")

    e = PrestigeEntry.objects.order_by('-id').first()
    # Dificultad B paga 5, y la recaída cuesta el doble.
    check(e.amount == -10, f"el asiento de recaída debe ser -10, fue {e.amount}")
    check(e.source == 'recaida', f"la fuente debe ser 'recaida', fue '{e.source}'")
    check(e.ref_id == habito.id,
          f"el asiento apunta al hábito {habito.id}, apuntó a {e.ref_id}")

    saldo_después = GuildProfile.objects.get(id=1).prestige
    check(saldo_después == saldo_antes - 10,
          f"el saldo bajó de {saldo_antes} a {saldo_antes - 10}, quedó en {saldo_después}")
    # Y el invariante sigue en pie DESPUÉS del movimiento, que es lo que prueba que el
    # asiento y el saldo se escribieron juntos y no por separado.
    test_invariante()


def test_subida_de_nivel_escribe_su_asiento():
    """Crossing a level writes a `-prestige_meta` entry, or SUM(ledger) diverges from the
    balance permanently at the first crossing.

    THIS BRANCH HAS NEVER RUN IN PRODUCTION. The guild is level 1 with 102 of 500 (measured
    2026-08-20), so live data cannot make it fire and the check has to drive it on purpose —
    an assertion that can only go red one day a year has not been tested, it has been
    scheduled.
    """
    from posada.prestige import registrar_prestigio
    guild = GuildProfile.objects.get(id=1)
    nivel_antes, meta = guild.prestige_level, guild.prestige_meta
    falta = meta - guild.prestige

    subió = registrar_prestigio(guild, falta, 'meta_completada', detail='Cruce forzado')
    check(subió is True, "registrar_prestigio devuelve True cuando el gremio sube de nivel")
    check(guild.prestige_level == nivel_antes + 1,
          f"el nivel sube de {nivel_antes} a {nivel_antes + 1}, quedó en {guild.prestige_level}")

    asiento = PrestigeEntry.objects.filter(source=PrestigeEntry.SUBIDA_NIVEL).order_by('-id').first()
    check(asiento is not None, "la subida de nivel deja un asiento propio en el ledger")
    check(asiento.amount == -meta,
          f"el asiento de subida debe ser -{meta}, fue {asiento.amount}")
    # Lo único que importa de todo esto: el invariante sobrevive a un cruce de nivel.
    test_invariante()


def test_todas_las_fuentes_declaradas():
    r"""Every source a payer passes must exist in `FUENTES`, and every payer must pass one.

    The runtime guard in `registrar_prestigio` raises on an undeclared source, but only when
    that payer actually runs: the bestiary pays on a first monster discovery and a chart goal
    on completion, both of which can go months without firing. This reads the call sites
    statically, so a typo fails today instead of the night the path finally executes.

    Walks the AST rather than grepping, and not for elegance — two regexes were tried and
    both were WRONG against this codebase. `add_prestige\([^,]+,` silently skips any payer
    whose amount contains a comma (`reward_map.get(habit.difficulty, 5) * days`), and a
    skipped payer leaves the check green. Making it non-greedy instead matched the dict key
    inside `add_prestige(r['prestige'], 'habito_bueno')` and reported `'prestige'` as a
    source. The AST knows which argument is which; a regex is guessing.
    """
    import ast

    raiz = pathlib.Path(__file__).resolve().parent.parent
    usadas, sin_fuente, sitios = set(), [], 0
    for archivo in raiz.rglob('*.py'):
        # `tests` is excluded on purpose: this file passes a deliberately invalid source to
        # prove the runtime guard, and the scan audits production payers.
        if {'.venv', 'migrations', 'tests'} & set(archivo.parts):
            continue
        try:
            arbol = ast.parse(archivo.read_text(encoding='utf-8', errors='ignore'))
        except SyntaxError:
            continue
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = (nodo.func.attr if isinstance(nodo.func, ast.Attribute)
                      else getattr(nodo.func, 'id', None))
            if nombre not in ('add_prestige', 'registrar_prestigio'):
                continue
            sitios += 1
            # `source` va en la posición 1 del método y en la 2 de la función.
            posicion = 1 if nombre == 'add_prestige' else 2
            argumento = (nodo.args[posicion] if len(nodo.args) > posicion else
                         next((k.value for k in nodo.keywords if k.arg == 'source'), None))
            if argumento is None:
                sin_fuente.append(f"{archivo.name}:{nodo.lineno}")
            elif isinstance(argumento, ast.Constant) and isinstance(argumento.value, str):
                usadas.add(argumento.value)
            # Cualquier otra cosa es una fuente dinámica; de esa se encarga la guardia
            # en tiempo de ejecución, que es el único sitio donde su valor existe.

    check(sitios > 10, f"el escaneo debe encontrar los pagadores, encontró {sitios} llamadas")
    check(not sin_fuente,
          f"todo pagador pasa su fuente, la omiten: {sin_fuente or '—'}")
    faltan = usadas - {clave for clave, _ in PrestigeEntry.FUENTES}
    check(not faltan, f"fuentes usadas y no declaradas en FUENTES: {faltan or '—'}")


def test_fuente_inventada_revienta():
    """The runtime half of the same guard, aimed at the paths grep cannot read — a source
    held in a variable or built with an f-string."""
    from posada.prestige import registrar_prestigio
    guild = GuildProfile.objects.get(id=1)
    try:
        registrar_prestigio(guild, 1, 'fuente_inventada')
        reventó = False
    except ValueError:
        reventó = True
    check(reventó, "una fuente no declarada debe reventar en registrar_prestigio")


def test_reinicio_del_gremio_mantiene_el_invariante():
    """The reset endpoint used to write `guild.prestige = 0` by hand — the SECOND payer to
    bypass the choke point, after the relapse, and the one the plan's table did not list.

    Driven through the real endpoint on purpose: calling `registrar_prestigio` here would
    pass just as happily while `views.py` zeroed the balance behind its back. Third rule
    from handoff 023, and the reason this check exists at all.
    """
    _exige_rollback()
    # Plants its own balance: the level-up check above runs first and leaves the guild at 0,
    # where the reset has nothing to compensate and this check would pass without being able
    # to fail. An assertion that depends on what ran before it is not an assertion.
    from posada.prestige import registrar_prestigio
    registrar_prestigio(GuildProfile.objects.get(id=1), 37, 'diario',
                        detail='Saldo plantado para el reinicio')

    saldo_antes = GuildProfile.objects.get(id=1).prestige
    asientos_antes = PrestigeEntry.objects.count()

    respuesta = Client().post('/posada/api/guild/reset/',
                              data='{}', content_type='application/json')
    check(respuesta.status_code == 200,
          f"el endpoint de reinicio responde 200, respondió {respuesta.status_code}")

    guild = GuildProfile.objects.get(id=1)
    check(guild.prestige == 0, f"el reinicio deja el saldo en 0, quedó en {guild.prestige}")
    check(PrestigeEntry.objects.count() == asientos_antes + 1,
          f"el reinicio escribe exactamente un asiento compensatorio, escribió "
          f"{PrestigeEntry.objects.count() - asientos_antes}")

    asiento = PrestigeEntry.objects.order_by('-id').first()
    check(asiento.amount == -saldo_antes,
          f"el asiento compensatorio debe ser -{saldo_antes}, fue {asiento.amount}")
    check(asiento.source == 'reinicio_gremio',
          f"la fuente debe ser 'reinicio_gremio', fue '{asiento.source}'")
    # Y lo único que importa: el ledger sigue explicando el saldo DESPUÉS del reinicio.
    test_invariante()


def test_barrida_no_netea():
    """The nightly sweep writes one entry per event, not one netted payment.

    It used to accumulate three different things — a vice avoided, a habit missed, a calendar
    event — into `total_prestige_change` and pay them with a single `add_prestige()`. A `+35`
    row cannot say whether the week was good or bad, which is the entire question the weekly
    review asks. Plants its own habits and event: the live database has 0 habits defined, so
    an assertion resting on it would pass without being able to fail.
    """
    _exige_rollback()
    from datetime import timedelta

    from django.utils import timezone

    from posada.engine.legacy import evaluate_daily_penalties
    from posada.models import CalendarEvent

    hoy = timezone.localdate()
    todos_los_dias = ''.join(str(d) for d in range(7))

    vicio = DailyHabit.objects.create(name='Vicio de prueba', is_bad_habit=True,
                                      difficulty='A', valid_days=todos_los_dias,
                                      last_evaluated_date=hoy - timedelta(days=3))
    bueno = DailyHabit.objects.create(name='Virtud de prueba', is_bad_habit=False,
                                      difficulty='B', valid_days=todos_los_dias,
                                      last_evaluated_date=hoy - timedelta(days=3))
    # `created_at` is auto_now_add, and the missed-days window starts at max(eval, created),
    # so a habit born today has no uncovered days and this check would silently cover only
    # two of the three contributors.
    DailyHabit.objects.filter(pk=bueno.pk).update(created_at=hoy - timedelta(days=10))
    evento = CalendarEvent.objects.create(date=hoy - timedelta(days=2),
                                          title='Evento de prueba', status='PENDING')

    antes = PrestigeEntry.objects.count()
    saldo_antes = GuildProfile.objects.get(id=1).prestige
    evaluate_daily_penalties()

    nuevas = list(PrestigeEntry.objects.order_by('id')[antes:])
    # Asserted on the PLANTED rows, never on the total. The sweep also processes whatever the
    # live database holds, and this check runs inside `bunker doctor`: the day a real habit
    # exists with an old `last_evaluated_date` — the app's main feature — a count of all new
    # rows goes red for a reason that has nothing to do with the ledger. This project already
    # lost a session to exactly that (`test_reading_progress`, fixed 2026-08-17).
    esperadas = {('habito_evitado', vicio.id), ('habito_incumplido', bueno.id),
                 ('evento_asistido', evento.id)}
    plantadas = [f for f in nuevas if (f.source, f.ref_id) in esperadas]
    check(len(plantadas) == 3,
          f"la barrida escribe un asiento por evento plantado, escribió {len(plantadas)}")

    # Counting rows and sources is NOT enough, and this was measured: restoring the netted
    # payment under one of those three labels produces three rows and three sources too, and
    # an earlier version of this check passed against the very regression it exists for.
    # What a netted row cannot do is name its cause. Over ALL new rows, not just the planted
    # ones — the netted row is precisely the one that would not match a planted cause.
    sin_causa = [f for f in nuevas if f.ref_id is None or not f.detail]
    check(not sin_causa,
          f"cada asiento de la barrida apunta a la fila que lo causó, sin causa: "
          f"{[(f.source, f.amount) for f in sin_causa]}")

    por_fuente = {f.source: f.amount for f in plantadas}
    # 2 días sobrevividos × 25 (dificultad A) y 2 días incumplidos × 15. El evento paga
    # random.randint(5, 15) — no se puede afirmar hasta que la Tarea 4 lo vuelva fijo.
    check(por_fuente.get('habito_evitado') == 50,
          f"el vicio evitado paga exactamente lo suyo (+50), pagó {por_fuente.get('habito_evitado')}")
    check(por_fuente.get('habito_incumplido') == -30,
          f"el hábito incumplido cobra exactamente lo suyo (-30), cobró "
          f"{por_fuente.get('habito_incumplido')}")

    saldo = GuildProfile.objects.get(id=1).prestige
    check(sum(f.amount for f in nuevas) == saldo - saldo_antes,
          f"los asientos de la barrida suman el movimiento del saldo "
          f"({sum(f.amount for f in nuevas)} vs {saldo - saldo_antes})")


def run_tests():
    with transaction.atomic():
        test_invariante()
        test_saldo_inicial_existe()
        test_constraint_rechaza_cero()
        test_recaida_escribe_negativo()
        test_subida_de_nivel_escribe_su_asiento()
        test_todas_las_fuentes_declaradas()
        test_fuente_inventada_revienta()
        test_reinicio_del_gremio_mantiene_el_invariante()
        test_barrida_no_netea()
        transaction.set_rollback(True)

    print(f"\ntest_prestige_ledger: {_checks}/{_checks}")


if __name__ == '__main__':
    run_tests()
