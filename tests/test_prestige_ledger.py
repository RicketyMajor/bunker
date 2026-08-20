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

from posada.models import GuildProfile, PrestigeEntry  # noqa: E402

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


def run_tests():
    with transaction.atomic():
        test_invariante()
        test_saldo_inicial_existe()
        test_constraint_rechaza_cero()
        transaction.set_rollback(True)

    print(f"\ntest_prestige_ledger: {_checks}/{_checks}")


if __name__ == '__main__':
    run_tests()
