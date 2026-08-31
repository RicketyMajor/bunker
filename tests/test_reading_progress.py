"""Standalone check for per-book reading progress.

Run: docker compose exec web python -m tests.test_reading_progress

The migration's blast radius is case 4: rows written before the FK existed must keep being
counted, by tracker_stats and by the reading streak in the BFF. Everything else here is new
behaviour.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from datetime import timedelta  # noqa: E402

from django.db import transaction  # noqa: E402
from django.db.models import Sum  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from books.models import Book, ReadingSession  # noqa: E402
from books.views import log_pages, tracker_stats  # noqa: E402

factory = APIRequestFactory()


def post(payload):
    return log_pages(factory.post("/", payload, format="json"))


def run():
    with transaction.atomic():
        libro = Book.objects.create(title="Los detectives salvajes", page_count=608)

        # 1 — la primera posición cuenta desde cero
        assert post({"book_id": libro.id, "current_page": 240}).status_code == 201
        s = ReadingSession.objects.filter(book=libro).latest("id")
        assert s.pages_read == 240, s.pages_read
        assert s.current_page == 240
        print("OK · la primera posicion registra 240 paginas")

        # 2 — la segunda registra el delta, no la posición
        assert post({"book_id": libro.id, "current_page": 272}).status_code == 201
        s = ReadingSession.objects.filter(book=libro).latest("id")
        assert s.pages_read == 32, f"registro {s.pages_read}, se esperaba 32"
        print("OK · la segunda registra el delta de 32")

        # 3 — retroceder no escribe un delta negativo
        assert post({"book_id": libro.id, "current_page": 100}).status_code == 201
        s = ReadingSession.objects.filter(book=libro).latest("id")
        assert s.pages_read == 0, f"registro {s.pages_read}, se esperaba 0"
        assert s.current_page == 100
        print("OK · retroceder registra 0, no un negativo")

        # 4 — las filas viejas, sin libro, siguen sumando en los dos consumidores
        antes = tracker_stats(factory.get("/")).data["pages_this_month"]
        ReadingSession.objects.create(pages_read=55, date=timezone.localdate())
        sueltas = ReadingSession.objects.filter(book__isnull=True).aggregate(
            Sum("pages_read"))["pages_read__sum"]
        assert sueltas >= 55, "las filas sin libro dejaron de contarse"
        despues = tracker_stats(factory.get("/")).data["pages_this_month"]
        assert despues == antes + 55, (
            f"tracker_stats ignoro la fila sin libro: {antes} -> {despues}"
        )
        print("OK · las filas sin libro siguen sumando, y tracker_stats las ve")

        # 5 — una posicion imposible se rechaza antes de inflar el total
        r = post({"book_id": libro.id, "current_page": 6080})
        assert r.status_code == 400, f"acepto 6080 de 608 paginas ({r.status_code})"
        print("OK · una pagina mayor que el libro se rechaza con 400")

        # 6 — current_page sin book_id no tiene contra que calcular
        r = post({"current_page": 50})
        assert r.status_code == 400, f"acepto current_page sin libro ({r.status_code})"
        print("OK · current_page sin book_id se rechaza con 400")

        # 7 — el modo antiguo, que es el que usa el TUI hoy
        assert post({"pages": 10}).status_code == 201
        s = ReadingSession.objects.latest("id")
        assert s.pages_read == 10 and s.book_id is None and s.current_page is None
        assert post({"pages": 0}).status_code == 400
        assert post({"pages": "diez"}).status_code == 400
        print("OK · el modo suelto sigue igual: 10 paginas sin libro, y 0 o basura -> 400")

        # 8 — capturas que llegan desordenadas, que es lo normal en una cola offline:
        # se lee el viernes, se sincroniza el miércoles, y para entonces ya hay una
        # posición más reciente. Lo que no puede pasar es que invente páginas.
        otro = Book.objects.create(title="2666", page_count=1125)
        hace_tres = timezone.localdate() - timedelta(days=3)
        assert post({"book_id": otro.id, "current_page": 300}).status_code == 201
        assert post({"book_id": otro.id, "current_page": 250,
                     "occurred_on": hace_tres.isoformat()}).status_code == 201
        tardia = ReadingSession.objects.filter(book=otro).latest("id")
        assert tardia.date == hace_tres, f"se archivo el {tardia.date}"
        assert tardia.pages_read == 0, (
            f"una captura atrasada invento {tardia.pages_read} paginas"
        )
        total_otro = ReadingSession.objects.filter(book=otro).aggregate(
            Sum("pages_read"))["pages_read__sum"]
        assert total_otro == 300, f"el total del libro se inflo a {total_otro}"
        print("OK · una captura atrasada se archiva en su dia y no infla el total")

        # 9 — la consulta que el briefing de bunker-responde necesita: "el libro mas cerca
        # de terminarse". Ordena por paginas restantes, no por recencia, que es justo el
        # criterio que hoy no se podia calcular porque ReadingSession no sabia de que libro
        # hablaba. Con dos libros en curso el orden tiene que ser el correcto, no el ultimo.
        #
        # Acotado a los dos libros que esta prueba siembra, y no es cosmetico: hasta el
        # 2026-08-17 preguntaba por TODA la tabla y afirmaba que habia exactamente dos libros
        # con posicion. Eso solo era cierto mientras nadie hubiera capturado paginas de verdad.
        # La primera captura real desde el telefono — ReadingSession 1202, Jujutsu Kaisen,
        # la fila que el handoff 017 registro como prueba de que Task 10 funcionaba — metio un
        # tercer libro y dejo `bunker doctor` en rojo permanente. La prueba quedo falsificada
        # por el sistema funcionando bien, que es la peor clase de check.
        #
        # Regla que deja: una prueba que lee la base viva no puede afirmar un CONTEO. O acota a
        # lo que ella misma sembro, o afirma una relacion (este antes que aquel) que el ruido
        # no pueda romper. Aqui se acota, porque asi el resultado no depende del dia.
        mios = [libro.id, otro.id]
        posiciones = {}
        for s in (ReadingSession.objects
                  .filter(book_id__in=mios, current_page__isnull=False)
                  .order_by("date", "id")):
            posiciones[s.book_id] = s.current_page  # la ultima posicion de cada libro gana

        faltan = sorted(
            (b.page_count - posiciones[b.id], b.title)
            for b in Book.objects.filter(id__in=list(posiciones)) if b.page_count
        )
        assert len(faltan) == 2, faltan
        assert faltan[0] == (508, "Los detectives salvajes"), faltan
        assert faltan[1] == (825, "2666"), faltan
        print("OK · 'el libro mas cerca de terminarse' es calculable y ordena bien:", faltan)

        raise transaction.TransactionManagementError("rollback")


if __name__ == "__main__":
    try:
        run()
    except transaction.TransactionManagementError:
        print("\ntest_reading_progress: 9/9 (revertido, la base quedo intacta)")
