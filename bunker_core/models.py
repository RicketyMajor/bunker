"""Cross-cutting state that belongs to no single module.

One row, id=1, same singleton pattern as `GuildProfile` — but enforced here rather than
merely documented.

The weekly review's METRICS are still computed from the series each time, and `bunker_core`
owns no snapshot table. `posada.PrestigeWeek` (2026-08-20) is the project's one exception,
and it lives beside the balance it has to reconcile against rather than here. That reversed
the decision this docstring used to state flatly; `context/decisions/log.md` records the
reversal instead of overwriting the original, because the reasoning that produced it is
still the reasoning that keeps every other derived number out of a table.
"""
from django.db import models
from django.utils import timezone


class BunkerState(models.Model):
    # The singleton's identity, not a sequence. With the default `BigAutoField`, inserting
    # id=1 explicitly never advances the sequence — measured on 2026-08-19: `last_value=1,
    # is_called=f` — so the first `create()` without an id would ask for 1 and collide with
    # an error that reads like corruption instead of like the invariant it is. An explicit
    # default makes `create()` produce *the* row, and a second one fail on the primary key.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)

    # ISO week the last weekly review was shown for, as "2026-W33". A string rather than an
    # integer because week 1 of 2027 must not look like week 1 of 2026.
    last_review_week = models.CharField(max_length=8, blank=True, default="")

    # When the briefing was last delivered. Drives "achievements unlocked since your last
    # entry". Null means Bunker has never been entered since this model existed.
    last_entry_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # `last_entry_at` is stored UTC-aware (USE_TZ), and an f-string does no localization
        # the way a template does — printed raw it is four hours off the clock this project
        # is read on.
        entrada = timezone.localtime(self.last_entry_at) if self.last_entry_at else "nunca"
        return f"BunkerState(última entrada: {entrada}, revisión: {self.last_review_week or '—'})"
