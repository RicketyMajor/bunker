"""Check for the briefing payload. Runs inside the container:

    docker compose exec -T web python -m tests.test_briefing

Everything happens inside a transaction with a forced rollback, so it touches no real data.

The assertion that matters is the last one: **building the briefing must not pay anything.**
`/posada/api/habits/` and `/api/dashboard/` both settle past calendar events on every GET,
and guild prestige moved 75 → 102 once because of it. If the briefing is ever built by
calling one of them, opening Bunker becomes a payment — see state-of-the-project.md §1.
"""

import os
from datetime import date, timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import IntegrityError, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from bunker_core.briefing import (  # noqa: E402
    _semana_actual, _semana_anterior, construir_briefing, marcar_visto,
)
from django.db import connection  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from movies.models import MovieAnnualRecord  # noqa: E402
from bunker_core.models import BunkerState  # noqa: E402
from catalog.models import Author, Book, ReadingSession  # noqa: E402

# Medido, no supuesto: books cuesta 2 consultas agrupadas (AnnualRecord + ReadingSession) y
# movies y music 1 cada uno. Si cambia, el número es la cuenta y el check dice cuál salió.
COSTE_REVISION = 4

_checks = 0

# `hoy`, `habito_en_riesgo` y `logros_nuevos` eran tres claves más hasta el 2026-08-27:
# las tres eran de la Posada (hábitos pendientes, racha en riesgo, logros desbloqueados).
CLAVES = ("ayer", "libro_mas_cerca", "conclusiones", "show_review", "review")


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _claves_leidas(clase):
    """Las claves literales que una pantalla lee, agrupadas por la variable de la que cuelgan.

    Devuelve `{'d': {...}, 'self.datos': {...}, 'ayer': {...}}`. Reconoce las DOS formas —
    `x.get("k")` y `x["k"]`— y las dos raíces posibles: una variable local (`d`, `ayer`) y un
    atributo de la instancia (`self.datos`, `self.review`). Rastrear sólo la local dejaba pasar
    verde una lectura escrita como `self.datos.get(...)`, comprobado ejecutando.
    """
    import ast

    def raiz(nodo):
        if isinstance(nodo, ast.Name):
            return nodo.id
        if (isinstance(nodo, ast.Attribute) and isinstance(nodo.value, ast.Name)
                and nodo.value.id == 'self'):
            return f'self.{nodo.attr}'
        return None

    leidas = {}
    for nodo in ast.walk(clase):
        origen = clave = None
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == 'get' and nodo.args
                and isinstance(nodo.args[0], ast.Constant)
                and isinstance(nodo.args[0].value, str)):
            origen, clave = raiz(nodo.func.value), nodo.args[0].value
        elif (isinstance(nodo, ast.Subscript) and isinstance(nodo.slice, ast.Constant)
                and isinstance(nodo.slice.value, str)):
            origen, clave = raiz(nodo.value), nodo.slice.value
        if origen:
            leidas.setdefault(origen, set()).add(clave)
    return leidas


def _comprobar_pantalla(fichero, nombre_clase, ambitos):
    """Lo que una pantalla LEE tiene que estar en lo que el productor EMITE.

    `ambitos` es una lista de `(etiqueta, raíces, dict vivo)`. Las `raíces` de un mismo ámbito
    son ALIAS —`d` y `self.datos` son el mismo payload—, así que la vacuidad se exige sobre su
    UNIÓN: pedirla raíz por raíz pone en rojo a una pantalla que sólo usa una de las dos formas.

    Una raíz que la pantalla usa y no está aquí no se comprueba, y eso es deliberado: `libro`,
    `m` o `fuente` son elementos de una lista, no el payload. **Techo declarado:** un
    `libro['restantes']` que el productor renombre revienta con `KeyError` dentro de `compose`,
    ruidosamente, y este check no lo ve. Lo que cubre es la muerte SILENCIOSA, que es la que
    nadie encuentra.
    """
    import ast
    from django.conf import settings

    ruta = settings.BASE_DIR / fichero
    # Una ruta que no existe aporta cero claves EN SILENCIO, y un `<=` sobre el vacío es
    # cierto: sin esto el check saldría verde sin haber leído nada.
    check(ruta.is_file(), f"{nombre_clase} está donde se le busca: {ruta}")

    arbol = ast.parse(ruta.read_text(encoding='utf-8'))
    clase = next((n for n in ast.walk(arbol)
                  if isinstance(n, ast.ClassDef) and n.name == nombre_clase), None)
    check(clase is not None, f"{nombre_clase} sigue llamándose así en {fichero}")

    leidas = _claves_leidas(clase)
    for etiqueta, raices, vivo in ambitos:
        union = set().union(*(leidas.get(r, set()) for r in raices))
        # Vacuidad: si el barrido no matchea nada, el `<=` de abajo es cierto sobre la nada. El
        # umbral no se clava en el número de hoy a propósito — hacerlo convierte cualquier
        # cambio legítimo del payload en un rojo con el mensaje equivocado.
        check(union, f"el barrido encontró claves de '{etiqueta}' en {nombre_clase}: {union}")
        sobran = union - set(vivo)
        check(not sobran,
              f"{nombre_clase} no lee claves de '{etiqueta}' que ya no se emiten: {sobran}")


