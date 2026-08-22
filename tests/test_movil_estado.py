"""Standalone check for the capture-support endpoint the Transmisor reads on every open.

Run: docker compose exec web python -m tests.test_movil_estado

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

from django.conf import settings  # noqa: E402
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
    esperadas = {"leyendo", "habitos_pendientes", "libros", "peliculas", "albums",
                 "aventureros"}
    assert set(datos) == esperadas, f"claves {sorted(datos)}, se esperaba {sorted(esperadas)}"
    for clave in ("habitos_pendientes", "libros", "peliculas", "albums", "aventureros"):
        assert isinstance(datos[clave], list), f"{clave} no es una lista"
    assert datos["leyendo"] is None or isinstance(datos["leyendo"], dict)
    print("OK · las seis claves que renderizan las hojas de captura y el temporizador")


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


def test_a_finished_book_stops_being_the_one_you_are_reading():
    """Found while building Task 15, which is what made it reachable.

    The book correctly leaves `libros` once is_read is set, but the session that carries its
    last position outlives it, so `leyendo` kept offering a finished book — with a + PÁGINAS
    button on it — until another book was logged. Nothing else in the project reads this.
    """
    def cuerpo():
        libro = Book.objects.create(title="Libro terminado", page_count=300, is_read=False)
        ReadingSession.objects.create(date=HOY, pages_read=150, book=libro, current_page=150)
        assert pedir()["leyendo"]["book_id"] == libro.id, "no lo ofrecio ni estando en curso"

        libro.is_read = True
        libro.save(update_fields=["is_read"])
        leyendo = pedir()["leyendo"]
        assert leyendo is None or leyendo["book_id"] != libro.id, (
            "un libro ya terminado sigue apareciendo como 'leyendo ahora'"
        )
        assert not any(x["id"] == libro.id for x in pedir()["libros"]), (
            "y ademas se seguiria ofreciendo para terminar"
        )
    rollback(cuerpo)
    print("OK · terminar un libro lo saca de 'leyendo ahora', no solo del inventario")


def test_query_budget():
    """The constraint the spec sets: this is not a second dashboard."""
    with CaptureQueriesContext(connection) as ctx:
        pedir()
    assert len(ctx) <= 6, f"{len(ctx)} consultas: se convirtio en un segundo dashboard"
    print(f"OK · {len(ctx)} consultas, dentro del presupuesto de 6")


def test_el_estado_trae_la_nomina():
    """The timer sheet picks an adventurer from this, so the roster travels with the snapshot."""
    from posada.models import AdventurerClass
    datos = pedir()
    assert "aventureros" in datos, "el estado no trae la nomina"
    for a in datos["aventureros"]:
        assert {"id", "name", "class_name", "level"} <= set(a), f"aventurero incompleto: {a}"
        # Not `!= a.get("adv_class")`: that key is not in the payload, so the comparison is
        # against None and the check could never go red. The raw 3-letter code is the thing
        # that must not arrive — the TUI shipped "BBN" for every class by reading it.
        assert a["class_name"] not in AdventurerClass.values, \
            f"esta mandando el codigo crudo: {a['class_name']!r}"
    print(f"OK · el estado trae {len(datos['aventureros'])} aventurero(s) con clase legible")


def test_el_manifiesto_sigue_el_contenido():
    """The hash is the whole mechanism; a constant would be worse than no endpoint."""
    from bunker_core.views import MOVIL_ASSETS, movil_assets

    def version():
        resp = movil_assets(FABRICA.get('/api/movil/assets/'))
        assert resp.status_code == 200, f"el manifiesto devolvio {resp.status_code}"
        return json.loads(resp.content)

    uno = version()
    assert set(uno["files"]) == set(MOVIL_ASSETS), \
        f"el manifiesto no declara los tres archivos: {sorted(uno['files'])}"
    # Relative, never absolute: build_absolute_uri reflects the Host header and ALLOWED_HOSTS
    # is ['*'], and the APK runs whatever these point at inside a WebView.
    for nombre, url in uno["files"].items():
        assert url.startswith("/"), f"{nombre} trae una URL absoluta: {url!r}"

    # Cada URL anunciada tiene que servir EL MISMO fichero que se hasheó, y esto no es
    # pedantería: el 2026-08-21 el manifiesto reconstruía la URL como f"/static/movil/{nombre}"
    # mientras el fichero vivía en `dist/`. La URL resultante respondía **200** — porque
    # `bunker_core/static/movil/main.js` existe: es el entry point SIN empaquetar — así que el
    # APK habría bajado un módulo ES con `import`, ejecutado como script clásico, y mostrado una
    # página que renderiza y no corre nada. Los dos status eran 200; solo el CUERPO los separaba.
    for nombre, url in uno["files"].items():
        if nombre == "app.html":
            continue          # lo sirve una vista, no un fichero estático
        servido = settings.BASE_DIR / ("bunker_core" + url)
        hasheado = settings.BASE_DIR / MOVIL_ASSETS[nombre]
        assert servido.exists(), f"{nombre} se anuncia en {url} y ahí no hay fichero"
        assert servido.read_bytes() == hasheado.read_bytes(), (
            f"{nombre} se anuncia en {url}, que sirve un fichero distinto del hasheado "
            f"({MOVIL_ASSETS[nombre]})")

    # El fichero que se toca sale del propio manifiesto: nombrar uno a mano ata este check a
    # una lista de assets que ya cambió una vez.
    tocable = next(n for n in sorted(MOVIL_ASSETS) if n != "app.html")
    ruta = settings.BASE_DIR / MOVIL_ASSETS[tocable]
    original = ruta.read_bytes()
    try:
        ruta.write_bytes(original + b"\n// tocado por el test\n")
        dos = version()
    finally:
        ruta.write_bytes(original)
    assert uno["version"] != dos["version"], "el hash no cambio al cambiar un archivo"
    assert version()["version"] == uno["version"], "no volvio al hash original"
    print("OK · el manifiesto sigue el contenido y sirve rutas relativas")


def test_panel_es_una_ruta_real_con_su_marca():
    """`/panel/` resolves, renders the same template, and carries the panel's own markup.

    Three things this catches that a 200 does not. The route could resolve to the capture
    template with no panel markup at all, in which case `Panel.montar()` finds no `#p-briefing`
    and returns silently — a blank page and no error, which is the failure mode this whole task
    exists to make impossible. The `data-fuente` attribute is the block's endpoint and lives in
    the markup, so losing it makes every block fetch `undefined`. And the state CSS must be
    prefixed with `#panel`: unprefixed, `#panel section` outranks it and the states lose their
    background — measured in the browser 2026-08-21, --dim landed on --bg-alt at 4.17:1.
    """
    from django.test import Client

    respuesta = Client().get('/panel/')
    assert respuesta.status_code == 200, f"/panel/ dio {respuesta.status_code}"
    html = respuesta.content.decode()

    assert 'id="panel"' in html, "/panel/ no trae el <main id=\"panel\">"
    assert 'id="p-datos"' in html, "/panel/ no trae ningun bloque que montar"
    assert 'id="p-serie"' in html, "/panel/ perdio el bloque de la serie"
    assert '<h2>ACTIVIDAD POR MES</h2>' in html, (
        "el bloque de la serie perdio su h2; h1 -> h3 salta un nivel de encabezado")
    assert 'data-fuente="/api/panel/"' in html, (
        "el bloque perdio su data-fuente; `pedir` recibiria undefined")
    assert 'body[data-superficie="panel"] #home' in html, (
        "sin el conmutador de superficie el panel se pinta ENCIMA de la captura")
    for estado in ('cargando', 'sin-enlace', 'rechazado', 'roto', 'vacio'):
        assert f'#panel [data-estado="{estado}"]' in html, (
            f"el estado {estado} no tiene regla propia, o perdio el prefijo #panel que le gana "
            f"a `#panel section`")

    # La misma vista para las tres rutas: un segundo template es la segunda pagina que
    # mantener sincronizada, que es lo que mato al panel original.
    assert Client().get('/movil/').content.decode().count('id="p-datos"') == 1, (
        "/movil/ y /panel/ dejaron de ser el mismo template")
    print("OK · /panel/ existe, monta y sus cinco estados tienen regla propia")


if __name__ == "__main__":
    PRUEBAS = [
        test_payload_shape_is_the_contract,
        test_habit_due_today_is_offered,
        test_habit_already_done_today_is_not_offered,
        test_habit_not_scheduled_today_is_not_offered,
        test_leyendo_is_the_most_recent_session_with_a_position,
        test_a_finished_book_stops_being_the_one_you_are_reading,
        test_el_estado_trae_la_nomina,
        test_el_manifiesto_sigue_el_contenido,
        test_query_budget,
        test_panel_es_una_ruta_real_con_su_marca,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_movil_estado: {len(PRUEBAS)}/{len(PRUEBAS)}")
