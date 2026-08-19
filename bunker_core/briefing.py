"""What Bunker says when you walk in.

Everything here reads models directly. It deliberately does NOT call `/posada/api/habits/`
or `/api/dashboard/`: both pay prestige for past calendar events on every GET, so proxying
them would make opening Bunker a payment. See state-of-the-project.md §1.
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone


def _semana_actual():
    """The ISO week key, as "2026-W33". The ONE producer of this format.

    `construir_briefing` compares it and `marcar_visto` writes it; two copies of the format
    string would agree until the day one of them changed, and then `show_review` would be
    stuck on for ever with nothing to show for it. Eight characters, which is exactly the
    width of `BunkerState.last_review_week` — a wider key raises DataError on Postgres
    rather than truncating.
    """
    return "%d-W%02d" % timezone.localdate().isocalendar()[:2]


def construir_briefing():
    """The briefing payload. Pure read — nothing here writes."""
    # `timezone.localdate()`, never `date.today()`: the container runs UTC and the project is
    # America/Santiago, so between 20:00 and midnight `date.today()` returns *tomorrow* and
    # "ayer" would silently mean today.
    hoy = timezone.localdate()
    ayer = hoy - timedelta(days=1)

    from bunker_core.models import BunkerState
    from catalog.models import ReadingSession
    from movies.models import MovieViewingSession
    from posada.models import Achievement, DailyHabit, DeepWorkSession

    estado, _ = BunkerState.objects.get_or_create(id=1)

    paginas_ayer = (ReadingSession.objects.filter(date=ayer)
                    .aggregate(t=Sum('pages_read'))['t'] or 0)
    cine_ayer = (MovieViewingSession.objects.filter(date=ayer)
                 .aggregate(t=Sum('minutes_watched'))['t'] or 0)
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

    return {
        "ayer": {"paginas": paginas_ayer, "minutos_cine": cine_ayer,
                 "minutos_deep_work": deep_ayer, "habitos": habitos_ayer},
        "hoy": {"habitos_pendientes": pendientes},
        "habito_en_riesgo": en_riesgo,
        "libro_mas_cerca": libro_cerca,
        "logros_nuevos": logros,
        "conclusiones": [],          # Task 11 fills this
        "show_review": estado.last_review_week != _semana_actual(),
        "review": None,              # Task 12 fills this
    }


def marcar_visto(con_revision):
    """Records the entry. This is the ONLY thing here that writes, and it is a POST."""
    from bunker_core.models import BunkerState
    estado, _ = BunkerState.objects.get_or_create(id=1)
    estado.last_entry_at = timezone.now()
    if con_revision:
        estado.last_review_week = _semana_actual()
    estado.save()
    return estado