def _comprobar_claves_del_briefing(datos):
    """Las DOS pantallas que comen del briefing, contra lo que el briefing emite.

    La separación del 2026-08-27 quitó claves del productor y actualizó `CLAVES` aquí arriba,
    pero nadie barrió a los consumidores. `BriefingScreen` siguió leyendo `minutos_deep_work`,
    `habitos`, `hoy.habitos_pendientes`, `habito_en_riesgo` y `logros_nuevos`; `WeeklyReviewScreen`
    siguió leyendo `prestigio` y pintando once líneas con él. Todas con `.get()`, todas muertas
    EN SILENCIO —salvo el `Label` de `hoy`, incondicional, que pintó «Hoy: nada pendiente.»
    durante meses—. Ningún check lo vio porque todos miraban al productor.

    **Las dos pantallas, no una.** Arreglar sólo la que se encontró primero es lo que dejó viva
    la segunda: `WeeklyReviewScreen` sobrevivió a la sesión que arregló `BriefingScreen` y la
    encontró `/code-review` al día siguiente.

    Lee el ÁRBOL DE SINTAXIS, no una lista escrita a mano: dos listas comparadas entre sí
    concuerdan perfectamente mientras las dos están mal. Misma forma que
    `test_bundle._comprobar_shell_del_sw`, que lee las etiquetas `{% static %}` de app.html.
    """
    from bunker_core.briefing import _revision

    _comprobar_pantalla('cli/tui/modals.py', 'BriefingScreen', [
        ('el briefing', ('d', 'self.datos'), datos),
        ("ayer", ('ayer',), datos['ayer']),
    ])
    # `datos['review']` es None seis días de cada siete, así que se pregunta al productor
    # directamente en vez de esperar a que toque revisión.
    _comprobar_pantalla('cli/tui/screens.py', 'WeeklyReviewScreen', [
        ('la revisión', ('review', 'self.review'), _revision()),
    ])


