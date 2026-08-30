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
from itertools import chain, zip_longest

from django.db.models import Sum
from django.utils import timezone


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


# `feedback_habito` and `feedback_sesion` lived here until the 2026-08-27 split. Posada was
# their only caller and they read only Posada's models, so they moved to `posada/feedback.py`.
# `_horas_min` went with them and was DELETED here: `feedback_sesion` was its only caller, so
# after the move it was dead. `_periodo` stayed — `feedback_paginas` and `feedback_terminado`
# still use it — and was copied, not moved.


# --- Conclusiones: reglas puras sobre una serie. Cada una afirma algo o se calla. -------------
#
# The rule that governs them all: with fewer than three periods carrying data, `None`. Two
# points are not a trend, and an invented claim is worse than silence — the same constraint
# that makes the `feedback_*` functions above return the plain confirmation.
#
# EACH MODULE BRINGS ITS OWN NOUN. The plan wrote one rule per phrase ("Este mes llevas N
# páginas") and then ran every rule over books, posada and movies alike — which asserts
# "0 páginas" about a film. The rule is the same for all of them; the sentence is not, so the
# noun travels with the module and a module with no amount is simply skipped by the amount
# rules. Since 2026-08-19 movies and music carry `amount` = 0 by design, so this is not a
# hypothetical.
#
# Every rule is a pure function of (series, labels): no database, no clock, testable with a
# hand-built list.

_MINIMO_PERIODOS = 3

# ponytail: the sentences say "mes" because `conclusiones()` only ever asks for a monthly
# series. If a weekly briefing is ever built, the period noun comes from the caller — the
# rules themselves already work on any series shape.

# `monto` is None for a module that has no amount — the amount rules skip it rather than
# asserting zero.
# `actividad` is NOT a synonym of `obra`. A period counts as active when it has a count OR an
# amount, so July 2026 — 0 books finished, 60 pages read — is active while its count is zero.
# Reporting that streak as "6 meses seguidos con libros terminados" asserts six finished books
# in a month that had none. The streak rules speak of activity; the count rules speak of works.
# `_1` is the singular form, used whenever the quantity is exactly one: the live database
# produced "1 minutos de Deep Work" on the first run. `actividad` needs no singular — no rule
# puts a number in front of it.
_ETIQUETAS = {
    'books': {'monto': 'páginas', 'monto_1': 'página',
              'obra': 'libros terminados', 'obra_1': 'libro terminado',
              'actividad': 'lectura'},
    'movies': {'monto': None, 'monto_1': None,
               'obra': 'películas vistas', 'obra_1': 'película vista',
               'actividad': 'películas'},
    # `actividad` is "música", an activity noun like books' "lectura", not the object plural
    # movies uses. The two existing modules disagree with each other, so precedent settled
    # nothing; "música" is the one that does not collide with the inventory — in an app that
    # IS a record collection, "Dos meses sin discos" reads as owning none.
    'music': {'monto': None, 'monto_1': None,
              'obra': 'discos escuchados', 'obra_1': 'disco escuchado',
              'actividad': 'música'},
}


def _n(cantidad, etiquetas, clave):
    """"1 libro terminado" contra "3 libros terminados"."""
    return etiquetas[f"{clave}_1"] if cantidad == 1 else etiquetas[clave]


def _con_datos(series):
    return [p for p in series if p['count'] or p['amount']]


def _legible(periodo):
    """"2026-08" → "agosto"; "2026-W31" → "la semana 31"."""
    if '-W' in periodo:
        return f"la semana {periodo.split('-W')[1].lstrip('0')}"
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    return meses[int(periodo.split('-')[1]) - 1]


# The current period is INCOMPLETE and the ones it is measured against are not. Compared
# raw, on 2 September "12 pages against an average of 300" is arithmetically true and
# systematically misleading — it would fire every month by construction, for roughly the first
# third of it. `avance` is the fraction of the period already elapsed, and the comparison is
# against the pro-rated expectation. Below a quarter of the period the rule says nothing: two
# days are not a pace, which is the same principle as _MINIMO_PERIODOS one axis over.
_AVANCE_MINIMO = 0.25


def regla_tendencia_monto(series, etiquetas, avance=1.0):
    """El ritmo del periodo en curso contra lo que tocaría a su media."""
    if len(_con_datos(series)) < _MINIMO_PERIODOS or not etiquetas['monto']:
        return None
    if avance < _AVANCE_MINIMO:
        return None
    previos = [p['amount'] for p in series[:-1] if p['amount']]
    if not previos:
        return None
    actual = series[-1]['amount']
    esperado = (sum(previos) / len(previos)) * avance
    if actual > esperado * 1.5:
        return (f"Este mes llevas {actual} {_n(actual, etiquetas, 'monto')}: bastante más "
                f"que las {int(esperado)} que llevarías a tu ritmo habitual.")
    if actual < esperado * 0.5:
        return (f"Este mes llevas {actual} {_n(actual, etiquetas, 'monto')}, por debajo "
                f"de las {int(esperado)} que llevarías a tu ritmo habitual.")
    return None


