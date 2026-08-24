"""Standalone check for the capture date parser and the endpoints that use it.

Run: docker compose exec web python -m tests.test_capture_dates

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
    """One name on the wire, three field names behind it.

    The three collection modules named their date field differently — `date_finished`,
    `date_watched`, `date_listened` — and that divergence already caused one months-long
    bug (audit 3.1). Testing only one verb would leave the other two mappings unproven,
    which is exactly how the last one survived.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from catalog.models import AnnualRecord
    from catalog.views import finish_book
    from disquera.models import MusicAnnualRecord
    from disquera.views import finish_album
    from movies.models import MovieAnnualRecord
    from movies.views import finish_movie

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
            # Counted from the list rather than written in the string: this project has
            # already shipped three prose counts that drifted from what the code did.
            print(f"OK · los {len(casos)} verbos archivan bajo la fecha del evento, "
                  f"cada uno en su campo")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_every_verb_rejects_a_future_date():
    from rest_framework.test import APIRequestFactory

    from disquera.views import finish_album
    from catalog.views import finish_book
    from movies.views import finish_movie

    manana = (HOY + timedelta(days=1)).isoformat()
    f = APIRequestFactory()
    casos = [
        (finish_book, {"title": "Libro futuro", "occurred_on": manana}),
        (finish_movie, {"title": "Pelicula futura", "occurred_on": manana}),
        (finish_album, {"title": "Album futuro", "occurred_on": manana}),
    ]
    for vista, payload in casos:
        resp = vista(f.post("/", payload, format="json"))
        assert resp.status_code == 400, (
            f"{vista.__name__}: esperaba 400, llego {resp.status_code}"
        )
    print("OK · los 3 verbos rechazan el futuro con 400")


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


