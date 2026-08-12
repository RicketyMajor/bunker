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
    print("OK · sin fecha -> hoy")


def test_explicit_past_date_is_honoured():
    anteayer = HOY - timedelta(days=2)
    assert parse_occurred_on(anteayer.isoformat()) == anteayer
    print("OK · una fecha de anteayer se respeta")


def test_future_is_rejected():
    try:
        parse_occurred_on((HOY + timedelta(days=1)).isoformat())
    except InvalidOccurredOn:
        print("OK · el futuro se rechaza")
        return
    raise AssertionError("una fecha futura fue aceptada")


def test_too_old_is_rejected():
    viejo = HOY - timedelta(days=MAX_BACKDATE_DAYS + 30)
    try:
        parse_occurred_on(viejo.isoformat())
    except InvalidOccurredOn:
        print("OK · mas de 30 dias atras se rechaza")
        return
    raise AssertionError("una fecha demasiado antigua fue aceptada")


def test_garbage_is_rejected():
    for basura in ("ayer", "2026-13-45", "01/02/2026", 12345):
        try:
            parse_occurred_on(basura)
        except InvalidOccurredOn:
            continue
        raise AssertionError(f"{basura!r} fue aceptado")
    print("OK · basura se rechaza")


def test_boundaries_are_inclusive():
    """The two edges of the accepted range, which is where an off-by-one would live.

    Today itself is not the future, and exactly MAX_BACKDATE_DAYS back is not too old:
    a phone that queues a capture at 23:59 and syncs after midnight lands on the edge.
    """
    assert parse_occurred_on(HOY.isoformat()) == HOY
    limite = HOY - timedelta(days=MAX_BACKDATE_DAYS)
    assert parse_occurred_on(limite.isoformat()) == limite
    print("OK · hoy y el limite exacto de 30 dias se aceptan")


