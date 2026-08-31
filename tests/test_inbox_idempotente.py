"""Standalone check for the three barcode inboxes the Transmisor's scanner writes to.

Run: docker compose exec web python -m tests.test_inbox_idempotente

The scanner's most likely failure is not a crash, it is a stuck queue. `isbn` and `barcode`
are unique, and the mobile queue only removes an item once the server answers 2xx — so a
barcode scanned twice used to answer 400 and stay in the queue for ever, with nothing but
"HTTP 400" on screen to explain it. Scanning the same shelf across two sessions is the
normal case, not an edge one.

The three modules diverge on the field name (`isbn` for books, `barcode` for the other two),
which is audit §3.1's exact trap, so each is checked against its own name rather than one
being assumed to stand for all three.

Every check runs inside a transaction that is rolled back, so it is safe against live data.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from books.models import ScanInbox  # noqa: E402
from books.views import ScanInboxViewSet  # noqa: E402
from music.models import MusicInbox  # noqa: E402
from music.views import MusicInboxViewSet  # noqa: E402
from movies.models import MovieInbox  # noqa: E402
from movies.views import MovieInboxViewSet  # noqa: E402

FABRICA = APIRequestFactory()

# (label, viewset, model, wire field name). The field names are read off the models, not
# guessed: books/models.py:157 declares `isbn`, the other two declare `barcode`.
BANDEJAS = (
    ("libro", ScanInboxViewSet, ScanInbox, "isbn", "9788437604947"),
    ("peli", MovieInboxViewSet, MovieInbox, "barcode", "7321900000001"),
    ("disco", MusicInboxViewSet, MusicInbox, "barcode", "0724384960651"),
)


def rollback(fn):
    try:
        with transaction.atomic():
            fn()
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_first_scan_is_stored():
    def cuerpo():
        for etiqueta, vs, modelo, campo, codigo in BANDEJAS:
            vista = vs.as_view({"post": "create"})
            antes = modelo.objects.count()
            resp = vista(FABRICA.post("/", {campo: codigo}, format="json"))
            assert resp.status_code == 201, f"{etiqueta}: primera vez dio {resp.status_code}"
            assert modelo.objects.count() == antes + 1, f"{etiqueta}: no guardo"
    rollback(cuerpo)
    print("OK · un codigo nuevo se guarda en las tres bandejas (201)")


def test_second_scan_is_accepted_without_saving():
    """The whole point: a 2xx is what lets the mobile queue drop the item."""
    def cuerpo():
        for etiqueta, vs, modelo, campo, codigo in BANDEJAS:
            vista = vs.as_view({"post": "create"})
            vista(FABRICA.post("/", {campo: codigo}, format="json"))
            despues_de_la_primera = modelo.objects.count()

            resp = vista(FABRICA.post("/", {campo: codigo}, format="json"))
            assert resp.status_code == 200, (
                f"{etiqueta}: un duplicado dio {resp.status_code}; la captura se quedaria "
                f"atascada en la cola del telefono para siempre"
            )
            assert modelo.objects.count() == despues_de_la_primera, (
                f"{etiqueta}: guardo el duplicado igual"
            )
    rollback(cuerpo)
    print("OK · un codigo repetido responde 200 sin guardar, y la cola puede soltarlo")


def test_an_empty_code_is_still_rejected():
    """Idempotence must not become 'accepts anything'."""
    def cuerpo():
        for etiqueta, vs, modelo, campo, _ in BANDEJAS:
            vista = vs.as_view({"post": "create"})
            resp = vista(FABRICA.post("/", {}, format="json"))
            assert resp.status_code == 400, (
                f"{etiqueta}: un POST sin {campo} dio {resp.status_code}, se esperaba 400"
            )
    rollback(cuerpo)
    print("OK · un POST sin codigo sigue siendo 400 en las tres")


def test_the_wire_field_names_have_not_drifted():
    """Task 17's SC_CAMPO in app.js sends these exact names. A rename here is a silent 400."""
    def cuerpo():
        for etiqueta, vs, modelo, campo, codigo in BANDEJAS:
            assert any(f.name == campo for f in modelo._meta.get_fields()), (
                f"{etiqueta}: el modelo ya no tiene el campo '{campo}' que el movil envia"
            )
            vista = vs.as_view({"post": "create"})
            resp = vista(FABRICA.post("/", {campo: codigo}, format="json"))
            assert resp.status_code == 201, f"{etiqueta}: '{campo}' dejo de ser aceptado"
    rollback(cuerpo)
    print("OK · isbn/barcode/barcode siguen siendo los nombres que el movil manda")


if __name__ == "__main__":
    PRUEBAS = [
        test_first_scan_is_stored,
        test_second_scan_is_accepted_without_saving,
        test_an_empty_code_is_still_rejected,
        test_the_wire_field_names_have_not_drifted,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_inbox_idempotente: {len(PRUEBAS)}/{len(PRUEBAS)}")
