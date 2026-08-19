"""Check for the historical series. Runs inside the container:

    docker compose exec -T web python -m tests.test_timeline

Everything happens inside a transaction with a forced rollback, so it touches no real data.

Every test builds its own rows. Read against the live database most of these series come out
in zeros — `MovieViewingSession` and `SolvedPuzzle` are empty, `ListeningEntry` has one row —
so a check that read what is already there would pass just as happily against a function that
returns `[]`.

**The gap test runs on `chess` on purpose.** It is the only module whose sources are entirely
empty (`SolvedPuzzle`: 0 rows, verified 2026-08-19), so the middle period can be asserted to be
*exactly* zero. On `books` the same assertion would be answered by live reading sessions —
there are rows in July 2026 — and "at least one period came out empty" is a claim a six-month
window satisfies whether or not the gap filling works at all.
"""

import os
from datetime import datetime, timedelta, timezone as dt_timezone

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.utils import timezone  # noqa: E402

from bunker_core.timeline import WINDOW_MAX, serie  # noqa: E402
from catalog.models import Author, Book, ReadingSession  # noqa: E402
from chess_study.models import SolvedPuzzle  # noqa: E402
from posada.models import DeepWorkSession  # noqa: E402

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _puzzle_en(dia, tz, n=1):
    """SolvedPuzzle.solved_at es auto_now_add: create() lo pisa, hay que update() después."""
    for i in range(n):
        p = SolvedPuzzle.objects.create(puzzle_id=f"prueba-{dia}-{i}", rating=1500)
        SolvedPuzzle.objects.filter(pk=p.pk).update(
            solved_at=timezone.make_aware(datetime.combine(dia, datetime.min.time()) +
                                          timedelta(hours=12), tz))


