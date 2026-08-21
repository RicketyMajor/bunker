"""The only path by which prestige may move.

Fourteen call sites paid prestige before this module existed and ONE of them — the relapse
at `views.py:663` — wrote `guild.prestige` directly, skipping `add_prestige()` entirely. A
ledger hooked into `add_prestige` alone would have silently missed every relapse, which is
the event a weekly review most wants to show.

A guard in the shared function is a smaller diff than a guard in every caller, and it leaves
no route by which a payment reaches the balance without reaching the ledger. That property is
what `tests/test_prestige_ledger.py::test_invariante` exists to defend.
"""
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from .models import PrestigeEntry, PrestigeWeek


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
    if source not in dict(PrestigeEntry.FUENTES):
        # Django validates `choices` only on full_clean(), which .create() never calls, so a
        # typo would land in the ledger and render as a raw slug in the weekly review. The
        # payers that would carry one — the bestiary, a chart goal — fire once in months, so
        # a wrong label has to fail at the call, not whenever the path next happens to run.
        raise ValueError(f"fuente de prestigio no declarada en PrestigeEntry.FUENTES: {source!r}")

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


def _rango_semana(week_key):
    """Monday 00:00 and the following Monday 00:00, local, for an ISO key like '2026-W34'.

    The inverse of `bunker_core.briefing._clave_semana`, which is the ONE producer of the
    format. `tests/test_prestige_ledger.py::test_clave_semana_ida_y_vuelta` pins the round
    trip, because two functions that agree on a format until one of them changes is exactly
    how a week silently starts reporting the wrong seven days.
    """
    anio, semana = int(week_key[:4]), int(week_key[6:])
    lunes = date.fromisocalendar(anio, semana, 1)
    return lunes, lunes + timedelta(days=7)


def _calcular(week_key):
    """Sum the ledger for one ISO week. The ONE producer of the number.

    It never reads the cache, deliberately: `snapshot_semana` needs a rebuild to actually
    rebuild, and a rebuild that returns the row it is trying to replace is not one.
    """
    lunes, siguiente = _rango_semana(week_key)
    # ponytail: suma en Python sobre las filas, una sola consulta. Techo: una semana con
    # miles de asientos — la historia entera son ~150 filas y una semana son unidades.
    # Mejora: dos `Sum` condicionales, que también es una consulta y se lee peor por nada.
    montos = PrestigeEntry.objects.filter(
        occurred_at__date__gte=lunes, occurred_at__date__lt=siguiente
    ).values_list('amount', flat=True)
    ganado = sum(m for m in montos if m > 0)
    perdido = -sum(m for m in montos if m < 0)
    return {"earned": ganado, "lost": perdido, "net": ganado - perdido}


def resumen_semana(week_key):
    """Summary for one ISO week: `{"earned", "lost", "net"}`. **Pure read.**

    It used to persist the snapshot itself, which made `GET /api/briefing/` a GET that writes.
    A GET is supposed to be safe, and the panel of `specs/movil-v3.md` asserts that nothing it
    calls changes a row — so this one write broke that criterion before the panel had shipped a
    line. The write moved to `snapshot_semana`, called from `marcar_visto`: the POST that
    exists precisely because it writes. 2026-08-21.

    A closed week with no snapshot row is recomputed from the ledger on every read instead of
    once. Accepted: the whole history is ~150 rows and a week is units — the same reasoning the
    `ponytail:` marker in `_calcular` already carries.
    """
    lunes, siguiente = _rango_semana(week_key)
    # Estrictamente pasada. `not en_curso` metería también las semanas FUTURAS, que se
    # cachearían en cero y devolverían ese cero cuando por fin tuvieran asientos.
    if siguiente <= timezone.localdate():
        fila = PrestigeWeek.objects.filter(week_key=week_key).first()
        if fila:
            return {"earned": fila.earned, "lost": fila.lost, "net": fila.net}
    return _calcular(week_key)


def snapshot_semana(week_key):
    """Persist one week's summary. **The only writer of `PrestigeWeek` in the project.**

    Returns `None` without writing for a week still in progress, or a future one: its number
    is still moving, and a zero cached today is the zero handed back the day that week finally
    has entries.
    """
    _, siguiente = _rango_semana(week_key)
    if siguiente > timezone.localdate():
        return None
    datos = _calcular(week_key)
    # `update_or_create` y no `create`: reconstruir una semana que ya tiene fila debe dar la
    # misma fila, no un error de clave duplicada. `net` NO va aquí — lo calcula la base, y
    # escribirlo desde la aplicación es justo lo que esta tabla no permite.
    fila, _creada = PrestigeWeek.objects.update_or_create(
        week_key=week_key, defaults={"earned": datos["earned"], "lost": datos["lost"]})
    return fila
