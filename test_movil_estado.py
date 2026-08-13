"""Standalone check for the capture-support endpoint the Transmisor reads on every open.

Run: docker compose exec web python test_movil_estado.py

Two things can break here without anything else noticing. The payload's five keys are a
contract: Tasks 14-18 render exactly those names, so a rename is a blank screen on the
phone, not an error. And `habitos_pendientes` has to mean *due today* — a habit offered on
a day it is not scheduled for pays prestige for a day the penalty engine never scored.

Every check runs inside a transaction that is rolled back, so it is safe against live data.
"""
import json
import os
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test import RequestFactory  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.utils import timezone  # noqa: E402

from bunker_core.views import movil_estado  # noqa: E402
from catalog.models import Author, Book, ReadingSession  # noqa: E402
from posada.models import DailyHabit  # noqa: E402

HOY = timezone.localdate()
FABRICA = RequestFactory()


def pedir():
    """Call the view and return the decoded payload."""
    respuesta = movil_estado(FABRICA.get('/api/movil/estado/'))
    assert respuesta.status_code == 200, f"el endpoint devolvio {respuesta.status_code}"
    return json.loads(respuesta.content)


def rollback(fn):
    """Run fn inside a transaction that is always undone."""
    try:
        with transaction.atomic():
            fn()
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_payload_shape_is_the_contract():
    datos = pedir()
    esperadas = {"leyendo", "habitos_pendientes", "libros", "peliculas", "albums"}
    assert set(datos) == esperadas, f"claves {sorted(datos)}, se esperaba {sorted(esperadas)}"
    for clave in ("habitos_pendientes", "libros", "peliculas", "albums"):
        assert isinstance(datos[clave], list), f"{clave} no es una lista"
    assert datos["leyendo"] is None or isinstance(datos["leyendo"], dict)
    print("OK · las cinco claves que renderizan las tareas 14-18")


def test_habit_due_today_is_offered():
    def cuerpo():
        h = DailyHabit.objects.create(
            name="Habito de hoy", difficulty="B", valid_days="0,1,2,3,4,5,6")
        ids = [x["id"] for x in pedir()["habitos_pendientes"]]
        assert h.id in ids, "un habito valido hoy y sin marcar no fue ofrecido"
    rollback(cuerpo)
    print("OK · un habito valido hoy y sin marcar aparece")


def test_habit_already_done_today_is_not_offered():
    def cuerpo():
        h = DailyHabit.objects.create(
            name="Habito ya marcado", difficulty="B", valid_days="0,1,2,3,4,5,6",
            last_completed_date=HOY)
        ids = [x["id"] for x in pedir()["habitos_pendientes"]]
        assert h.id not in ids, "un habito ya marcado hoy se ofrecio de nuevo"
    rollback(cuerpo)
    print("OK · un habito ya marcado hoy desaparece")


def test_habit_not_scheduled_today_is_not_offered():
    """The deviation from the plan: the plan filtered only by last_completed_date.

    Neither the TUI nor complete_habit reads valid_days, but the penalty engine does
    (legacy.py:481). Offering an out-of-schedule habit is free prestige.
    """
    otros_dias = ",".join(str(d) for d in range(7) if d != HOY.weekday())

    def cuerpo():
        fuera = DailyHabit.objects.create(
            name="Habito de otro dia", difficulty="B", valid_days=otros_dias)
        dentro = DailyHabit.objects.create(
            name="Habito de hoy", difficulty="B", valid_days=str(HOY.weekday()))
        ids = [x["id"] for x in pedir()["habitos_pendientes"]]
        assert fuera.id not in ids, "se ofrecio un habito que hoy no toca"
        assert dentro.id in ids, "se escondio un habito que hoy si toca"
    rollback(cuerpo)
    print(f"OK · hoy es weekday {HOY.weekday()}: solo se ofrece lo que toca")


def test_leyendo_is_the_most_recent_session_with_a_position():
    """Rows without a book or a page are invisible here, which is the live situation.

    Every ReadingSession written before the 2026-08 migration has book=NULL, so `leyendo`
    is legitimately null on this database until a page is logged from the phone.
    """
    def cuerpo():
        autor = Author.objects.create(name="Autor de prueba")
        viejo = Book.objects.create(title="Libro viejo", author=autor, page_count=300)
        nuevo = Book.objects.create(title="Libro nuevo", author=autor, page_count=500)

        # Written out of order on purpose: the queue syncs late, so insertion order and
        # event order are not the same thing.
        ReadingSession.objects.create(
            date=HOY, pages_read=10, book=nuevo, current_page=120)
        ReadingSession.objects.create(
            date=HOY - timedelta(days=1), pages_read=10, book=viejo, current_page=40)
        ReadingSession.objects.create(
            date=HOY + timedelta(days=0), pages_read=5, book=None, current_page=None)

        leyendo = pedir()["leyendo"]
        assert leyendo is not None, "habia sesiones con libro y pagina, y devolvio null"
        assert leyendo["book_id"] == nuevo.id, f"eligio {leyendo['title']}"
        assert leyendo["current_page"] == 120, f"posicion {leyendo['current_page']}"
        assert leyendo["page_count"] == 500
        assert leyendo["author"] == "Autor de prueba"
    rollback(cuerpo)
    print("OK · leyendo es la sesion mas reciente que tiene libro y posicion")


def test_query_budget():
    """The constraint the spec sets: this is not a second dashboard."""
    with CaptureQueriesContext(connection) as ctx:
        pedir()
    assert len(ctx) <= 6, f"{len(ctx)} consultas: se convirtio en un segundo dashboard"
    print(f"OK · {len(ctx)} consultas, dentro del presupuesto de 6")


if __name__ == "__main__":
    PRUEBAS = [
        test_payload_shape_is_the_contract,
        test_habit_due_today_is_offered,
        test_habit_already_done_today_is_not_offered,
        test_habit_not_scheduled_today_is_not_offered,
        test_leyendo_is_the_most_recent_session_with_a_position,
        test_query_budget,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_movil_estado: {len(PRUEBAS)}/{len(PRUEBAS)}")
