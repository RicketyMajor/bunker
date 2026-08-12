"""Parsing for the event date the mobile companion sends with every capture.

The phone captures offline and syncs later, so a capture carries the date it *happened*
rather than the date it arrived. Without this, everything logged away from home is filed
under the day the queue happened to flush, which silently corrupts streaks, the reading
heatmap and the annual records at once.

Spec: context/specs/transmisor-de-campo.md
"""
from datetime import date, timedelta

from django.utils import timezone

# How far back a capture may claim to be. The queue is expected to drain in hours, not
# weeks; this is a guard against a phone with a wrong clock, not a feature.
MAX_BACKDATE_DAYS = 30


class InvalidOccurredOn(ValueError):
    """Carries a user-facing Spanish message, safe to return in a 400 body."""


def parse_occurred_on(raw):
    """Return a date for an optional wire value, defaulting to today.

    `raw` is whatever arrived over the network: None, "" or "YYYY-MM-DD". This is a trust
    boundary — the value comes from a device whose clock is not under our control — so the
    range is validated rather than clamped, and a bad value is loud.
    """
    today = timezone.localdate()
    if not raw:
        return today

    # date.fromisoformat accepts only str. A bool is an int and would never reach here as
    # anything but garbage, so everything non-str is rejected rather than coerced: str(12345)
    # is "12345", which fromisoformat would reject anyway, but str(date(...)) would sneak a
    # non-wire type through.
    if not isinstance(raw, str):
        raise InvalidOccurredOn("Fecha inválida: se espera AAAA-MM-DD.")

    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        raise InvalidOccurredOn("Fecha inválida: se espera AAAA-MM-DD.")

    if parsed > today:
        raise InvalidOccurredOn("La fecha no puede estar en el futuro.")
    if parsed < today - timedelta(days=MAX_BACKDATE_DAYS):
        raise InvalidOccurredOn(
            f"La fecha no puede tener más de {MAX_BACKDATE_DAYS} días de antigüedad."
        )
    return parsed
