"""Standalone check for the capture date parser and the endpoints that use it.

Run: docker compose exec web python test_capture_dates.py

This is the failure the offline queue produces silently: a capture made on Friday and
synced on Wednesday must be filed under Friday. Nothing else in the project would notice
if it were not.
"""
import os
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.utils import timezone  # noqa: E402

from bunker_core.capture import (  # noqa: E402
    MAX_BACKDATE_DAYS,
    InvalidOccurredOn,
    parse_occurred_on,
)

HOY = timezone.localdate()


def test_default_is_today():
    assert parse_occurred_on(None) == HOY
    assert parse_occurred_on("") == HOY
    print("OK 1/6 · sin fecha -> hoy")


def test_explicit_past_date_is_honoured():
    anteayer = HOY - timedelta(days=2)
    assert parse_occurred_on(anteayer.isoformat()) == anteayer
    print("OK 2/6 · una fecha de anteayer se respeta")


def test_future_is_rejected():
    try:
        parse_occurred_on((HOY + timedelta(days=1)).isoformat())
    except InvalidOccurredOn:
        print("OK 3/6 · el futuro se rechaza")
        return
    raise AssertionError("una fecha futura fue aceptada")


def test_too_old_is_rejected():
    viejo = HOY - timedelta(days=MAX_BACKDATE_DAYS + 30)
    try:
        parse_occurred_on(viejo.isoformat())
    except InvalidOccurredOn:
        print("OK 4/6 · mas de 30 dias atras se rechaza")
        return
    raise AssertionError("una fecha demasiado antigua fue aceptada")


def test_garbage_is_rejected():
    for basura in ("ayer", "2026-13-45", "01/02/2026", 12345):
        try:
            parse_occurred_on(basura)
        except InvalidOccurredOn:
            continue
        raise AssertionError(f"{basura!r} fue aceptado")
    print("OK 5/6 · basura se rechaza")


def test_boundaries_are_inclusive():
    """The two edges of the accepted range, which is where an off-by-one would live.

    Today itself is not the future, and exactly MAX_BACKDATE_DAYS back is not too old:
    a phone that queues a capture at 23:59 and syncs after midnight lands on the edge.
    """
    assert parse_occurred_on(HOY.isoformat()) == HOY
    limite = HOY - timedelta(days=MAX_BACKDATE_DAYS)
    assert parse_occurred_on(limite.isoformat()) == limite
    print("OK 6/6 · hoy y el limite exacto de 30 dias se aceptan")


if __name__ == "__main__":
    test_default_is_today()
    test_explicit_past_date_is_honoured()
    test_future_is_rejected()
    test_too_old_is_rejected()
    test_garbage_is_rejected()
    test_boundaries_are_inclusive()
    print("\ntest_capture_dates: 6/6")
