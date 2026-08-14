"""Verificación de los textos de feedback. Corre dentro del contenedor:

    docker compose exec -T web python test_insights.py

Todo ocurre dentro de una transacción con rollback forzado, así que no toca datos reales.

Lo que se comprueba no es la redacción, es la regla: un feedback nunca inventa. Con datos
insuficientes tiene que caer en la confirmación simple, y nunca puede devolver vacío — un
hueco en la interfaz es peor que una frase sosa, porque parece que el registro no llegó.
"""

import os
from datetime import date

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402

from bunker_core.insights import (  # noqa: E402
    feedback_habito, feedback_minutos, feedback_paginas, feedback_sesion, feedback_terminado,
)
from catalog.models import Author, Book, ReadingSession  # noqa: E402
from posada.models import DailyHabit, DeepWorkSession  # noqa: E402

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def run_tests():
    hoy = date.today()

    with transaction.atomic():
        autor, _ = Author.objects.get_or_create(name="Autor de prueba")
        libro = Book.objects.create(title="Libro de prueba", author=autor,
                                    isbn="0000000000001", page_count=300)
        ReadingSession.objects.create(date=hoy, pages_read=40, book=libro, current_page=40)

        # --- feedback_paginas ---
        texto = feedback_paginas(40, hoy, book=libro, current_page=40)
        check(isinstance(texto, str) and texto.strip(), "paginas devuelve texto no vacío")
        check("40" in texto, "paginas nombra las páginas leídas")

        # Cerca del final el hecho interesante es lo que queda, no el acumulado del mes.
        texto_final = feedback_paginas(10, hoy, book=libro, current_page=280)
        check("20" in texto_final, "a 20 páginas del final, el feedback lo dice")
        check("Libro de prueba" in texto_final, "nombra el libro cuando habla de él")

        # Sin libro no hay nada que inventar: confirmación simple, pero nunca vacía.
        texto_suelto = feedback_paginas(15, hoy)
        check(isinstance(texto_suelto, str) and texto_suelto.strip(),
              "paginas sin libro sigue devolviendo texto")
        check("página" in texto_suelto.lower(), "paginas sin libro confirma lo registrado")

        # Un libro sin page_count no puede afirmar cuánto falta, y no debe intentarlo.
        sin_paginas = Book.objects.create(title="Sin longitud", author=autor,
                                          isbn="0000000000009")
        texto_sin = feedback_paginas(12, hoy, book=sin_paginas, current_page=12)
        check(isinstance(texto_sin, str) and texto_sin.strip(),
              "un libro sin page_count no rompe el feedback")
        check("quedan" not in texto_sin.lower(),
              "sin page_count no se inventa cuántas páginas faltan")

        # --- feedback_terminado ---
        for modulo in ("libros", "peliculas", "discos"):
            t = feedback_terminado(modulo, "Título de prueba", hoy)
            check(isinstance(t, str) and t.strip(), f"terminado({modulo}) devuelve texto")
            check("Título de prueba" in t, f"terminado({modulo}) nombra el título")

        # Un módulo desconocido confirma, no explota: esto lo llama un endpoint.
        t_raro = feedback_terminado("comics", "Algo", hoy)
        check(isinstance(t_raro, str) and "Algo" in t_raro,
              "un módulo desconocido cae en la confirmación simple")

        # --- feedback_minutos ---
        t = feedback_minutos(110, hoy)
        check(isinstance(t, str) and t.strip(), "minutos devuelve texto")
        check("110" in t, "minutos nombra los minutos registrados")

        # --- feedback_habito ---
        habito = DailyHabit.objects.create(name="Hábito de prueba", difficulty='C',
                                           current_streak=7, last_completed_date=hoy)
        t = feedback_habito(habito, es_recaida=False)
        check("7" in t, "hábito bueno nombra la racha")

        malo = DailyHabit.objects.create(name="Recaída de prueba", difficulty='S',
                                         is_bad_habit=True, current_streak=0)
        t_malo = feedback_habito(malo, es_recaida=True)
        check(isinstance(t_malo, str) and t_malo.strip(), "recaída devuelve texto")
        # La regla no es "no digas la palabra racha", es "no felicites": el texto de recaída
        # menciona la racha justamente para decir que se rompió.
        check("días seguidos" not in t_malo,
              "una recaída no felicita por una racha")

        # Racha de 1: un punto de dato no es una tendencia.
        nuevo = DailyHabit.objects.create(name="Primer día", difficulty='B', current_streak=1)
        t_nuevo = feedback_habito(nuevo, es_recaida=False)
        check(isinstance(t_nuevo, str) and t_nuevo.strip(), "racha de 1 devuelve texto")
        check("días seguidos" not in t_nuevo,
              "el primer día no se anuncia como una racha de días")

        # --- feedback_sesion ---
        sesion = DeepWorkSession.objects.create(duration_minutes=50, category="Programación",
                                                completed=True)
        t = feedback_sesion(sesion)
        check(isinstance(t, str) and t.strip(), "sesión devuelve texto")
        check("50" in t or "Programación" in t, "sesión nombra minutos o categoría")

        # Rendirse marca la sesión como `completed` igual (legacy.py:765) y nadie ajusta
        # `duration_minutes`, que es la duración OBJETIVO. Sin esto, abandonar a los 5
        # minutos de una sesión de 50 responde "50 min": el feedback inventando.
        t_rendida = feedback_sesion(sesion, minutos_reales=5)
        check("5 min de" in t_rendida, "una sesión abandonada reporta lo sobrevivido")
        check(not t_rendida.startswith("50"), "no reporta la duración objetivo como cumplida")

        transaction.set_rollback(True)

    print(f"\ntest_insights: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
