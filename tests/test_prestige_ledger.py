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


def run_tests():
    with transaction.atomic():
        test_invariante()
        test_saldo_inicial_existe()
        test_constraint_rechaza_cero()
        test_recaida_escribe_negativo()
        test_subida_de_nivel_escribe_su_asiento()
        transaction.set_rollback(True)

    print(f"\ntest_prestige_ledger: {_checks}/{_checks}")


if __name__ == '__main__':
    run_tests()
