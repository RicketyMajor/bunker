"""Check for the feedback strings. Runs inside the container:

    docker compose exec -T web python test_insights.py

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
    _horas_min, feedback_habito, feedback_paginas, feedback_sesion, feedback_terminado,
)
from catalog.models import AnnualRecord, Author, Book, ReadingSession  # noqa: E402
from disquera.models import MusicAnnualRecord  # noqa: E402
from movies.models import MovieAnnualRecord  # noqa: E402
from posada.models import DailyHabit, DeepWorkSession  # noqa: E402

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

        # --- _horas_min ---
        # Checked directly rather than through a caller. Its whole-hour branch used to be
        # reached only by feedback_minutos, so deleting the minute ledger would have deleted
        # the only check on it — and that is the exact branch where the two formatters this
        # function replaced disagreed, one saying "2 h" and the other "2 h 0 min".
        # feedback_sesion is now its only caller and never exercises the boundary on purpose.
        check(_horas_min(0) == "0 min", f"0 → {_horas_min(0)!r}")
        check(_horas_min(45) == "45 min", f"45 → {_horas_min(45)!r}")
        check(_horas_min(120) == "2 h", f"120 → {_horas_min(120)!r}, se esperaba '2 h'")
        check(_horas_min(150) == "2 h 30 min", f"150 → {_horas_min(150)!r}")

        # --- feedback_habito ---
        habito = DailyHabit.objects.create(name="Hábito de prueba", difficulty='C',
                                           current_streak=7, last_completed_date=hoy)
        t = feedback_habito(habito, es_recaida=False)
        check("7" in t, "hábito bueno nombra la racha")

        malo = DailyHabit.objects.create(name="Recaída de prueba", difficulty='S',
                                         is_bad_habit=True, current_streak=0)
        t_malo = feedback_habito(malo, es_recaida=True)
        check(isinstance(t_malo, str) and t_malo.strip(), "recaída devuelve texto")
        # The rule is not "never say the word streak" — the relapse text mentions it exactly
        # to say that it broke. The rule is "do not congratulate".
        check("días seguidos" not in t_malo,
              "una recaída no felicita por una racha")

        # A streak of 1: one data point is not a trend.
        nuevo = DailyHabit.objects.create(name="Primer día", difficulty='B', current_streak=1)
        t_nuevo = feedback_habito(nuevo, es_recaida=False)
        check(isinstance(t_nuevo, str) and t_nuevo.strip(), "racha de 1 devuelve texto")
        check("días seguidos" not in t_nuevo,
              "el primer día no se anuncia como una racha de días")

        # --- feedback_sesion ---
        # A category of its own, so the monthly total is exactly what this check wrote.
        sesion = DeepWorkSession.objects.create(duration_minutes=50,
                                                category="Categoria de prueba", completed=True)
        t = feedback_sesion(sesion)
        check(isinstance(t, str) and t.strip(), "sesión devuelve texto")
        # `and`, not `or`: the category is in the string by construction, so an `or` here
        # short-circuits every failure and the check can never go red. That is what let the
        # target-vs-survived bug through.
        check("50 min" in t and "Categoria de prueba" in t,
              "sesión nombra los minutos Y la categoría")
        check("este mes" in t, "una sesión de hoy habla de este mes")

        # Surrendering marks the session `completed` all the same (legacy.py:765) and nobody
        # adjusts `duration_minutes`, which is the TARGET duration. Without this, abandoning
        # a 50-minute session after 5 answers "50 min": the feedback inventing.
        t_rendida = feedback_sesion(sesion, minutos_reales=5)
        check("5 min de" in t_rendida, "una sesión abandonada reporta lo sobrevivido")
        check(not t_rendida.startswith("50"), "no reporta la duración objetivo como cumplida")

        transaction.set_rollback(True)

    print(f"\ntest_insights: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
