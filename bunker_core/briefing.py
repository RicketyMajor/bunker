"""What Bunker says when you walk in.

Everything here reads models directly. It deliberately does NOT call `/posada/api/habits/`
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
    from catalog.models import ReadingSession
    from movies.models import MovieAnnualRecord
    from posada.models import Achievement, DailyHabit, DeepWorkSession

    estado, _ = BunkerState.objects.get_or_create(id=1)

    paginas_ayer = (ReadingSession.objects.filter(date=ayer)
                    .aggregate(t=Sum('pages_read'))['t'] or 0)
    # Films watched, NOT minutes. `MovieViewingSession` is the minute ledger deleted on
    # 2026-08-14 — 0 rows, nothing writes it — so "minutos de cine ayer" was a permanent zero
    # that a film watched last night could not move. The spec's own correction says it: a
    # film watched is the fact, its runtime is a property of the film.
    cine_ayer = MovieAnnualRecord.objects.filter(date_watched=ayer).count()
    deep_ayer = (DeepWorkSession.objects
                 .filter(completed=True, start_time__date=ayer)
                 .aggregate(t=Sum('duration_minutes'))['t'] or 0)
    habitos_ayer = DailyHabit.objects.filter(last_completed_date=ayer).count()

    # Same `valid_days` rule the penalty engine uses and the one `movil_estado` already
    # applies. A habit not scheduled today is not pending today.
    pendientes = list(DailyHabit.objects
                      .filter(valid_days__contains=str(hoy.weekday()))
                      .exclude(last_completed_date=hoy)
                      .values('id', 'name', 'difficulty')[:20])

    # At risk: the longest live streak that has not been marked today. A streak of 0 has
    # nothing to lose, so it is not "at risk" — it is just unstarted.
    en_riesgo = (DailyHabit.objects
                 .filter(valid_days__contains=str(hoy.weekday()), current_streak__gt=0,
                         is_bad_habit=False)
                 .exclude(last_completed_date=hoy)
                 .order_by('-current_streak')
                 .values('id', 'name', 'current_streak')
                 .first())

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

    logros = []
    if estado.last_entry_at:
        logros = list(Achievement.objects
                      .filter(unlocked_at__gt=estado.last_entry_at)
                      .values('key', 'name', 'icon'))

    # The review is built ONLY when it is going to be shown: on six days out of seven this
    # block is skipped entirely and the briefing does not pay for it.
    mostrar_revision = estado.last_review_week != _semana_actual()
    revision = _revision() if mostrar_revision else None

    return {
        "ayer": {"paginas": paginas_ayer, "peliculas": cine_ayer,
                 "minutos_deep_work": deep_ayer, "habitos": habitos_ayer},
        "hoy": {"habitos_pendientes": pendientes},
        "habito_en_riesgo": en_riesgo,
        "libro_mas_cerca": libro_cerca,
        "logros_nuevos": logros,
        "conclusiones": conclusiones(),
        "show_review": mostrar_revision,
        "review": revision,
    }


def marcar_visto(con_revision):
    """Records the entry. This is the ONLY thing here that writes, and it is a POST.

    Since 2026-08-21 it also persists the prestige snapshots. They used to be written by
    `resumen_semana` on the READ path, which made `GET /api/briefing/` an unsafe GET and broke
    the read-only criterion of `specs/movil-v3.md` before that panel existed. This is where
    the write belongs: the endpoint that is a POST because it writes.

    The weeks snapshotted are the two the review actually reported — `hoy - 7` and `hoy - 14`,
    the same pair `_prestigio_por_semana` builds — and NOT `_semana_actual()`, which is the
    different piece of bookkeeping below: "shown once this week".
    """
    from bunker_core.models import BunkerState
    estado, _ = BunkerState.objects.get_or_create(id=1)
    estado.last_entry_at = timezone.now()
    if con_revision:
        from posada.prestige import snapshot_semana
        hoy = timezone.localdate()
        snapshot_semana(_clave_semana(hoy - timedelta(days=7)))
        snapshot_semana(_clave_semana(hoy - timedelta(days=14)))
        estado.last_review_week = _semana_actual()
    estado.save()
    return estado


# Label, module and which field of the series it reads. `books` appears twice on purpose —
# pages and works are two different facts about the same week.
_METRICAS_REVISION = (("Páginas", 'books', 'amount'),
                      ("Libros", 'books', 'count'),
                      ("Deep Work (min)", 'posada', 'amount'),
                      ("Películas", 'movies', 'count'),
                      ("Discos", 'music', 'count'),
                      ("Puzzles", 'chess', 'count'))


def _logros_por_semana():
    """Achievements unlocked in the two LAST COMPLETE weeks, newest first. One grouped query,
    same idiom as `timeline.py` — `unlocked_at` is a DateTimeField, so `TruncWeek` needs the
    timezone the project actually runs in, not the container's UTC."""
    from django.db.models import Count
    from django.db.models.functions import TruncWeek
    from posada.models import Achievement
    hoy = timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())
    revisada, comparada = lunes - timedelta(days=7), lunes - timedelta(days=14)
    filas = (Achievement.objects
             .filter(unlocked_at__date__gte=comparada, unlocked_at__date__lt=lunes)
             .annotate(semana=TruncWeek('unlocked_at'))
             .values('semana').annotate(n=Count('id')))
    por_semana = {f['semana'].date() if hasattr(f['semana'], 'date') else f['semana']: f['n']
                  for f in filas}
    return por_semana.get(revisada, 0), por_semana.get(comparada, 0)


