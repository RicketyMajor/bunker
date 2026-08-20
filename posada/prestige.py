"""The only path by which prestige may move.

Fourteen call sites paid prestige before this module existed and ONE of them — the relapse
at `views.py:663` — wrote `guild.prestige` directly, skipping `add_prestige()` entirely. A
ledger hooked into `add_prestige` alone would have silently missed every relapse, which is
the event a weekly review most wants to show.

A guard in the shared function is a smaller diff than a guard in every caller, and it leaves
no route by which a payment reaches the balance without reaching the ledger. That property is
what `tests/test_prestige_ledger.py::test_invariante` exists to defend.
"""
from django.db import transaction

from .models import PrestigeEntry


def registrar_prestigio(guild, amount, source, detail="", ref_id=None):
    """Move prestige and record it, atomically. Returns True if the guild leveled up.

    `amount` is signed: relapses, undos and missed habits are negative.

    A zero amount saves the guild WITHOUT writing an entry. That is not a shortcut — several
    callers compute an amount that can legitimately come out zero, the CHECK constraint
    forbids a zero row, and `achievements.py` sets a coin reward on `guild` and relies on
    this call to persist the whole row. Returning early without saving would silently drop
    that coin the day an achievement pays 0 prestige. There are none today; there was no
    reason to leave the trap armed.
    """
    if amount == 0:
        guild.save()
        return False

    with transaction.atomic():
        PrestigeEntry.objects.create(
            amount=amount, source=source, detail=detail[:120], ref_id=ref_id)
        guild.prestige += amount

        leveled_up = False
        while guild.prestige >= guild.prestige_meta:
            meta = guild.prestige_meta
            guild.prestige -= meta
            guild.prestige_level += 1
            leveled_up = True
            # The subtraction is a movement like any other, or SUM(ledger) diverges from the
            # balance permanently at the first crossing. The guild has never leveled up in
            # production (level 1, 102 of 500 on 2026-08-20), so this branch has no live data
            # and any check that covers it must drive it deliberately.
            PrestigeEntry.objects.create(
                amount=-meta, source=PrestigeEntry.SUBIDA_NIVEL,
                detail=f"Ascenso a nivel {guild.prestige_level}")

        guild.save()
        return leveled_up
