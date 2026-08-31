"""What Bunker says when you walk in.

Everything here reads models directly. It deliberately does NOT call
or `/api/dashboard/`: both pay prestige for past calendar events on every GET, so proxying
them would make opening Bunker a payment. See state-of-the-project.md §1.
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from bunker_core.insights import conclusiones


def _clave_semana(dia):
    """The ISO week key for a date, as "2026-W33". The ONE producer of this format."""
    return "%d-W%02d" % dia.isocalendar()[:2]


def _semana_actual():
    """The ISO week key, as "2026-W33". The ONE producer of this format.

    `construir_briefing` compares it and `marcar_visto` writes it; two copies of the format
    string would agree until the day one of them changed, and then `show_review` would be
    stuck on for ever with nothing to show for it. Eight characters, which is exactly the
    width of `BunkerState.last_review_week` — a wider key raises DataError on Postgres
    rather than truncating.
    """
    return _clave_semana(timezone.localdate())


def _semana_anterior(hoy=None):
    """The previous ISO week key. Seven days back through the SAME producer as
    `_semana_actual`, never by decrementing the number: week 1 minus one is not week 0, it is
    week 52 or 53 of the previous year, and which one it is depends on the year.

    `hoy` exists so a check can ask about January. Read from `localdate()` it is week 34 for
    the next four months, and "week number minus one" is right for all of them — an assertion
    that can only go red on one day a year has not been tested, it has been scheduled.
    """
    return _clave_semana((hoy or timezone.localdate()) - timedelta(days=7))


def construir_briefing():
    """The briefing payload. Pure read — nothing here writes."""
    # `timezone.localdate()`, never `date.today()`: the container runs UTC and the project is
    # America/Santiago, so between 20:00 and midnight `date.today()` returns *tomorrow* and
    # "ayer" would silently mean today.
    hoy = timezone.localdate()
    ayer = hoy - timedelta(days=1)

    from bunker_core.models import BunkerState
    from books.models import ReadingSession
    from music.models import MusicAnnualRecord
    from movies.models import MovieAnnualRecord

    estado, _ = BunkerState.objects.get_or_create(id=1)

    paginas_ayer = (ReadingSession.objects.filter(date=ayer)
                    .aggregate(t=Sum('pages_read'))['t'] or 0)
    # Films watched, NOT minutes. `MovieViewingSession` is the minute ledger deleted on
    # 2026-08-14 — 0 rows, nothing writes it — so "minutos de cine ayer" was a permanent zero
    # that a film watched last night could not move. The spec's own correction says it: a
    # film watched is the fact, its runtime is a property of the film.
    cine_ayer = MovieAnnualRecord.objects.filter(date_watched=ayer).count()
    # Records listened, NOT minutes — the same correction as films above. `ListeningEntry` is
    # the music minute ledger: 1 row, nothing writes it since 2026-08-14.
    discos_ayer = MusicAnnualRecord.objects.filter(date_listened=ayer).count()

    # Closest to finishing: fewest pages left, not furthest along. A book at 580/608 beats
    # one at 40/300 even though the second is a smaller fraction of nothing.
    # `.distinct('book_id')` is PostgreSQL-only (DISTINCT ON). Fine — this project has never
    # run on anything else — but it is the line that would break a SQLite port.
    ultima = (ReadingSession.objects
              .filter(book__isnull=False, book__is_read=False, current_page__isnull=False,
                      book__page_count__isnull=False)
              .order_by('book_id', '-date', '-id')
              .distinct('book_id')
              .values('book_id', 'current_page', 'book__title', 'book__page_count'))
    candidatos = [
        {"id": r['book_id'], "title": r['book__title'],
         "restantes": r['book__page_count'] - r['current_page']}
        for r in ultima if r['book__page_count'] > r['current_page']
    ]
    libro_cerca = min(candidatos, key=lambda c: c['restantes']) if candidatos else None

    # The review is built ONLY when it is going to be shown: on six days out of seven this
    # block is skipped entirely and the briefing does not pay for it.
    mostrar_revision = estado.last_review_week != _semana_actual()
    revision = _revision() if mostrar_revision else None

    return {
        "ayer": {"paginas": paginas_ayer, "peliculas": cine_ayer, "discos": discos_ayer},
        "libro_mas_cerca": libro_cerca,
        "conclusiones": conclusiones(),
        "show_review": mostrar_revision,
        "review": revision,
    }


def marcar_visto(con_revision):
    """Records the entry. This is the ONLY thing here that writes, and it is a POST.

    It also persisted the prestige snapshots until the 2026-08-27 split. That write moved to
    La Posada with the ledger; what remains here is the bookkeeping this repository owns —
    when the briefing was last shown, and for which week the review was shown.
    """
    from bunker_core.models import BunkerState
    estado, _ = BunkerState.objects.get_or_create(id=1)
    estado.last_entry_at = timezone.now()
    if con_revision:
        estado.last_review_week = _semana_actual()
    estado.save()
    return estado


# Label, module and which field of the series it reads. `books` appears twice on purpose —
# pages and works are two different facts about the same week.
_METRICAS_REVISION = (("Páginas", 'books', 'amount'),
                      ("Libros", 'books', 'count'),
                      ("Películas", 'movies', 'count'),
                      ("Discos", 'music', 'count'))


# `_logros_por_semana`, `_desglose` and `_prestigio_por_semana` stood here until the 2026-08-27
# split. All three read ONLY Posada's models, so they were domain code living in the Bunker's
# briefing; they moved to `posada/prestige.py` as `desglose_semana` and `prestigio_por_semana`,
# next to `_rango_semana`, whose inverse `_clave_semana` went with them.


def _revision():
    """The LAST COMPLETE ISO week against the one before it, built from the series and nothing
    else.

    NOT the week in progress. The review fires on the first entry of a new week, which in
    practice is Monday morning: comparing 0 days of data against a full seven made every one
    of the seven metrics a large negative delta, painted red, by construction. A review that
    structurally cannot say anything good is not a review. `window=3` so `[-1]` — the week in
    progress — can be dropped.

    The week being REVIEWED and the week being RECORDED are different: `marcar_visto` still
    writes `_semana_actual()`, because that is the bookkeeping for "shown once this week".

    Four metrics over THREE distinct modules: books twice (pages and works are two different
    facts about the same week), movies and music once each. Each module is fetched ONCE —
    calling `serie()` per metric would run books twice for no reason. Looping over the same
    module is the same waste as looping over periods, wearing a different hat.

    It was six metrics over five modules until the 2026-08-27 split, when posada and chess left
    and prestige and achievements went with them.
    """
    from bunker_core.timeline import serie
    series = {modulo: serie(modulo, 'weekly', 3)
              for modulo in {m[1] for m in _METRICAS_REVISION}}
    hoy = timezone.localdate()
    return {
        "semana": _clave_semana(hoy - timedelta(days=7)),
        "anterior": _clave_semana(hoy - timedelta(days=14)),
        # `window=3` guarantees three periods — `serie()` gap-fills from the calendar, so both
        # past weeks are present as zeros even in a database with no history at all. `[-1]` is
        # the week in progress and is deliberately not reported.
        "metricas": [{"etiqueta": etiqueta,
                      "actual": series[modulo][-2][campo],
                      "previa": series[modulo][-3][campo]}
                     for etiqueta, modulo, campo in _METRICAS_REVISION],
    }