def _desglose(week_key):
    """That week's entries grouped by source, largest first, zeros omitted.

    One grouped query. A source whose entries net to exactly zero in the week — a habit
    completed and then undone — carries no information and is dropped rather than rendered
    as a `0` line the reader has to interpret.
    """
    from django.db.models import Sum

    from posada.models import PrestigeEntry
    from posada.prestige import _rango_semana

    lunes, siguiente = _rango_semana(week_key)
    etiquetas = dict(PrestigeEntry.FUENTES)
    filas = (PrestigeEntry.objects
             .filter(occurred_at__date__gte=lunes, occurred_at__date__lt=siguiente)
             .values('source').annotate(monto=Sum('amount')).order_by('-monto'))
    return [{"fuente": f['source'],
             "etiqueta": etiquetas.get(f['source'], f['source']),
             "monto": f['monto']}
            for f in filas if f['monto']]


def _prestigio_por_semana():
    """Prestige for the two LAST COMPLETE weeks, plus the reviewed week's breakdown by source.

    Same window as `_logros_por_semana()` directly above — that function already gets the
    Monday boundary and the timezone right, and inventing a second way to ask the same
    question is how two numbers start disagreeing. The keys come from `_clave_semana`, the
    one producer of the format, and the summing lives in `posada.prestige.resumen_semana`,
    the one producer of the number.
    """
    from posada.prestige import resumen_semana

    hoy = timezone.localdate()
    revisada = _clave_semana(hoy - timedelta(days=7))
    comparada = _clave_semana(hoy - timedelta(days=14))
    return resumen_semana(revisada), resumen_semana(comparada), _desglose(revisada)


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

    Six metrics over FIVE distinct modules — the plan says four, but the list names books,
    posada, movies, music and chess. Each module is fetched ONCE: calling `serie()` per metric
    would run books twice for no reason. Looping over the same module is the same waste as
    looping over periods, wearing a different hat.
    """
    from bunker_core.timeline import serie
    series = {modulo: serie(modulo, 'weekly', 3)
              for modulo in {m[1] for m in _METRICAS_REVISION}}
    hoy = timezone.localdate()
    logros_actual, logros_previa = _logros_por_semana()
    prest_actual, prest_previa, desglose = _prestigio_por_semana()
    return {
        "semana": _clave_semana(hoy - timedelta(days=7)),
        "anterior": _clave_semana(hoy - timedelta(days=14)),
        # `window=3` guarantees three periods — `serie()` gap-fills from the calendar, so both
        # past weeks are present as zeros even in a database with no history at all. `[-1]` is
        # the week in progress and is deliberately not reported.
        "metricas": [{"etiqueta": etiqueta,
                      "actual": series[modulo][-2][campo],
                      "previa": series[modulo][-3][campo]}
                     for etiqueta, modulo, campo in _METRICAS_REVISION]
                    + [{"etiqueta": "Logros", "actual": logros_actual,
                        "previa": logros_previa}],
        # Prestige is NOT a metric row: a row is one number against last week's, and the
        # whole point of the ledger is that a week has two — what was earned and what was
        # lost. A net of +40 that hides "avoided three vices, missed two habits" is the
        # question the review is supposed to answer, not the answer.
        "prestigio": {"actual": prest_actual, "previa": prest_previa,
                      "por_fuente": desglose},
    }
