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
    print(f"OK · los {len(casos)} verbos rechazan el futuro con 400")


# Cuatro pruebas de hábitos vivían aquí: fecha pasada -> 409, hoy funciona, un día que no
# toca -> 409, y que el pago y la racha se escriben en UNA transacción. Se fueron con La Posada
# el 2026-08-27, y con ellas el único verbo del Transmisor que podía ser rechazado por su fecha.
# Lo que queda es lo que siempre fue de inventario: páginas, libros, películas y discos.


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
    `feedback` exists and is non-empty on all four verbs — five cases, because `log_pages`
    is exercised both loose and against a book. Second, that `message` survived
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


# `test_the_two_posada_verbs_answer_with_a_fact` comprobaba que `habito` y `sesion` devolvían
# un hecho medido y no una confirmación genérica. Los dos verbos salieron del Transmisor el
# 2026-08-27; los nueve que quedan los cubre `test_the_collection_capture_verbs_answer_with_a_fact`.


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
        test_finish_book_rejects_an_id_that_does_not_exist,
        test_finish_book_without_an_id_still_works,
        test_the_collection_capture_verbs_answer_with_a_fact,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_capture_dates: {len(PRUEBAS)}/{len(PRUEBAS)}")
