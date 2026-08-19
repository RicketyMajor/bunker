"""The historical series everything else reads.

One grouped query per SOURCE MODEL, never a loop over periods — the dashboard made that
mistake once (seven aggregations in a `for`) and it was collapsed on 2026-07-26.

Three of the five modules need two queries, not one: their counts and their amounts live in
different tables. Books count `AnnualRecord` but sum pages from `ReadingSession`; movies and
music are the same shape. Only posada and chess are single-model. The spec says "one query
per module"; the tables say otherwise, and the constraint that matters — no loop over
periods — is unaffected.

Gap filling happens in Python over the result: a period with no activity returns zeros, it
is never omitted.
"""
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

MODULOS = ('books', 'movies', 'music', 'posada', 'chess')
PERIODOS = ('monthly', 'weekly')
WINDOW_DEFECTO = 12
# 60 months is five years; 60 weeks is over a year. Past that the series stops being a
# series and starts being a data export, which is not what this endpoint is for.
WINDOW_MAX = 60


def _fuentes(module):
    """(model, date_field, amount_field, filtro) per source. Imported lazily: this module is
    inside the project package that owns settings.py."""
    from catalog.models import AnnualRecord, ReadingSession
    from chess_study.models import SolvedPuzzle
    from disquera.models import ListeningEntry, MusicAnnualRecord
    from movies.models import MovieAnnualRecord, MovieViewingSession
    from posada.models import DeepWorkSession

    return {
        'books': [(AnnualRecord, 'date_finished', None, {}),
                  (ReadingSession, 'date', 'pages_read', {})],
        'movies': [(MovieAnnualRecord, 'date_watched', None, {}),
                   (MovieViewingSession, 'date', 'minutes_watched', {})],
        'music': [(MusicAnnualRecord, 'date_listened', None, {}),
                  (ListeningEntry, 'date', 'minutes_listened', {})],
        'posada': [(DeepWorkSession, 'start_time', 'duration_minutes', {'completed': True})],
        'chess': [(SolvedPuzzle, 'solved_at', None, {})],
    }[module]


def _inicio_periodo(d, period):
    if period == 'monthly':
        return d.replace(day=1)
    return d - timedelta(days=d.weekday())      # Monday, same as TruncWeek and ISO


def _anterior(d, period):
    if period == 'monthly':
        return (d.replace(day=1) - timedelta(days=1)).replace(day=1)
    return d - timedelta(days=7)


def _clave(d, period):
    if period == 'monthly':
        return d.strftime('%Y-%m')
    anio, semana, _ = d.isocalendar()
    return f"{anio}-W{semana:02d}"


def _normalizar(valor):
    """TruncMonth over a DateTimeField returns a datetime, over a DateField a date. The
    merge key has to be the same type either way."""
    return valor.date() if hasattr(valor, 'date') else valor


def serie(module, period='monthly', window=WINDOW_DEFECTO):
    """The gap-filled series for one module.

    Raises ValueError on an unknown module or period. `window` is clamped to
    [1, WINDOW_MAX] rather than rejected: a hand-typed 99999 is a typo, not an attack,
    and a clamped answer is more useful than a 400.
    """
    if module not in MODULOS:
        raise ValueError(f"module debe ser uno de: {', '.join(MODULOS)}.")
    if period not in PERIODOS:
        raise ValueError(f"period debe ser uno de: {', '.join(PERIODOS)}.")

    try:
        window = int(window)
    except (TypeError, ValueError):
        window = WINDOW_DEFECTO
    window = max(1, min(window, WINDOW_MAX))

    trunc = TruncMonth if period == 'monthly' else TruncWeek

    # The periods the answer must contain, newest first then reversed. Built from the
    # calendar, not from the data — this is what makes a hole come back as a zero.
    # `localdate()`, never `date.today()`: the container runs UTC and the project is
    # America/Santiago, so after 20:00 local `date.today()` already names tomorrow — and on
    # the last day of a month that starts the series one period too far forward.
    cursor = _inicio_periodo(timezone.localdate(), period)
    periodos = []
    for _ in range(window):
        periodos.append(cursor)
        cursor = _anterior(cursor, period)
    periodos.reverse()
    desde = periodos[0]

    conteos, montos = {}, {}
    for modelo, campo_fecha, campo_monto, filtro in _fuentes(module):
        # `__date__gte` on a DateTimeField, plain `__gte` on a DateField: comparing a
        # DateTimeField against a `date` hands the ORM a naive datetime under USE_TZ, which
        # warns and pins the boundary to UTC midnight — four hours off the local one.
        es_datetime = modelo._meta.get_field(campo_fecha).get_internal_type() == 'DateTimeField'
        lookup = f"{campo_fecha}__date__gte" if es_datetime else f"{campo_fecha}__gte"
        qs = modelo.objects.filter(**filtro, **{lookup: desde})
        agregados = {'n': Count('id')}
        if campo_monto:
            agregados['total'] = Sum(campo_monto)
        filas = (qs.annotate(periodo=trunc(campo_fecha))
                   .values('periodo')
                   .annotate(**agregados)
                   .order_by('periodo'))
        for fila in filas:
            clave = _clave(_normalizar(fila['periodo']), period)
            if campo_monto:
                montos[clave] = montos.get(clave, 0) + (fila.get('total') or 0)
            else:
                conteos[clave] = conteos.get(clave, 0) + fila['n']

    return [{"period": _clave(p, period),
             "count": conteos.get(_clave(p, period), 0),
             "amount": montos.get(_clave(p, period), 0)}
            for p in periodos]
