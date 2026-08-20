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
    review asks. The calendar left the sweep entirely in Task 4 (it expires unpaid now, see
    `test_evento_pasado_no_paga`), so two contributors remain. Plants its own habits: the live
    database has 0 habits defined, so an assertion resting on it would pass without being able
    to fail.

    It also pins the ORDER of the payments. `add_prestige` crosses `prestige_meta` against the
    balance it sees, `prestige_level` only ever goes up, and `DailyHabit.objects.all()` has no
    `Meta.ordering` — so paying a gross reward before a pending penalty granted a permanent
    level that depended on the order Postgres returned rows in.
    """
    _exige_rollback()
    from datetime import timedelta

    from django.utils import timezone

    from posada.engine.legacy import evaluate_daily_penalties

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
    antes = PrestigeEntry.objects.count()
    saldo_antes = GuildProfile.objects.get(id=1).prestige
    evaluate_daily_penalties()

    nuevas = list(PrestigeEntry.objects.order_by('id')[antes:])
    # Asserted on the PLANTED rows, never on the total. The sweep also processes whatever the
    # live database holds, and this check runs inside `bunker doctor`: the day a real habit
    # exists with an old `last_evaluated_date` — the app's main feature — a count of all new
    # rows goes red for a reason that has nothing to do with the ledger. This project already
    # lost a session to exactly that (`test_reading_progress`, fixed 2026-08-17).
    esperadas = {('habito_evitado', vicio.id), ('habito_incumplido', bueno.id)}
    plantadas = [f for f in nuevas if (f.source, f.ref_id) in esperadas]
    check(len(plantadas) == 2,
          f"la barrida escribe un asiento por evento plantado, escribió {len(plantadas)}")

    # El orden importa y es lo único que mantiene el nivel del gremio estable: la
    # penalización se paga ANTES que la recompensa, siempre.
    check([f.source for f in plantadas] == ['habito_incumplido', 'habito_evitado'],
          f"la barrida paga penalizaciones antes que recompensas, pagó "
          f"{[f.source for f in plantadas]}")

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
    # 2 días sobrevividos × 25 (dificultad A) y 2 días incumplidos × 15. Ambos reproducibles
    # desde su causa, que es lo que vuelve auditable una fila del ledger.
    check(por_fuente.get('habito_evitado') == 50,
          f"el vicio evitado paga exactamente lo suyo (+50), pagó {por_fuente.get('habito_evitado')}")
    check(por_fuente.get('habito_incumplido') == -30,
          f"el hábito incumplido cobra exactamente lo suyo (-30), cobró "
          f"{por_fuente.get('habito_incumplido')}")

    saldo = GuildProfile.objects.get(id=1).prestige
    check(sum(f.amount for f in nuevas) == saldo - saldo_antes,
          f"los asientos de la barrida suman el movimiento del saldo "
          f"({sum(f.amount for f in nuevas)} vs {saldo - saldo_antes})")


def test_evento_pasado_no_paga():
    """A past calendar event expires unpaid. It used to pay `random.randint(5, 15)` for
    merely existing — no attendance check anywhere — which is both the cheapest prestige in
    the project and a row whose amount cannot be reproduced from its cause.

    The sweep is `evaluate_daily_penalties()` at `posada/engine/legacy.py:446`, named here
    rather than looked up: a wrong import raises BEFORE the assert, and a check that crashes
    has proved nothing.
    """
    _exige_rollback()
    from datetime import timedelta

    from django.utils import timezone

    from posada.engine.legacy import evaluate_daily_penalties
    from posada.models import CalendarEvent

    evento = CalendarEvent.objects.create(date=timezone.localdate() - timedelta(days=3),
                                          title='Evento vencido de prueba', status='PENDING')
    antes = PrestigeEntry.objects.filter(ref_id=evento.id,
                                         source='evento_asistido').count()
    evaluate_daily_penalties()

    evento.refresh_from_db()
    check(evento.status == 'EXPIRED',
          f"un evento pasado debe vencer, quedó en '{evento.status}'")
    # Filtrado por el evento plantado, no por el total: la barrida también procesa lo que
    # haya en la base viva, y este check corre dentro de `bunker doctor`.
    check(PrestigeEntry.objects.filter(ref_id=evento.id, source='evento_asistido').count() == antes,
          "un evento vencido no escribe ningún asiento")


def test_confirmar_paga_fijo_y_una_vez():
    """Confirming attendance pays a fixed +3/+1, and only the first time.

    Driven through the real endpoint: the guard that makes confirming idempotent lives in the
    view, and a check that called `registrar_prestigio` directly would pass with the guard
    deleted. Without it the endpoint is a prestige faucet — a worse version of the defect
    this task removes.
    """
    _exige_rollback()
    from django.utils import timezone

    from posada.models import CalendarEvent

    evento = CalendarEvent.objects.create(date=timezone.localdate(), title='Importante',
                                          is_important=True, status='PENDING')
    cliente = Client()
    respuesta = cliente.post(f'/posada/api/calendar/{evento.id}/asistir/')
    check(respuesta.status_code == 200,
          f"confirmar responde 200, respondió {respuesta.status_code}")

    asiento = PrestigeEntry.objects.filter(ref_id=evento.id,
                                           source='evento_asistido').order_by('-id').first()
    check(asiento is not None, "confirmar asistencia deja un asiento en el ledger")
    check(asiento.amount == 3,
          f"un evento importante paga exactamente 3, pagó {asiento.amount}")

    evento.refresh_from_db()
    check(evento.status == 'DONE', f"el evento queda en DONE, quedó en '{evento.status}'")

    antes = PrestigeEntry.objects.filter(ref_id=evento.id, source='evento_asistido').count()
    cliente.post(f'/posada/api/calendar/{evento.id}/asistir/')
    despues = PrestigeEntry.objects.filter(ref_id=evento.id, source='evento_asistido').count()
    check(despues == antes,
          f"confirmar dos veces no puede pagar dos veces, pasó de {antes} a {despues}")

    # Un evento normal paga 1, no 3: el monto sale de su causa, no de un dado.
    normal = CalendarEvent.objects.create(date=timezone.localdate(), title='Normal',
                                          is_important=False, status='PENDING')
    cliente.post(f'/posada/api/calendar/{normal.id}/asistir/')
    asiento = PrestigeEntry.objects.filter(ref_id=normal.id,
                                           source='evento_asistido').order_by('-id').first()
    check(asiento is not None and asiento.amount == 1,
          f"un evento normal paga exactamente 1, pagó {asiento and asiento.amount}")


def _planta_en_semana_cerrada(monto, detalle):
    """One entry inside the LAST COMPLETE week, written straight to the table.

    Not through `registrar_prestigio`: that stamps `occurred_at` with now, and every one of
    these checks is about a week that has already closed. It puts `SUM(ledger)` out of step
    with the balance, which is why the Task 5 checks run LAST — `test_invariante` and every
    check that calls it have already passed by then, and the whole run rolls back.
    """
    from datetime import timedelta

    from django.utils import timezone

    hoy = timezone.localdate()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    momento = timezone.make_aware(
        timezone.datetime.combine(lunes_actual - timedelta(days=4),
                                  timezone.datetime.min.time()))
    return PrestigeEntry.objects.create(amount=monto, source='diario', detail=detalle,
                                        occurred_at=momento)


def test_clave_semana_ida_y_vuelta():
    """`_rango_semana` is the inverse of `_clave_semana`, and nothing else may parse the key.

    Two functions that agree on a format until one of them changes is how a week silently
    starts reporting the wrong seven days. Checked across a year boundary too: week 1 of a
    year can start in December, and `date.fromisocalendar` is the only thing that gets that
    right on its own.
    """
    from bunker_core.briefing import _clave_semana
    from posada.prestige import _rango_semana

    for clave in ('2026-W34', '2026-W01', '2026-W53', '2027-W01', '2025-W52'):
        try:
            lunes, siguiente = _rango_semana(clave)
        except ValueError:
            # 2026 no tiene semana 53; que reviente es correcto, no hay nada que afirmar.
            continue
        check(_clave_semana(lunes) == clave,
              f"la clave {clave} vuelve de su lunes como {_clave_semana(lunes)}")
        check((siguiente - lunes).days == 7,
              f"la semana {clave} dura 7 días, duró {(siguiente - lunes).days}")


def test_net_no_se_puede_escribir():
    """`net` is a stored generated column: the database computes it from `earned - lost`.

    Writing it from the application is the one way a snapshot could be WRONG rather than
    merely stale, which is the distinction the model exists to make. This pins that it stays
    a generated column and does not quietly become a plain integer field in a later
    migration.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT is_generated FROM information_schema.columns
            WHERE table_name = 'posada_prestigeweek' AND column_name = 'net'""")
        generada = cursor.fetchone()[0]
    check(generada == 'ALWAYS',
          f"la columna net debe ser generada por la base, is_generated={generada!r}")


def test_snapshot_cuadra_con_ledger():
    """Every stored snapshot must equal what the ledger says for its week. Same shape as
    `SUM(ledger) == prestige` is for Task 1: the assertion that goes red when the derived
    number and its source drift apart."""
    _exige_rollback()
    from bunker_core.briefing import _semana_anterior
    from posada.models import PrestigeWeek
    from posada.prestige import _rango_semana, resumen_semana

    _planta_en_semana_cerrada(7, 'Semilla del snapshot')
    resumen_semana(_semana_anterior())

    filas = list(PrestigeWeek.objects.all())
    check(bool(filas), f"debe existir al menos un snapshot para comprobar, hay {len(filas)}")
    for fila in filas:
        lunes, siguiente = _rango_semana(fila.week_key)
        real = sum(PrestigeEntry.objects.filter(
            occurred_at__date__gte=lunes,
            occurred_at__date__lt=siguiente).values_list('amount', flat=True))
        check(fila.net == real,
              f"el snapshot {fila.week_key} dice net={fila.net}, el ledger dice {real}")


def test_snapshot_es_cache_y_es_derivable():
    """Two properties in one run, because either alone passes against a broken cache.

    Building the snapshot and immediately recomputing it proves nothing: both calls take the
    same path. Adding an entry BETWEEN them is what makes the two paths tell different
    stories — the cached read must return the OLD number (it really is a cache) and the read
    after deleting the snapshots must return the NEW one (it really is derivable from the
    ledger, and stale is the worst it can ever be).
    """
    _exige_rollback()
    from bunker_core.briefing import _semana_anterior
    from posada.models import PrestigeWeek
    from posada.prestige import resumen_semana

    clave = _semana_anterior()
    # Deltas, nunca absolutos: `test_snapshot_cuadra_con_ledger` ya plantó en esta misma
    # semana y dejó su fila. Un check que afirma un número fijo afirma en realidad el orden
    # en que corrieron los checks anteriores.
    PrestigeWeek.objects.all().delete()
    _planta_en_semana_cerrada(10, 'Primer asiento de la semana cerrada')
    primero = resumen_semana(clave)
    check(PrestigeWeek.objects.filter(week_key=clave).exists(),
          f"una semana cerrada deja su fila de snapshot, {clave} no la dejó")

    _planta_en_semana_cerrada(5, 'Asiento posterior al snapshot')
    cacheado = resumen_semana(clave)
    check(cacheado == primero,
          f"el snapshot es una caché y debe devolver lo viejo: {cacheado} vs {primero}")

    PrestigeWeek.objects.all().delete()
    reconstruido = resumen_semana(clave)
    check(reconstruido['earned'] == primero['earned'] + 5,
          f"sin caché se reconstruye desde el ledger y suma los +5 posteriores: "
          f"{primero['earned']} -> {reconstruido['earned']}")
    check(reconstruido['net'] == reconstruido['earned'] - reconstruido['lost'],
          f"el net reconstruido sale de sus dos columnas: {reconstruido}")


def test_semana_en_curso_no_se_guarda():
    """The week in progress is never cached — its number is still moving, and the review
    reports complete periods only. A future week is not cached either: it would be stored as
    a zero and hand that zero back the day it finally has entries."""
    _exige_rollback()
    from bunker_core.briefing import _semana_actual
    from posada.models import PrestigeWeek
    from posada.prestige import resumen_semana

    actual = _semana_actual()
    resumen_semana(actual)
    check(not PrestigeWeek.objects.filter(week_key=actual).exists(),
          f"la semana en curso {actual} no puede tener fila de snapshot")

    futura = '2099-W10'
    resumen_semana(futura)
    check(not PrestigeWeek.objects.filter(week_key=futura).exists(),
          f"una semana futura {futura} tampoco puede cachearse")


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
        test_evento_pasado_no_paga()
        test_confirmar_paga_fijo_y_una_vez()
        # Las de la Tarea 5 van AL FINAL: plantan asientos con fecha pasada sin pasar por
        # `registrar_prestigio`, así que dejan `SUM(ledger)` fuera de paso con el saldo.
        test_clave_semana_ida_y_vuelta()
        test_net_no_se_puede_escribir()
        test_snapshot_cuadra_con_ledger()
        test_snapshot_es_cache_y_es_derivable()
        test_semana_en_curso_no_se_guarda()
        transaction.set_rollback(True)

    print(f"\ntest_prestige_ledger: {_checks}/{_checks}")


if __name__ == '__main__':
    run_tests()