def run_tests():
    hoy = timezone.localdate()

    with transaction.atomic():
        # 1. Todas las claves del contrato existen aunque no haya nada que contar.
        datos = construir_briefing()
        for clave in CLAVES:
            check(clave in datos, f"el briefing trae la clave '{clave}'")
        check(isinstance(datos["conclusiones"], list), "conclusiones es una lista")
        check(isinstance(datos["ayer"]["paginas"], int), "ayer.paginas es un entero, no None")

        # 1b. Y lo que la pantalla LEE existe en lo que el productor EMITE. Ver el docstring
        #     de `_comprobar_claves_del_briefing`: esta es la mitad que faltaba el 2026-08-27.
        _comprobar_claves_del_briefing(datos)

        # 2. Un libro a 28 páginas del final es el más cerca.
        autor, _ = Author.objects.get_or_create(name="Autor de prueba")
        cerca = Book.objects.create(title="Casi terminado", author=autor,
                                    isbn="0000000000002", page_count=300)
        lejos = Book.objects.create(title="Recién empezado", author=autor,
                                    isbn="0000000000003", page_count=300)
        ReadingSession.objects.create(date=hoy, pages_read=1, book=cerca, current_page=272)
        ReadingSession.objects.create(date=hoy, pages_read=1, book=lejos, current_page=40)
        datos = construir_briefing()
        check(datos["libro_mas_cerca"]["title"] == "Casi terminado",
              "el libro más cerca es el que menos páginas le faltan, no el más largo")
        check(datos["libro_mas_cerca"]["restantes"] == 28, "cuenta las páginas restantes")

        # 3. Un libro terminado ya no está "cerca de terminarse".
        cerca.is_read = True
        cerca.save()
        datos = construir_briefing()
        check(datos["libro_mas_cerca"] is None or datos["libro_mas_cerca"]["title"] != "Casi terminado",
              "un libro terminado sale de 'libro más cerca'")

        # El check «el briefing NO paga prestigio» vivía aquí y era el que más importaba.
        # El prestigio se fue a La Posada el 2026-08-27, así que ya no hay nada que pagar; lo
        # que sobrevive de esa propiedad es que `construir_briefing` no escribe NADA, y eso lo
        # afirma `test_panel.test_el_panel_no_escribe_nada` censando todas las tablas.

        # El bloque 5 comprobaba `logros_nuevos` contra `last_entry_at`. Los logros eran
        # de la Posada y se fueron con ella el 2026-08-27; `last_entry_at` sigue vivo y lo
        # ejercita el bloque 6, justo debajo.
        estado, _ = BunkerState.objects.get_or_create(id=1)

        # 6. `marcar_visto` es lo único que escribe, y sólo toca la semana si se lo piden.
        estado.last_review_week = ""
        estado.save()
        marcar_visto(False)
        estado.refresh_from_db()
        check(estado.last_entry_at is not None, "marcar_visto registra la entrada")
        check(estado.last_review_week == "",
              "marcar_visto sin revisión no marca la semana como vista")
        check(construir_briefing()["show_review"] is True,
              "con la semana sin marcar, la revisión se ofrece")
        # `marcar_visto` persistía además los dos snapshots de prestigio de la semana
        # revisada. Esa escritura se fue con el ledger a La Posada el 2026-08-27; aquí queda
        # sólo la contabilidad que este repositorio posee: cuándo se entró y qué semana se
        # revisó.
        marcar_visto(True)
        estado.refresh_from_db()
        check(estado.last_review_week != "", "marcar_visto con revisión marca la semana")
        check(len(estado.last_review_week) <= 8,
              f"la clave de semana cabe en el campo: {estado.last_review_week!r}")
        check(construir_briefing()["show_review"] is False,
              "marcada la semana, la revisión no se vuelve a ofrecer")

        # 7. El estado es un singleton de verdad, no por convención.
        try:
            with transaction.atomic():
                BunkerState.objects.create()
            creada = True
        except IntegrityError:
            creada = False
        check(not creada, "no se puede crear una segunda fila de BunkerState")

        # El bloque 8 ejercitaba la regla `valid_days` de los hábitos, que ya tuvo un
        # agujero una vez. Se fue entero con La Posada el 2026-08-27, junto con
        # `hoy.habitos_pendientes` y `habito_en_riesgo`, que eran su superficie.

        # --- Revisión semanal: aparece una vez por semana ISO y se calla el resto. --------
        estado, _ = BunkerState.objects.get_or_create(id=1)
        estado.last_review_week = ""
        estado.save()
        check(construir_briefing()["show_review"] is True,
              "sin revisión esta semana, show_review es True")
        marcar_visto(con_revision=True)
        check(construir_briefing()["show_review"] is False,
              "tras marcarla vista, no vuelve a aparecer esta semana")

        # Diez días sin abrir: la revisión sigue esperando, no caduca.
        estado.refresh_from_db()
        estado.last_review_week = "2020-W01"
        estado.save()
        check(construir_briefing()["show_review"] is True,
              "una revisión de otra semana sigue pendiente por muchos días que pasen")

        # La clave de la semana anterior NO se calcula restando 1 al número. Preguntado HOY
        # —semana 34— restar 1 acierta, y acertará los próximos cuatro meses: la aserción
        # solo podría ponerse roja un día del año. Se pregunta por enero, donde la semana
        # anterior a la 1 es la 52 o la 53 del año PASADO, y cuál de las dos depende del año.
        check(_semana_anterior(date(2027, 1, 4)) == "2026-W53",
              f"antes de la semana 1 de 2027 va la 53 de 2026: {_semana_anterior(date(2027, 1, 4))!r}")
        check(_semana_anterior(date(2026, 1, 1)) == "2025-W52",
              f"y antes de la de 2026, la 52 de 2025: {_semana_anterior(date(2026, 1, 1))!r}")
        check(_semana_anterior() != _semana_actual(),
              "la semana anterior no es la actual")
        check(len(_semana_anterior()) == 8 and "-W" in _semana_anterior(),
              f"la clave anterior es ISO de 8 caracteres: {_semana_anterior()!r}")

        # Cada métrica se compara contra la semana previa, y ninguna llega vacía.
        estado.last_review_week = ""
        estado.save()
        briefing = construir_briefing()
        review = briefing["review"]
        check(review is not None, "con show_review, review no es None")
        # La semana REVISADA es la última COMPLETA, no la que está en curso: la revisión se
        # dispara la primera entrada de la semana nueva —un lunes— y comparar 0 días contra 7
        # pintaba las siete métricas en rojo por construcción.
        check(review["semana"] == _semana_anterior(),
              f"revisa la última semana COMPLETA, no la que está en curso: {review['semana']!r}")
        check(review["semana"] != _semana_actual(),
              "la semana en curso no es la que se revisa")
        check(review["anterior"] == _semana_anterior(timezone.localdate() - timedelta(days=7)),
              f"y la compara contra la anterior a esa: {review['anterior']!r}")

        # Lo que la revisión reporta tiene que ser lo de la semana revisada, no lo de hoy.
        # Una lectura de HOY —semana en curso— no puede aparecer en ella. Iba sobre los
        # minutos de Deep Work hasta el 2026-08-27; `books` es el único módulo con monto que
        # queda, así que la propiedad se comprueba con las páginas.
        antes_pag = next(m for m in review["metricas"] if m["etiqueta"] == "Páginas")
        ReadingSession.objects.create(date=timezone.localdate(), pages_read=999, book=cerca)
        estado.last_review_week = ""
        estado.save()
        despues_pag = next(m for m in construir_briefing()["review"]["metricas"]
                           if m["etiqueta"] == "Páginas")
        check(despues_pag["actual"] == antes_pag["actual"],
              f"999 páginas de HOY no entran en la revisión de la semana pasada: {despues_pag}")
        check(len(review["metricas"]) == 4, f"cuatro métricas, no {len(review['metricas'])}")
        for m in review["metricas"]:
            check("actual" in m and "previa" in m,
                  f"la métrica '{m['etiqueta']}' se compara contra la semana previa")
            check(isinstance(m["actual"], int) and isinstance(m["previa"], int),
                  f"la métrica '{m['etiqueta']}' trae enteros, nunca None")

        # TRES módulos distintos, no cuatro llamadas: books sale dos veces en la lista de
        # métricas y se consulta UNA. books cuesta 2 consultas (registros + páginas), los
        # otros 1. Eran cinco módulos y +3 de prestigio y +1 de logros hasta el 2026-08-27.
        #
        # El calentamiento que había aquí SE FUE con la escritura, 2026-08-21. Existía porque
        # la primera revisión de una semana nueva costaba 17: `resumen_semana` construía los
        # dos snapshots y `update_or_create` gastaba 8 statements en savepoints, así que el
        # número dependía del orden en que corrieran los checks de más arriba. Ahora
        # `construir_briefing` no escribe, y las dos semanas cuestan una consulta cada una
        # tanto si hay fila de snapshot como si no — el número es estable por construcción.
        estado.last_review_week = ""
        estado.save()
        with CaptureQueriesContext(connection) as con_rev:
            construir_briefing()
        estado.last_review_week = _semana_actual()
        estado.save()
        with CaptureQueriesContext(connection) as sin_rev:
            construir_briefing()
        coste = len(con_rev) - len(sin_rev)
        check(coste == COSTE_REVISION,
              f"la revisión cuesta {COSTE_REVISION} consultas (3 módulos, books doble), "
              f"no {coste}")

        # Y el día que no toca no se paga: el payload es None, no un dict vacío.
        check(construir_briefing()["review"] is None,
              "sin revisión pendiente, review es None y no se construye")

        # --- "Ayer" cuenta películas, no minutos de un libro mayor muerto. ---------------
        #     `MovieViewingSession` tiene 0 filas y nada la escribe desde 2026-08-14, así que
        #     `minutos_cine` era un cero permanente que ver una película no podía mover.
        ayer = timezone.localdate() - timedelta(days=1)
        antes_pelis = construir_briefing()["ayer"]["peliculas"]
        MovieAnnualRecord.objects.create(title="Prueba", date_watched=ayer)
        check(construir_briefing()["ayer"]["peliculas"] == antes_pelis + 1,
              "una película vista ayer aparece en el briefing de hoy")

        transaction.set_rollback(True)

    print(f"\ntest_briefing: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