def run_tests():
    # `localdate()`, no `date.today()`: el contenedor corre en UTC y el proyecto es
    # America/Santiago, así que después de las 20:00 `date.today()` ya es mañana.
    hoy = timezone.localdate()
    tz = timezone.get_current_timezone()

    with transaction.atomic():
        # --- 1. Forma de la serie. ---
        autor, _ = Author.objects.get_or_create(name="Autor de prueba")
        libro = Book.objects.create(title="Libro de prueba", author=autor,
                                    isbn="0000000000004", page_count=300)
        ReadingSession.objects.create(date=hoy, pages_read=100, book=libro)

        s = serie('books', 'monthly', 6)
        check(len(s) == 6, "una ventana de 6 devuelve exactamente 6 periodos")
        check([p['period'] for p in s] == sorted(p['period'] for p in s),
              "la serie viene ordenada de más antigua a más reciente")
        claves = [p['period'] for p in s]
        check(len(claves) == len(set(claves)), "no hay periodos repetidos")
        check(s[-1]['period'] == hoy.strftime('%Y-%m'),
              "el último periodo es el mes en curso")
        check(all(isinstance(p['count'], int) and isinstance(p['amount'], int) for p in s),
              "count y amount son enteros en todos los periodos, nunca None")

        # --- 2. El agujero. Es lo que se rompe, no la agregación. ---
        #     chess parte de cero filas, así que el mes de en medio se puede exigir EXACTO.
        primero = hoy.replace(day=1)
        mes_1 = (primero - timedelta(days=1)).replace(day=1)          # mes pasado
        mes_2 = (mes_1 - timedelta(days=1)).replace(day=1)            # hace dos meses
        _puzzle_en(hoy, tz, 2)
        _puzzle_en(mes_2, tz, 3)

        s = {p['period']: p for p in serie('chess', 'monthly', 6)}
        check(s[hoy.strftime('%Y-%m')]['count'] == 2, "el mes en curso cuenta sus dos puzzles")
        check(s[mes_2.strftime('%Y-%m')]['count'] == 3, "hace dos meses cuenta sus tres")
        hueco = s.get(mes_1.strftime('%Y-%m'))
        check(hueco is not None, "el mes sin actividad NO se omite de la serie")
        check(hueco['count'] == 0 and hueco['amount'] == 0,
              "el mes sin actividad vuelve en ceros explícitos")
        check(s[hoy.strftime('%Y-%m')]['amount'] == 0,
              "chess no tiene 'amount': es 0, no None")

        # --- 3. Zona horaria. Solo muerde en los dos modelos DateTimeField. ---
        #     La sesión se pone el ÚLTIMO día del mes pasado a las 23:30 locales, que en UTC
        #     ya es el día 1 del mes en curso. Truncar en UTC la archivaría en este mes;
        #     truncar en America/Santiago la deja en el pasado, que es donde ocurrió. Puesta
        #     un día cualquiera —como decía el plan— la aserción es cierta con o sin zona
        #     horaria, y pasaría 29 de cada 30 días sin medir nada.
        #     Probarlo contra ReadingSession.date tampoco probaría nada: ese campo es un
        #     DateField ya escrito con localdate().
        fin_mes_pasado = primero - timedelta(days=1)
        tarde = timezone.make_aware(datetime.combine(fin_mes_pasado, datetime.min.time()) +
                                    timedelta(hours=23, minutes=30), tz)
        check(tarde.astimezone(dt_timezone.utc).month != tarde.month,
              f"el caso de prueba cruza el mes en UTC: local {tarde:%Y-%m-%d %H:%M} → "
              f"UTC {tarde.astimezone(dt_timezone.utc):%Y-%m-%d %H:%M}")
        antes = {p['period']: p['amount'] for p in serie('posada', 'monthly', 3)}
        DeepWorkSession.objects.create(start_time=tarde, duration_minutes=45,
                                       category="Prueba", completed=True)
        despues = {p['period']: p['amount'] for p in serie('posada', 'monthly', 3)}
        mes, pasado = hoy.strftime('%Y-%m'), mes_1.strftime('%Y-%m')
        check(despues[pasado] - antes[pasado] == 45,
              "una sesión a las 23:30 del último día del mes suma en ESE mes")
        check(despues[mes] - antes[mes] == 0,
              "y no se cuela en el mes siguiente, que es donde la pondría UTC")

        # --- 4. Entradas inválidas: ValueError, no 500 y no una serie vacía. ---
        for modulo_malo in ("nope", "", "BOOKS"):
            try:
                serie(modulo_malo, 'monthly', 12)
                check(False, f"serie('{modulo_malo}') tenía que lanzar ValueError")
            except ValueError as exc:
                check("books" in str(exc), f"el error de '{modulo_malo}' nombra los módulos válidos")
        try:
            serie('books', 'diario', 12)
            check(False, "un periodo desconocido tenía que lanzar ValueError")
        except ValueError as exc:
            check("monthly" in str(exc), "el error de periodo nombra los valores válidos")

        # --- 5. La ventana se recorta, no se obedece. ---
        check(len(serie('books', 'monthly', 99999)) == WINDOW_MAX,
              "una ventana absurda se recorta al máximo")
        check(len(serie('books', 'monthly', 0)) == 1, "una ventana de 0 devuelve un periodo")
        check(len(serie('books', 'monthly', 'ocho')) == 12,
              "una ventana que no es número cae al valor por defecto")

        # --- 6. Semanal: la clave es ISO y la ventana también se respeta. ---
        sem = serie('chess', 'weekly', 4)
        check(len(sem) == 4, "una ventana semanal de 4 devuelve 4 semanas")
        check(all(len(p['period']) == 8 and '-W' in p['period'] for p in sem),
              f"la clave semanal es ISO 'AAAA-Wnn': {[p['period'] for p in sem]}")
        check(sem[-1]['count'] == 2, "los puzzles de hoy caen en la semana en curso")

        # --- 7. Presupuesto de consultas. books son DOS modelos, no uno. ---
        with CaptureQueriesContext(connection) as ctx:
            serie('books', 'monthly', 12)
        check(len(ctx) == 2,
              f"books = 2 consultas agrupadas (registros + páginas), no {len(ctx)}")
        with CaptureQueriesContext(connection) as ctx:
            serie('chess', 'monthly', 12)
        check(len(ctx) == 1, f"chess = 1 consulta agrupada, no {len(ctx)}")
        with CaptureQueriesContext(connection) as ctx:
            serie('posada', 'monthly', 60)
        check(len(ctx) == 1,
              f"una ventana de 60 sigue siendo 1 consulta, no una por periodo: {len(ctx)}")

        transaction.set_rollback(True)

    print(f"\ntest_timeline: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