def regla_tendencia_conteo(series, etiquetas, avance=1.0):
    """Lo mismo sobre el conteo, que es lo único que tienen movies y music.

    Sólo dispara al alza, así que el periodo incompleto no puede producir una falsa alarma:
    superar la media entera con el mes a medias es un hecho, no un artefacto. Aun así se
    calla al principio del periodo, para no llamar racha a dos días.
    """
    if len(_con_datos(series)) < _MINIMO_PERIODOS or avance < _AVANCE_MINIMO:
        return None
    previos = [p['count'] for p in series[:-1] if p['count']]
    if not previos:
        return None
    actual, media = series[-1]['count'], sum(previos) / len(previos)
    if actual > media * 1.5:
        return f"Van {actual} {_n(actual, etiquetas, 'obra')} este mes, sobre una media de {media:.1f}."
    return None


def regla_racha(series, etiquetas, avance=1.0):
    """Periodos consecutivos con actividad, contando hacia atrás desde el último."""
    if len(_con_datos(series)) < _MINIMO_PERIODOS:
        return None
    racha = 0
    for p in reversed(series):
        if not (p['count'] or p['amount']):
            break
        racha += 1
    if racha < _MINIMO_PERIODOS:
        return None
    return f"Llevas {racha} meses seguidos con {etiquetas['actividad']}."


def regla_record(series, etiquetas, avance=1.0):
    """El periodo en curso es el mejor de la ventana. Empate NO es récord."""
    if len(_con_datos(series)) < _MINIMO_PERIODOS:
        return None
    conteos = [p['count'] for p in series]
    if conteos[-1] and conteos[-1] > max(conteos[:-1]):
        return (f"{conteos[-1]} {_n(conteos[-1], etiquetas, 'obra')} este mes: "
                f"tu mejor marca de la ventana.")
    return None


def regla_mejor_periodo(series, etiquetas, avance=1.0):
    """El pico está DETRÁS. Complementaria de regla_record: nunca disparan juntas."""
    if len(_con_datos(series)) < _MINIMO_PERIODOS:
        return None
    previos = series[:-1]
    pico = max(previos, key=lambda p: p['count'])
    if not pico['count'] or pico['count'] <= series[-1]['count']:
        return None
    return (f"Tu mejor mes fue {_legible(pico['period'])} con {pico['count']} "
            f"{_n(pico['count'], etiquetas, 'obra')}.")


def regla_silencio(series, etiquetas, avance=1.0):
    """Dos periodos sin nada, después de haber tenido actividad. Rompe el silencio."""
    if len(_con_datos(series)) < _MINIMO_PERIODOS or len(series) < _MINIMO_PERIODOS:
        return None
    ultimos = series[-2:]
    if any(p['count'] or p['amount'] for p in ultimos):
        return None
    return (f"Dos meses sin {etiquetas['actividad']}. El último fue "
            f"{_legible(_con_datos(series)[-1]['period'])}.")


REGLAS = (regla_tendencia_monto, regla_tendencia_conteo, regla_racha,
          regla_record, regla_mejor_periodo, regla_silencio)


def conclusiones():
    """Entre 0 y 3 frases. El silencio es una respuesta válida, y al principio la habitual.

    ONE SENTENCE PER MODULE BEFORE A SECOND FROM ANY. Taken in dict order, books fired all
    three rules and the module after it never got a word in. Which module speaks first was an
    accident of insertion order; a round trip makes the cap of three cover three parts of the
    Bunker instead of one.

    `music` joined `_ETIQUETAS` on 2026-08-30 and had never been in it before. Its sentences
    stay silent until the music series holds three periods with data — `_MINIMO_PERIODOS`, the
    same bar every module clears — which is a property of the data, not of this dict. On the day
    it was added the live series had ONE (June 2026, 6 rows), so nothing on screen changed.
    """
    import calendar
    from bunker_core.timeline import serie
    hoy = timezone.localdate()
    # Fracción del mes ya transcurrida. Lo lee `conclusiones()`, no las reglas: siguen siendo
    # funciones puras de sus argumentos y se comprueban con listas escritas a mano.
    avance = hoy.day / calendar.monthrange(hoy.year, hoy.month)[1]
    por_modulo = []
    for modulo, etiquetas in _ETIQUETAS.items():
        s = serie(modulo, 'monthly', 6)
        por_modulo.append([f for f in (regla(s, etiquetas, avance) for regla in REGLAS) if f])
    return [f for f in chain(*zip_longest(*por_modulo)) if f][:3]