def test_habit_pays_and_saves_in_one_transaction():
    """The guild write and the habit write must stand or fall together.

    `complete_habit` writes two models on both branches: the good one calls
    `guild.add_prestige()` (which saves the guild) and then `habit.save()`; the bad one saves
    the guild and then the habit. An exception between them paid the reward and lost the streak
    -- the same failure class as the rollover bug fixed 2026-08-11 and the one `finish_book`
    had.

    Inverted by making `habit.save()` raise. Without `@transaction.atomic` on the view the
    guild keeps the prestige it was paid for a habit that never got marked; with it, the
    savepoint takes both back. The raise is a plain Python exception, not a database error, so
    the connection stays usable and the surrounding test transaction survives either way --
    which is what makes the two outcomes comparable.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from posada.models import DailyHabit, GuildProfile
    from posada.views import complete_habit

    f = APIRequestFactory()
    original = DailyHabit.save
    try:
        with transaction.atomic():
            guild, _ = GuildProfile.objects.get_or_create(id=1)
            habito = DailyHabit.objects.create(
                name="Habito atomico", difficulty="B", valid_days=str(HOY.weekday()),
                current_streak=3)
            guild.refresh_from_db()
            prestigio_antes = guild.prestige

            def revienta(self, *a, **kw):
                raise RuntimeError("el disco se cae justo entre las dos escrituras")

            DailyHabit.save = revienta
            try:
                complete_habit(f.post("/", {"habit_id": habito.id}, format="json"))
            except RuntimeError:
                pass
            finally:
                DailyHabit.save = original

            guild.refresh_from_db()
            assert guild.prestige == prestigio_antes, (
                f"la guilda se quedo con el prestigio de un habito que no se guardo: "
                f"{prestigio_antes} -> {guild.prestige}")
            habito.refresh_from_db()
            assert habito.current_streak == 3, f"la racha se movio a {habito.current_streak}"

            print("OK · un fallo entre las dos escrituras no deja prestigio pagado")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass
    finally:
        DailyHabit.save = original


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


def test_the_collection_capture_verbs_answer_with_a_fact():
    """Every logging endpoint returns a fact alongside the acknowledgement.

    Two things are pinned here, and the second is the one that breaks quietly. First, that
    `feedback` exists and is non-empty on all five verbs. Second, that `message` survived
    verbatim: the TUI, the phone's offline queue and three other checks in this project all
    read `message`, so this change is additive or it is a regression.

    `feedback != message` is what separates a real wiring from a constant string. An endpoint
    answering `"feedback": "Registrado."` would pass a non-empty check and still deliver
    nothing — which is the exact complaint this whole feature answers.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from catalog.models import Author, Book
    from catalog.views import finish_book, log_pages
    from disquera.views import finish_album
    from movies.views import finish_movie

    f = APIRequestFactory()
    try:
        with transaction.atomic():
            autor, _ = Author.objects.get_or_create(name="Autor de prueba")
            libro = Book.objects.create(title="Libro con paginas", author=autor,
                                        isbn="0000000000005", page_count=300)

            # (vista, payload, etiqueta). log_pages appears twice on purpose: its two
            # branches bind `book` and `current_page` differently, and a wiring that names
            # the wrong variable only fails in one of them.
            casos = [
                (log_pages, {"pages": 10}, "log_pages suelto"),
                (log_pages, {"book_id": libro.id, "current_page": 120}, "log_pages con libro"),
                (finish_book, {"title": "Libro terminado de prueba"}, "finish_book"),
                (finish_movie, {"title": "Pelicula terminada de prueba"}, "finish_movie"),
                (finish_album, {"title": "Album terminado de prueba"}, "finish_album"),
            ]

            for vista, payload, etiqueta in casos:
                resp = vista(f.post("/", payload, format="json"))
                assert resp.status_code == 201, f"{etiqueta}: {resp.status_code}"

                feedback = resp.data.get("feedback")
                assert isinstance(feedback, str) and feedback.strip(), \
                    f"{etiqueta}: feedback vacio o ausente ({feedback!r})"

                mensaje = resp.data.get("message")
                assert isinstance(mensaje, str) and mensaje.strip(), \
                    f"{etiqueta}: se perdio la clave message, que leen la TUI y la cola"

                assert feedback != mensaje, \
                    f"{etiqueta}: el feedback es el acuse repetido, no un hecho"

            print("OK · los 4 verbos devuelven un hecho y conservan su message")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_the_two_posada_verbs_answer_with_a_fact():
    """Posada's two capture verbs, including the one that reports a failure.

    A relapse returns `status: error` and is still a capture — the habit was recorded, the
    streak was reset, the prestige was charged — so it earns a feedback like any other. The
    refusals do not: a 409 answers something that did not happen.

    The surrender case is the one worth pinning. `process_session_completion` marks every
    session `completed` even when abandoned (engine/sesion.py) and never adjusts
    `duration_minutes`, which is the TARGET duration. A feedback reading it straight would
    tell someone who quit after 5 minutes that they did 50.
    """
    from django.db import transaction
    from rest_framework.test import APIRequestFactory

    from posada.models import DailyHabit, DeepWorkSession, GuildProfile
    from posada.views import complete_habit, complete_session

    hoy_toca = str(HOY.weekday())
    f = APIRequestFactory()
    try:
        with transaction.atomic():
            guild, _ = GuildProfile.objects.get_or_create(id=1)
            prestigio_antes = guild.prestige

            # --- Buen hábito: captura, feedback con la racha nueva ---
            bueno = DailyHabit.objects.create(name="Habito bueno de prueba", difficulty="C",
                                              valid_days=hoy_toca, current_streak=6)
            resp = complete_habit(f.post("/", {"habit_id": bueno.id}, format="json"))
            assert resp.status_code == 200, f"buen habito: {resp.status_code}"
            assert resp.data.get("message"), "buen habito: se perdio message"
            fb = resp.data.get("feedback")
            assert isinstance(fb, str) and fb.strip(), f"buen habito: feedback {fb!r}"
            assert "7" in fb, f"no nombra la racha ya incrementada: {fb!r}"

            # --- Recaída: status error, y aun asi es una captura ---
            malo = DailyHabit.objects.create(name="Mal habito de prueba", difficulty="C",
                                             valid_days=hoy_toca, is_bad_habit=True,
                                             current_streak=9)
            resp = complete_habit(f.post("/", {"habit_id": malo.id}, format="json"))
            assert resp.data.get("status") == "error", "la recaida cambio de status"
            fb = resp.data.get("feedback")
            assert isinstance(fb, str) and fb.strip(), f"recaida: feedback {fb!r}"
            assert "días seguidos" not in fb, f"la recaida felicita por una racha: {fb!r}"

            # --- Un rechazo NO lleva feedback: no hubo captura que comentar ---
            resp = complete_habit(f.post("/", {"habit_id": bueno.id}, format="json"))
            assert resp.data.get("status") == "warning", "el segundo intento no fue rechazado"
            assert "feedback" not in resp.data, \
                "un rechazo trae feedback: responde por algo que no ocurrio"

            # --- Sesión abandonada: el hecho es lo sobrevivido, no lo planeado ---
            sesion = DeepWorkSession.objects.create(duration_minutes=50,
                                                    category="Programacion de prueba")
            resp = complete_session(f.post(
                "/", {"session_id": sesion.id, "survived_seconds": 300, "surrendered": True},
                format="json"))
            assert resp.status_code == 200, f"complete_session: {resp.status_code}"
            assert resp.data.get("message"), "complete_session: se perdio message"
            fb = resp.data.get("feedback")
            assert isinstance(fb, str) and fb.strip(), f"sesion: feedback {fb!r}"
            assert not fb.startswith("50"), \
                f"reporta los 50 min planeados de una sesion abandonada a los 5: {fb!r}"
            assert "5 min" in fb, f"no reporta los minutos sobrevividos: {fb!r}"
            # Y queda ESCRITO, no solo dicho: si vive unicamente en esta respuesta, el total
            # del mes no tiene de donde leerlo y vuelve a sumar objetivos.
            sesion.refresh_from_db()
            assert sesion.survived_minutes == 5, \
                f"complete_session no persistio lo sobrevivido: {sesion.survived_minutes!r}"

            # Un reintento (la TUI postea con timeout=10.0, asi que una respuesta perdida se
            # reintenta) NO puede sobrescribir lo ya archivado: el motor responde `warning` y no
            # paga nada, pero la escritura llegaba igual y dejaba el campo en 0.
            resp = complete_session(f.post(
                "/", {"session_id": sesion.id, "survived_seconds": 0}, format="json"))
            assert resp.data.get("engine_details", {}).get("status") == "warning", \
                "el motor ya no marca el reintento como procesado; este check quedo ciego"
            sesion.refresh_from_db()
            assert sesion.survived_minutes == 5, \
                f"un reintento borro lo sobrevivido: {sesion.survived_minutes!r}"

            # Un valor fuera de rango se rechaza ANTES de que el motor pague, no despues: si
            # pasa, el IntegrityError es un 500 por trabajo ya cobrado, y la cola del movil
            # solo suelta un item con 2xx.
            otra = DeepWorkSession.objects.create(duration_minutes=15,
                                                  category="Rango de prueba")
            resp = complete_session(f.post(
                "/", {"session_id": otra.id, "survived_seconds": -899}, format="json"))
            assert resp.status_code == 400, \
                f"un tiempo negativo no fue rechazado: {resp.status_code}"
            otra.refresh_from_db()
            assert not otra.completed, "el motor cobro una sesion con tiempo invalido"

            print("OK · habito y sesion devuelven un hecho; el rechazo no, y el abandono no miente")
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass
    finally:
        # The rollback covers the writes, but this check runs the reward engine against the
        # live guild row. Two test habits moved prestige 102 -> 57 once already.
        from posada.models import GuildProfile as _GP
        assert _GP.objects.get(id=1).prestige == prestigio_antes, \
            "el prestigio del gremio no volvio a su valor: revisalo a mano"


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
        test_habit_pays_and_saves_in_one_transaction,
        test_finish_book_rejects_an_id_that_does_not_exist,
        test_finish_book_without_an_id_still_works,
        test_the_collection_capture_verbs_answer_with_a_fact,
        test_the_two_posada_verbs_answer_with_a_fact,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_capture_dates: {len(PRUEBAS)}/{len(PRUEBAS)}")
