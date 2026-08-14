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


def test_habit_refuses_a_day_it_is_not_scheduled_for():
    """The sibling guard: right date, wrong day of the week.

    Same 409 as the retroactive refusal, and for the same reason — the penalty engine only
    scores days listed in `valid_days`, so anything paid outside them is free prestige.
    Pinned here rather than in test_movil_estado.py because this is the write path: the
    endpoint refuses it even when nothing offered it.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from posada.models import DailyHabit, GuildProfile
    from posada.views import complete_habit

    otros_dias = ",".join(str(d) for d in range(7) if d != HOY.weekday())
    f = APIRequestFactory()
    try:
        with transaction.atomic():
            guild, _ = GuildProfile.objects.get_or_create(id=1)
            prestigio_antes = guild.prestige

            fuera = DailyHabit.objects.create(
                name="Habito de otro dia", difficulty="B", valid_days=otros_dias,
                current_streak=4)
            resp = complete_habit(f.post("/", {"habit_id": fuera.id}, format="json"))
            assert resp.status_code == 409, f"esperaba 409, llego {resp.status_code}"
            fuera.refresh_from_db()
            assert fuera.current_streak == 4, f"la racha se movio a {fuera.current_streak}"
            assert fuera.last_completed_date is None, "marco la fecha de todas formas"
            guild.refresh_from_db()
            assert guild.prestige == prestigio_antes, "pago prestigio por un dia que no toca"

            # A bad habit is refused by the same guard: the engine would not have counted
            # that day as survived either, so it must not be charged as a relapse.
            malo = DailyHabit.objects.create(
                name="Mal habito de otro dia", difficulty="B", valid_days=otros_dias,
                is_bad_habit=True, current_streak=9)
            resp = complete_habit(f.post("/", {"habit_id": malo.id}, format="json"))
            assert resp.status_code == 409, f"el mal habito dio {resp.status_code}"
            malo.refresh_from_db()
            assert malo.current_streak == 9, "reseteo la racha de un mal habito fuera de dia"
            guild.refresh_from_db()
            assert guild.prestige == prestigio_antes, "cobro penalizacion fuera de dia"

            # And the day it *is* scheduled for still works, so the guard is not a wall.
            hoy_si = DailyHabit.objects.create(
                name="Habito de hoy", difficulty="B", valid_days=str(HOY.weekday()))
            resp = complete_habit(f.post("/", {"habit_id": hoy_si.id}, format="json"))
            assert resp.status_code == 200, f"el habito de hoy dio {resp.status_code}"
            hoy_si.refresh_from_db()
            assert hoy_si.current_streak == 1, "el habito de hoy no aplico"

            print("OK · dia no programado -> 409 en ambas ramas, y el dia que toca sigue pagando")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_finish_book_rejects_an_id_that_does_not_exist():
    """The failure this guards is late and looks like a success.

    Django creates its FKs in PostgreSQL as DEFERRABLE INITIALLY DEFERRED, so an unknown
    book_id is not caught on the INSERT — it is caught at COMMIT, after the view has already
    returned 201, and the request dies as a 500. A plain rolled-back check therefore reports
    a false pass, which is why this one forces the constraint the way a real commit would.

    It matters to the queue: an item only leaves it on a 2xx, so a book captured offline and
    deleted from the vault before the flush would 500 for ever, and the only way out is
    discarding a book that was actually finished.
    """
    from django.db import connection, transaction
    from rest_framework.test import APIRequestFactory

    from catalog.models import AnnualRecord
    from catalog.views import finish_book

    f = APIRequestFactory()
    try:
        with transaction.atomic():
            resp = finish_book(f.post(
                "/", {"title": "Libro fantasma", "book_id": 999999}, format="json"))
            assert resp.status_code == 400, f"esperaba 400, llego {resp.status_code}"
            assert not AnnualRecord.objects.filter(title="Libro fantasma").exists(), \
                "escribio el registro igual"
            # Would raise IntegrityError here if the row had been written with a dangling FK.
            with connection.cursor() as cur:
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
            print("OK · un book_id inexistente da 400, no un 201 que revienta en el commit")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_finish_book_without_an_id_still_works():
    """The TUI and any external book send no id at all. That path must not have moved."""
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from catalog.models import AnnualRecord
    from catalog.views import finish_book

    f = APIRequestFactory()
    try:
        with transaction.atomic():
            resp = finish_book(f.post(
                "/", {"title": "Libro prestado", "author_name": "Alguien"}, format="json"))
            assert resp.status_code == 201, f"esperaba 201, llego {resp.status_code}"
            rec = AnnualRecord.objects.filter(title="Libro prestado").first()
            assert rec is not None and rec.book_id is None, "no acepto un libro sin id"
            print("OK · sin book_id sigue siendo 201, que es como registra la TUI")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_log_minutes_rejects_garbage_instead_of_crashing():
    """Task 18b made the phone call this. `int(minutes)` used to raise straight through.

    A 500 is not just noisy here: the mobile queue only drops an item on a 2xx, so a capture
    that 500s is one the user can never clear except by discarding it.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from movies.models import MovieViewingSession
    from movies.views import log_minutes

    f = APIRequestFactory()
    try:
        with transaction.atomic():
            antes = MovieViewingSession.objects.count()
            for basura in ("noventa", "45min", "-30", 0, ""):
                resp = log_minutes(f.post("/", {"minutes": basura}, format="json"))
                assert resp.status_code == 400, (
                    f"{basura!r} devolvio {resp.status_code}, se esperaba 400"
                )
            assert MovieViewingSession.objects.count() == antes, "escribio alguna sesion"

            resp = log_minutes(f.post("/", {"minutes": 95}, format="json"))
            assert resp.status_code == 201, f"un valor bueno dio {resp.status_code}"
            assert MovieViewingSession.objects.latest("id").minutes_watched == 95
            print("OK · minutos: basura y negativos dan 400, un numero real sigue dando 201")
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
        test_habit_refuses_a_day_it_is_not_scheduled_for,
        test_finish_book_rejects_an_id_that_does_not_exist,
        test_finish_book_without_an_id_still_works,
        test_log_minutes_rejects_garbage_instead_of_crashing,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_capture_dates: {len(PRUEBAS)}/{len(PRUEBAS)}")
