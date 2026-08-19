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

from bunker_core.briefing import construir_briefing, marcar_visto  # noqa: E402
from bunker_core.models import BunkerState  # noqa: E402
from catalog.models import Author, Book, ReadingSession  # noqa: E402
from posada.models import Achievement, DailyHabit, GuildProfile  # noqa: E402

_checks = 0

CLAVES = ("ayer", "hoy", "habito_en_riesgo", "libro_mas_cerca", "logros_nuevos",
          "conclusiones", "show_review", "review")


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def run_tests():
    hoy = timezone.localdate()

    with transaction.atomic():
        # 1. Todas las claves del contrato existen aunque no haya nada que contar.
        datos = construir_briefing()
        for clave in CLAVES:
            check(clave in datos, f"el briefing trae la clave '{clave}'")
        check(isinstance(datos["conclusiones"], list), "conclusiones es una lista")
        check(isinstance(datos["ayer"]["paginas"], int), "ayer.paginas es un entero, no None")

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

        # 4. El briefing NO paga prestigio. Esta es la que importa.
        guild, _ = GuildProfile.objects.get_or_create(id=1)
        prestigio_antes = guild.prestige
        construir_briefing()
        guild.refresh_from_db()
        check(guild.prestige == prestigio_antes,
              "construir el briefing no mueve el prestigio del gremio")

        # 5. Los logros nuevos se cuentan desde la última entrada, no desde siempre.
        #    Con `last_entry_at` en nulo la lista va vacía: en la primera entrada de la vida
        #    del modelo, "nuevos desde tu última entrada" no tiene desde cuándo contar, y
        #    anunciar el historial completo es exactamente el ruido que esto evita.
        estado, _ = BunkerState.objects.get_or_create(id=1)
        estado.last_entry_at = None
        estado.save()
        check(construir_briefing()["logros_nuevos"] == [],
              "sin última entrada registrada, no hay logros 'nuevos'")

        # El logro se crea aquí en vez de buscar uno vivo: hoy la base tiene ocho logros y
        # CERO desbloqueados, así que un `if antiguo is not None` habría saltado estas dos
        # comprobaciones en silencio y el check habría reportado verde sin medir nada.
        desbloqueo = timezone.now() - timedelta(hours=1)
        logro = Achievement.objects.create(
            key="prueba_briefing", name="Logro de prueba", description="Sólo para el check",
            metric="paginas_leidas", unlocked_at=desbloqueo)

        estado.last_entry_at = timezone.now()
        estado.save()
        check(construir_briefing()["logros_nuevos"] == [],
              "un logro desbloqueado antes de la última entrada no es nuevo")

        estado.last_entry_at = desbloqueo - timedelta(seconds=1)
        estado.save()
        claves = [l["key"] for l in construir_briefing()["logros_nuevos"]]
        check(logro.key in claves,
              "un logro desbloqueado después de la última entrada sí es nuevo")

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

        # 8. La regla `valid_days`, que ya tuvo un agujero una vez y hoy no tiene ni una
        #    fila viva que la ejerza: la base no guarda ningún hábito, así que sin estas
        #    filas la lista de pendientes sale vacía por falta de datos y no por la regla.
        otro_dia = str((hoy.weekday() + 1) % 7)
        hoy_toca = DailyHabit.objects.create(
            name="Hábito de hoy", valid_days=str(hoy.weekday()), current_streak=5)
        DailyHabit.objects.create(
            name="Hábito de otro día", valid_days=otro_dia, current_streak=9)
        hecho = DailyHabit.objects.create(
            name="Hábito ya hecho", valid_days=str(hoy.weekday()), current_streak=3,
            last_completed_date=hoy)

        datos = construir_briefing()
        nombres = [h["name"] for h in datos["hoy"]["habitos_pendientes"]]
        check("Hábito de hoy" in nombres, "un hábito programado hoy está pendiente")
        check("Hábito de otro día" not in nombres,
              "un hábito que hoy no toca no cuenta como pendiente")
        check("Hábito ya hecho" not in nombres,
              "un hábito ya marcado hoy no cuenta como pendiente")
        check(datos["habito_en_riesgo"]["name"] == "Hábito de hoy",
              "el hábito en riesgo es el de racha más larga entre los que hoy tocan")

        # Una racha de 0 no está en riesgo: no tiene nada que perder.
        hoy_toca.current_streak = 0
        hoy_toca.save()
        hecho.delete()
        check(construir_briefing()["habito_en_riesgo"] is None,
              "una racha de 0 no está 'en riesgo'")

        transaction.set_rollback(True)

    print(f"\ntest_briefing: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
