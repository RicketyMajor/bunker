"""The strings Bunker answers with when something is logged.

Every function returns a Spanish string, always — never `None`, never empty. When the data
does not support an interesting claim, the plain confirmation IS the correct answer: a
milestone that did not happen is worse than no milestone, and an empty bubble reads as "the
capture did not arrive".

Budget: at most one extra query per call. These run inside a capture request, and the TUI
must not feel slower for having something to say.

The model imports are deliberately inside the functions. This module lives in the project
package that owns `settings.py`, so importing app models at its top level makes it
unimportable before the app registry is ready. These run once per capture, never in a loop,
so the deferred import costs nothing worth measuring.
"""
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone


def _horas_min(total):
    """Minutes as "2 h", "1 h 30 min" or "45 min".

    One formatter rather than one per caller: the two that existed disagreed on whole hours
    (`2 h` against `2 h 0 min`), so the same quantity read two ways in the same TUI.
    """
    horas, resto = divmod(total, 60)
    if not horas:
        return f"{resto} min"
    if not resto:
        return f"{horas} h"
    return f"{horas} h {resto} min"


def _periodo(dia, unidad):
    """"este mes" when the capture belongs to the current period, "ese mes" when it does not.

    Captures are backdated by up to MAX_BACKDATE_DAYS, so a queue that drains on the 2nd
    files pages under the previous month and aggregates that month's total. Calling it
    "este mes" would report a real number about a period nobody asked about — the same class
    of invention as a milestone that did not happen.
    """
    hoy = timezone.localdate()
    if unidad == "año":
        mismo = dia.year == hoy.year
    else:
        mismo = (dia.year, dia.month) == (hoy.year, hoy.month)
    return f"{'este' if mismo else 'ese'} {unidad}"


def feedback_paginas(pages_read, occurred_on, book=None, current_page=None):
    """Pages logged. The interesting fact is how much is left, when that is known.

    `book.page_count` is nullable across half the inventory, so the "N pages left" branch
    only exists when the book declares its length. Without it nothing is estimated: the
    capture is confirmed instead.
    """
    if book is not None and current_page is not None and book.page_count:
        restantes = book.page_count - current_page
        if restantes <= 0:
            return f"«{book.title}» está en su última página. Márcalo como terminado."
        if restantes <= 50:
            return f"Te quedan {restantes} páginas de «{book.title}»."

    from catalog.models import ReadingSession
    total_mes = (ReadingSession.objects
                 .filter(date__year=occurred_on.year, date__month=occurred_on.month)
                 .aggregate(t=Sum('pages_read'))['t'] or 0)
    return f"{pages_read} páginas. Van {total_mes} {_periodo(occurred_on, 'mes')}."


def feedback_terminado(modulo, title, occurred_on):
    """An item finished. The interesting fact is how many that year holds."""
    from catalog.models import AnnualRecord
    from disquera.models import MusicAnnualRecord
    from movies.models import MovieAnnualRecord

    # The milestone phrase is stored whole rather than built from the noun: "película" is
    # feminine and takes "primera", so composing it from a singular produced "primer
    # película". One string per module is smaller than agreeing gender in code.
    modelos = {
        'libros': (AnnualRecord, 'date_finished', 'primer libro', 'libros'),
        'peliculas': (MovieAnnualRecord, 'date_watched', 'primera película', 'películas'),
        'discos': (MusicAnnualRecord, 'date_listened', 'primer disco', 'discos'),
    }
    if modulo not in modelos:
        # An endpoint calls this: an unexpected module confirms rather than killing the
        # capture that already succeeded.
        return f"«{title}» registrado."

    modelo, campo, primero, plural = modelos[modulo]
    van = modelo.objects.filter(**{f"{campo}__year": occurred_on.year}).count()
    periodo = _periodo(occurred_on, 'año')
    if van == 1:
        return f"«{title}» es tu {primero} de {periodo}."
    return f"«{title}». Van {van} {plural} {periodo}."


def feedback_habito(habit, es_recaida):
    """A habit marked. The streak is the fact; a relapse is not congratulated.

    Called AFTER `habit.save()`, so `current_streak` is already the new value.
    """
    if es_recaida:
        return f"Recaída en «{habit.name}». La racha vuelve a empezar."
    if habit.current_streak <= 1:
        return f"«{habit.name}» marcado. Día 1."
    return f"«{habit.name}»: {habit.current_streak} días seguidos."


def feedback_sesion(session, minutos_reales=None):
    """A Deep Work session closed. The fact is that category's total for the session's month.

    `duration_minutes` is the session's TARGET, and `process_session_completion` marks a
    session completed even when it was abandoned (engine/legacy.py:765) without ever
    adjusting it. So a caller that knows what was actually survived passes it in
    `minutos_reales`; otherwise the target is the honest figure, because the session ran.

    The month comes from `start_time`, not from today: a session started at 23:50 and closed
    after midnight would otherwise be excluded from its own accumulated figure.
    """
    from posada.models import DeepWorkSession
    dia = timezone.localdate(session.start_time)
    # ponytail: no index on (category, start_time). Invisible at 53 rows; if Deep Work ever
    # grows to thousands, index there before touching this function.
    # Survived minutes when the row has them, the target when it does not. COALESCE rather
    # than a Python fallback because this is one grouped query and must stay one: every row
    # written before survived_minutes existed carries NULL, and NULL must read as "unknown,
    # assume the target", never as zero — that would erase real work from the total.
    total_mes = (DeepWorkSession.objects
                 .filter(completed=True, category=session.category,
                         start_time__year=dia.year, start_time__month=dia.month)
                 .aggregate(t=Sum(Coalesce('survived_minutes', 'duration_minutes')))['t'] or 0)
    minutos = session.duration_minutes if minutos_reales is None else minutos_reales
    return (f"{minutos} min de {session.category}. "
            f"{_horas_min(total_mes)} {_periodo(dia, 'mes')}.")
