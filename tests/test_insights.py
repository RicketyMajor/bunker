"""Check for the feedback strings. Runs inside the container:

    docker compose exec -T web python -m tests.test_insights

Everything happens inside a transaction with a forced rollback, so it touches no real data.

What is checked is not the wording, it is the rule: a feedback never invents. With
insufficient data it has to fall back to the plain confirmation, and it can never return
empty — a hole in the interface is worse than a dull sentence, because it reads as if the
capture never arrived.

Counts are asserted against years and months that hold no live rows (the year 2000, June
2001). Aggregating the current period would mean asserting against whatever the database
happens to hold, which is how a check ends up passing against a function that returns
nothing.
"""

import os
from datetime import date

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from bunker_core.insights import (  # noqa: E402
    _ETIQUETAS, REGLAS, conclusiones, feedback_paginas,
    feedback_terminado, regla_tendencia_monto,
)
from catalog.models import AnnualRecord, Author, Book, ReadingSession  # noqa: E402
from disquera.models import MusicAnnualRecord  # noqa: E402
from movies.models import MovieAnnualRecord  # noqa: E402

_checks = 0

# A year and a month with no live rows, so a count can be asserted exactly. They are also
# not the current period, which is what the "ese mes" / "ese año" wording is for.
ANNO_VACIO = date(2000, 6, 15)
MES_VACIO = date(2001, 6, 15)


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def run_tests():
    hoy = timezone.localdate()

    with transaction.atomic():
        autor, _ = Author.objects.get_or_create(name="Autor de prueba")
        libro = Book.objects.create(title="Libro de prueba", author=autor,
                                    isbn="0000000000001", page_count=300)
        ReadingSession.objects.create(date=hoy, pages_read=40, book=libro, current_page=40)

        # --- feedback_paginas ---
        texto = feedback_paginas(40, hoy, book=libro, current_page=40)
        check(isinstance(texto, str) and texto.strip(), "paginas devuelve texto no vacío")
        check("40" in texto, "paginas nombra las páginas leídas")
        check("este mes" in texto, "una captura de hoy habla de este mes")

        # Near the end the interesting fact is what is left, not the month's total.
        texto_final = feedback_paginas(10, hoy, book=libro, current_page=280)
        check("20" in texto_final, "a 20 páginas del final, el feedback lo dice")
        check("Libro de prueba" in texto_final, "nombra el libro cuando habla de él")

        # With no book there is nothing to invent: plain confirmation, never empty.
        texto_suelto = feedback_paginas(15, hoy)
        check(isinstance(texto_suelto, str) and texto_suelto.strip(),
              "paginas sin libro sigue devolviendo texto")
        check("página" in texto_suelto.lower(), "paginas sin libro confirma lo registrado")

        # A book with no page_count cannot claim how much is left, and must not try.
        sin_paginas = Book.objects.create(title="Sin longitud", author=autor,
                                          isbn="0000000000009")
        texto_sin = feedback_paginas(12, hoy, book=sin_paginas, current_page=12)
        check(isinstance(texto_sin, str) and texto_sin.strip(),
              "un libro sin page_count no rompe el feedback")
        check("quedan" not in texto_sin.lower(),
              "sin page_count no se inventa cuántas páginas faltan")

        # A backdated capture aggregates ITS month, so it must not call it "este mes".
        # The mobile queue backdates by up to 30 days, so this crosses a month boundary
        # once a month, and the number reported is real — about a period nobody asked about.
        ReadingSession.objects.create(date=MES_VACIO, pages_read=70)
        texto_viejo = feedback_paginas(70, MES_VACIO)
        check("70" in texto_viejo, "una captura atrasada suma su propio mes")
        check("ese mes" in texto_viejo,
              "un mes que no es el actual no se anuncia como 'este mes'")

        # --- feedback_terminado ---
        # The year 2000 holds nothing, so both branches can be asserted by count. The
        # singular/plural table is the trap audit 3.1 named: one wire name, three models.
        casos = [
            ('libros', AnnualRecord, {"title": "Primero", "date_finished": ANNO_VACIO},
             "primer libro", "libros"),
            ('peliculas', MovieAnnualRecord, {"title": "Primera", "date_watched": ANNO_VACIO},
             "primera película", "películas"),
            ('discos', MusicAnnualRecord, {"title": "Primero", "date_listened": ANNO_VACIO},
             "primer disco", "discos"),
        ]
        for modulo, modelo, campos, esperado_uno, plural in casos:
            modelo.objects.create(**campos)
            t = feedback_terminado(modulo, "Título de prueba", ANNO_VACIO)
            check(esperado_uno in t, f"terminado({modulo}) anuncia el primero en singular")
            check("ese año" in t, f"terminado({modulo}) no llama 'este año' a otro año")

            modelo.objects.create(**{**campos, "title": "Segundo"})
            t2 = feedback_terminado(modulo, "Título de prueba", ANNO_VACIO)
            check(f"Van 2 {plural}" in t2, f"terminado({modulo}) cuenta y pluraliza")

        t_hoy = feedback_terminado('libros', "De hoy", hoy)
        check("este año" in t_hoy, "un terminado de hoy sí habla de este año")

        # An unknown module confirms, it does not blow up: an endpoint calls this.
        t_raro = feedback_terminado("comics", "Algo", hoy)
        check(isinstance(t_raro, str) and "Algo" in t_raro,
              "un módulo desconocido cae en la confirmación simple")

        # Los bloques `_horas_min`, `feedback_habito` y `feedback_sesion` estaban aquí. Los
        # tres se fueron a `posada/feedback.py` el 2026-08-27; `_horas_min` era además dead
        # code en este repositorio en cuanto `feedback_sesion` dejó de llamarlo.

        # --- Conclusiones: las dos propiedades que definen la función. -------------------
        #     El resto es redacción. Cada regla se llama con etiquetas reales porque una
        #     regla que no puede nombrar su módulo no es la que corre en producción.
        etiquetas = _ETIQUETAS['books']
        un_punto = [{"period": "2026-08", "count": 1, "amount": 10}]
        for regla in REGLAS:
            check(regla([], etiquetas) is None,
                  f"{regla.__name__} con serie vacía devuelve None")
            check(regla(un_punto, etiquetas) is None,
                  f"{regla.__name__} con un solo punto devuelve None")

        # Dos puntos tampoco: el mínimo es tres periodos CON datos, no tres periodos.
        dos_puntos = [{"period": "2026-07", "count": 2, "amount": 20},
                      {"period": "2026-08", "count": 9, "amount": 90}]
        for regla in REGLAS:
            check(regla(dos_puntos, etiquetas) is None,
                  f"{regla.__name__} con dos puntos sigue callada")

        # Y con tres periodos con datos sí hablan: si nunca hablaran, las 12 aserciones de
        # arriba las cumpliría `return None`.
        tres = [{"period": "2026-06", "count": 1, "amount": 10},
                {"period": "2026-07", "count": 2, "amount": 20},
                {"period": "2026-08", "count": 9, "amount": 300}]
        hablan = [r.__name__ for r in REGLAS if r(tres, etiquetas)]
        check(len(hablan) >= 2, f"con tres periodos con datos alguna regla afirma algo: {hablan}")

        # `movies` no tiene monto desde 2026-08-14, y una regla de monto sobre él afirmaría
        # "0 páginas" de una película. Se calla.
        check(regla_tendencia_monto(tres, _ETIQUETAS['movies']) is None,
              "una regla de monto sobre un módulo sin monto se calla")

        # Singular: la base viva produjo "1 minutos de Deep Work" en la primera corrida, con
        # las etiquetas de posada. Ese módulo se fue el 2026-08-27 y `books` es el único que
        # queda con monto, así que la propiedad se comprueba con «1 página».
        uno = [{"period": "2026-06", "count": 1, "amount": 10},
               {"period": "2026-07", "count": 1, "amount": 10},
               {"period": "2026-08", "count": 1, "amount": 1}]
        frase = regla_tendencia_monto(uno, _ETIQUETAS['books'])
        check(frase and "1 página" in frase, f"una unidad va en singular: {frase!r}")

        # El periodo en curso está INCOMPLETO y aquellos contra los que se mide, no. Crudo,
        # "12 páginas contra una media de 300" el 2 de septiembre es cierto y sistemáticamente
        # engañoso: dispararía todos los meses, por construcción, durante el primer tercio.
        gastador = [{"period": "2026-06", "count": 1, "amount": 300},
                    {"period": "2026-07", "count": 1, "amount": 300},
                    {"period": "2026-09", "count": 1, "amount": 12}]
        libros = _ETIQUETAS['books']
        check(regla_tendencia_monto(gastador, libros, 2 / 30) is None,
              "el día 2 del mes la regla de tendencia se calla, no acusa")
        media_mes = regla_tendencia_monto(gastador, libros, 0.5)
        check(media_mes and "150" in media_mes,
              f"a mitad de mes compara contra la mitad de la media, no contra la media: {media_mes!r}")
        check(media_mes and "300" not in media_mes,
              f"y no nombra la media entera, que no es lo que tocaría hoy: {media_mes!r}")

        # Toda regla acepta `avance`, o `conclusiones()` no puede recorrerlas uniformemente.
        for regla in REGLAS:
            check(regla(un_punto, libros, 0.5) is None,
                  f"{regla.__name__} acepta avance y sigue callada sin datos")

        # El tope, y el reparto: tres frases del mismo módulo dejaban muda a la Posada.
        cs = conclusiones()
        check(len(cs) <= 3, f"el briefing nunca trae más de 3 conclusiones: {len(cs)}")
        check(all(isinstance(c, str) and c for c in cs), "ninguna conclusión es vacía o None")

        transaction.set_rollback(True)

    print(f"\ntest_insights: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
