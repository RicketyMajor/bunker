"""Check for the historical series. Runs inside the container:

    docker compose exec -T web python -m tests.test_timeline

Everything happens inside a transaction with a forced rollback, so it touches no real data.

Every test builds its own rows. Read against the live database most of these series come out
in zeros — `MovieViewingSession` and `SolvedPuzzle` are empty, `ListeningEntry` has one row —
so a check that read what is already there would pass just as happily against a function that
returns `[]`.

**The gap test EMPTIES its module first.** It used to run on `chess`, whose table happened to
hold 0 rows — but "empty by accident" is not "empty by construction", and both zero-row modules
left in the 2026-08-27 split. It now deletes every `MusicAnnualRecord` inside the rollback, so
the middle period is exactly zero because this file made it so. On `books` the same assertion
would be answered by live reading sessions, and "at least one period came out empty" is a claim
a six-month window satisfies whether or not the gap filling works at all.

**Two checks left with the split and were NOT reproduced**, because no surviving module has the
shape they needed. Both are recorded in `context/general/state-of-the-project.md`:

  · The TIMEZONE check drove `DeepWorkSession.start_time`, and all four remaining sources
    (`AnnualRecord.date_finished`, `ReadingSession.date`, `MovieAnnualRecord.date_watched`,
    `MusicAnnualRecord.date_listened`) are **DateField**, which `TruncMonth` does not convert.
    Faking it on a DateField would assert nothing.
  · The COUNT-vs-AMOUNT check needed a module whose SINGLE source is both the counting source
    and the amount source — the shape that made posada report `count: 0` on 35 real sessions.
    `books` has two sources and the other two are count-only, so nothing here can reach it.
"""

import os
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.utils import timezone  # noqa: E402

from bunker_core.timeline import WINDOW_MAX, serie  # noqa: E402
from books.models import Author, Book, ReadingSession  # noqa: E402
from music.models import ListeningEntry, MusicAnnualRecord  # noqa: E402
from movies.models import MovieViewingSession  # noqa: E402

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _disco_en(dia, n=1):
    """`n` albums filed on `dia`. `MusicAnnualRecord` is count-only, which is what makes it the
    right subject for the gap test: its `amount` must be 0 in every period, gap or not."""
    for i in range(n):
        MusicAnnualRecord.objects.create(title=f"Disco {dia} {i}", date_listened=dia)


def run_tests():
    # `localdate()`, no `date.today()`: el contenedor corre en UTC y el proyecto es
    # America/Santiago, así que después de las 20:00 `date.today()` ya es mañana.
    hoy = timezone.localdate()

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
        #     Se VACÍA la tabla primero, dentro del rollback: el mes de en medio es cero
        #     porque este check lo hizo cero, no porque la tabla estuviera vacía de casualidad.
        #     Los dos módulos que sí estaban vacíos se fueron el 2026-08-27.
        MusicAnnualRecord.objects.all().delete()
        primero = hoy.replace(day=1)
        mes_1 = (primero - timedelta(days=1)).replace(day=1)          # mes pasado
        mes_2 = (mes_1 - timedelta(days=1)).replace(day=1)            # hace dos meses
        _disco_en(hoy, 2)
        _disco_en(mes_2, 3)

        s = {p['period']: p for p in serie('music', 'monthly', 6)}
        mes = hoy.strftime('%Y-%m')
        check(s[mes]['count'] == 2, "el mes en curso cuenta sus dos discos")
        check(s[mes_2.strftime('%Y-%m')]['count'] == 3, "hace dos meses cuenta sus tres")
        hueco = s.get(mes_1.strftime('%Y-%m'))
        check(hueco is not None, "el mes sin actividad NO se omite de la serie")
        check(hueco['count'] == 0 and hueco['amount'] == 0,
              "el mes sin actividad vuelve en ceros explícitos")
        check(s[mes]['amount'] == 0, "music no tiene 'amount': es 0, no None")

        # --- 3. Movies y music son count-only por spec (corrección 2026-08-14): sus libros
        #     mayores de minutos se vaciaron y no deben leerse. Una fila en cada uno tiene
        #     que ser invisible — antes reaparecía como `amount: 45` en la serie de música.
        ListeningEntry.objects.create(date=hoy, minutes_listened=45)
        MovieViewingSession.objects.create(date=hoy, minutes_watched=120)
        for modulo in ('music', 'movies'):
            check(all(p['amount'] == 0 for p in serie(modulo, 'monthly', 3)),
                  f"{modulo} es count-only: su libro mayor de minutos no se lee")

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
        sem = serie('music', 'weekly', 4)
        check(len(sem) == 4, "una ventana semanal de 4 devuelve 4 semanas")
        check(all(len(p['period']) == 8 and '-W' in p['period'] for p in sem),
              f"la clave semanal es ISO 'AAAA-Wnn': {[p['period'] for p in sem]}")
        check(sem[-1]['count'] == 2, "los dos discos de hoy caen en la semana en curso")

        # --- 7. Presupuesto de consultas. books son DOS modelos, no uno. ---
        with CaptureQueriesContext(connection) as ctx:
            serie('books', 'monthly', 12)
        check(len(ctx) == 2,
              f"books = 2 consultas agrupadas (registros + páginas), no {len(ctx)}")
        for modulo in ('movies', 'music'):
            with CaptureQueriesContext(connection) as ctx:
                serie(modulo, 'monthly', 12)
            check(len(ctx) == 1,
                  f"{modulo} = 1 consulta agrupada desde que no lee su libro mayor, no {len(ctx)}")
        with CaptureQueriesContext(connection) as ctx:
            serie('music', 'monthly', 60)
        check(len(ctx) == 1,
              f"una ventana de 60 sigue siendo 1 consulta, no una por periodo: {len(ctx)}")

        transaction.set_rollback(True)

    print(f"\ntest_timeline: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