def test_every_verb_files_under_the_event_date():
    """One name on the wire, four field names behind it.

    The three collection modules named their date field differently — `date_finished`,
    `date_watched`, `date_listened` — and that divergence already caused one months-long
    bug (audit 3.1). Testing only one verb would leave the other three mappings unproven,
    which is exactly how the last one survived.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from catalog.models import AnnualRecord
    from catalog.views import finish_book
    from disquera.models import MusicAnnualRecord
    from disquera.views import finish_album
    from movies.models import MovieAnnualRecord, MovieViewingSession
    from movies.views import finish_movie, log_minutes

    anteayer = HOY - timedelta(days=2)
    fecha = anteayer.isoformat()
    f = APIRequestFactory()

    # (vista, payload, modelo, campo de fecha, filtro para encontrar la fila)
    casos = [
        (finish_book, {"title": "Libro de prueba", "occurred_on": fecha},
         AnnualRecord, "date_finished", {"title": "Libro de prueba"}),
        (finish_movie, {"title": "Pelicula de prueba", "occurred_on": fecha},
         MovieAnnualRecord, "date_watched", {"title": "Pelicula de prueba"}),
        (finish_album, {"title": "Album de prueba", "occurred_on": fecha},
         MusicAnnualRecord, "date_listened", {"title": "Album de prueba"}),
        (log_minutes, {"minutes": 42, "occurred_on": fecha},
         MovieViewingSession, "date", {"minutes_watched": 42}),
    ]

    try:
        with transaction.atomic():
            for vista, payload, modelo, campo, filtro in casos:
                resp = vista(f.post("/", payload, format="json"))
                assert resp.status_code == 201, f"{vista.__name__}: {resp.status_code}"
                fila = modelo.objects.filter(**filtro).order_by("-id").first()
                assert fila is not None, f"{vista.__name__}: no se creo la fila"
                real = getattr(fila, campo)
                assert real == anteayer, (
                    f"{vista.__name__} archivo bajo {real} en {modelo.__name__}.{campo}, "
                    f"se esperaba {anteayer}"
                )
            print("OK · los 4 verbos archivan bajo la fecha del evento, cada uno en su campo")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_every_verb_rejects_a_future_date():
    from rest_framework.test import APIRequestFactory

    from disquera.views import finish_album
    from catalog.views import finish_book
    from movies.views import finish_movie, log_minutes

    manana = (HOY + timedelta(days=1)).isoformat()
    f = APIRequestFactory()
    casos = [
        (finish_book, {"title": "Libro futuro", "occurred_on": manana}),
        (finish_movie, {"title": "Pelicula futura", "occurred_on": manana}),
        (finish_album, {"title": "Album futuro", "occurred_on": manana}),
        (log_minutes, {"minutes": 10, "occurred_on": manana}),
    ]
    for vista, payload in casos:
        resp = vista(f.post("/", payload, format="json"))
        assert resp.status_code == 400, (
            f"{vista.__name__}: esperaba 400, llego {resp.status_code}"
        )
    print("OK · los 4 verbos rechazan el futuro con 400")


def test_habit_refuses_a_past_date_and_leaves_the_streak_alone():
    """The one verb with no correct retroactive behaviour, only an honest refusal.

    Also pins the boundary between the two rejections: a malformed or future date is a 400
    like everywhere else, and only a genuine past date earns the 409. Conflating them would
    tell the user "los hábitos se marcan el mismo día" about a typo.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from posada.models import DailyHabit
    from posada.views import complete_habit

    ayer = HOY - timedelta(days=1)
    f = APIRequestFactory()
    try:
        with transaction.atomic():
            h = DailyHabit.objects.create(name="Habito de prueba", current_streak=5)

            resp = complete_habit(
                f.post("/", {"habit_id": h.id, "occurred_on": ayer.isoformat()}, format="json")
            )
            assert resp.status_code == 409, f"esperaba 409, llego {resp.status_code}"
            h.refresh_from_db()
            assert h.current_streak == 5, f"la racha se movio a {h.current_streak}"
            assert h.last_completed_date is None, "marco la fecha de todas formas"

            futuro = (HOY + timedelta(days=1)).isoformat()
            resp = complete_habit(
                f.post("/", {"habit_id": h.id, "occurred_on": futuro}, format="json")
            )
            assert resp.status_code == 400, f"el futuro dio {resp.status_code}, se esperaba 400"

            resp = complete_habit(
                f.post("/", {"habit_id": h.id, "occurred_on": "ayer"}, format="json")
            )
            assert resp.status_code == 400, f"la basura dio {resp.status_code}, se esperaba 400"

            h.refresh_from_db()
            assert h.current_streak == 5, "alguna rama movio la racha"
            print("OK · habito atrasado -> 409, futuro y basura -> 400, racha intacta")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_habit_today_still_works():
    """Regression guard on the path the TUI uses: it never sends occurred_on, and an
    explicit today must behave identically."""
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from posada.models import DailyHabit
    from posada.views import complete_habit

    f = APIRequestFactory()
    try:
        with transaction.atomic():
            sin_fecha = DailyHabit.objects.create(name="Habito sin fecha", difficulty="B")
            resp = complete_habit(f.post("/", {"habit_id": sin_fecha.id}, format="json"))
            assert resp.status_code == 200, f"el TUI recibio {resp.status_code}"
            sin_fecha.refresh_from_db()
            assert sin_fecha.last_completed_date == HOY, "no marco hoy"
            assert sin_fecha.current_streak == 1, f"racha {sin_fecha.current_streak}, se esperaba 1"

            con_hoy = DailyHabit.objects.create(name="Habito con hoy", difficulty="B")
            resp = complete_habit(
                f.post("/", {"habit_id": con_hoy.id, "occurred_on": HOY.isoformat()}, format="json")
            )
            assert resp.status_code == 200, f"con hoy explicito recibio {resp.status_code}"
            con_hoy.refresh_from_db()
            assert con_hoy.current_streak == 1, "hoy explicito no aplico"
            print("OK · sin fecha y con hoy explicito se comportan igual que siempre")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


if __name__ == "__main__":
    # Listed rather than called one by one so the count in the summary cannot drift from
    # the number of checks. Later tasks in this plan keep appending here.
    PRUEBAS = [
        test_default_is_today,
        test_explicit_past_date_is_honoured,
        test_future_is_rejected,
        test_too_old_is_rejected,
        test_garbage_is_rejected,
        test_boundaries_are_inclusive,
        test_every_verb_files_under_the_event_date,
        test_every_verb_rejects_a_future_date,
        test_habit_refuses_a_past_date_and_leaves_the_streak_alone,
        test_habit_today_still_works,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_capture_dates: {len(PRUEBAS)}/{len(PRUEBAS)}")
