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
from datetime import date

from django.db.models import Sum


def feedback_paginas(pages_read, occurred_on, book=None, current_page=None):
    """Páginas registradas. El hecho interesante es cuánto falta, cuando se sabe.

    `book.page_count` es nullable en la mitad del inventario, así que la rama de "te quedan
    N" solo existe cuando el libro declara su longitud. Sin ella no se estima: se confirma.
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
    return f"{pages_read} páginas. Van {total_mes} este mes."


def feedback_terminado(modulo, title, occurred_on):
    """Un ítem terminado. El hecho interesante es cuántos van este año."""
    from catalog.models import AnnualRecord
    from disquera.models import MusicAnnualRecord
    from movies.models import MovieAnnualRecord

    modelos = {
        'libros': (AnnualRecord, 'date_finished', 'libro', 'libros'),
        'peliculas': (MovieAnnualRecord, 'date_watched', 'película', 'películas'),
        'discos': (MusicAnnualRecord, 'date_listened', 'disco', 'discos'),
    }
    if modulo not in modelos:
        # Lo llama un endpoint: un módulo inesperado confirma, no revienta la captura.
        return f"«{title}» registrado."

    modelo, campo, singular, plural = modelos[modulo]
    van = modelo.objects.filter(**{f"{campo}__year": occurred_on.year}).count()
    if van == 1:
        return f"«{title}» es tu primer {singular} del año."
    return f"«{title}». Van {van} {plural} este año."


def feedback_minutos(minutes, occurred_on):
    """Minutos de cine. Se expresan en horas cuando pasan de una."""
    from movies.models import MovieViewingSession
    total_mes = (MovieViewingSession.objects
                 .filter(date__year=occurred_on.year, date__month=occurred_on.month)
                 .aggregate(t=Sum('minutes_watched'))['t'] or 0)
    if total_mes >= 60:
        horas, resto = divmod(total_mes, 60)
        acumulado = f"{horas} h {resto} min" if resto else f"{horas} h"
    else:
        acumulado = f"{total_mes} min"
    return f"{minutes} min. Llevas {acumulado} de cine este mes."


def feedback_habito(habit, es_recaida):
    """Un hábito marcado. La racha es el hecho; una recaída no se felicita.

    Se llama DESPUÉS de `habit.save()`, así que `current_streak` ya es el valor nuevo.
    """
    if es_recaida:
        return f"Recaída en «{habit.name}». La racha vuelve a empezar."
    if habit.current_streak <= 1:
        return f"«{habit.name}» marcado. Día 1."
    return f"«{habit.name}»: {habit.current_streak} días seguidos."


def feedback_sesion(session, minutos_reales=None):
    """Una sesión de Deep Work cerrada. El hecho es el acumulado de esa categoría este mes.

    `duration_minutes` is the session's TARGET, and `process_session_completion` marks a
    session completed even when it was abandoned (engine/legacy.py:765) without ever
    adjusting it. So a caller that knows what was actually survived passes it in
    `minutos_reales`; otherwise the target is the honest figure, because the session ran.

    ponytail: the monthly total can only ever sum targets — no field records survived time,
    so an abandoned session still counts as its full length in the accumulated figure. The
    upgrade is a `survived_minutes` column on DeepWorkSession, not arithmetic here.
    """
    from posada.models import DeepWorkSession
    hoy = date.today()
    # ponytail: sin índice en (category, start_time). A 53 filas es invisible; si Deep Work
    # crece a miles, indexar ahí antes que tocar esta función.
    total_mes = (DeepWorkSession.objects
                 .filter(completed=True, category=session.category,
                         start_time__year=hoy.year, start_time__month=hoy.month)
                 .aggregate(t=Sum('duration_minutes'))['t'] or 0)
    horas, resto = divmod(total_mes, 60)
    acumulado = f"{horas} h {resto} min" if horas else f"{resto} min"
    minutos = session.duration_minutes if minutos_reales is None else minutos_reales
    return f"{minutos} min de {session.category}. {acumulado} este mes."
