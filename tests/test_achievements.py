"""Verificación del sistema de logros. Corre dentro del contenedor:

    docker compose exec web python -m tests.test_achievements

Todo ocurre dentro de una transacción con rollback forzado, así que no toca datos reales:
ni el prestigio del gremio ni los logros ya desbloqueados quedan modificados al terminar.

La prueba que importa es la tercera: evaluar dos veces no puede pagar dos veces.
"""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402

from posada.achievements import evaluate_achievements  # noqa: E402
from posada.models import Achievement, GuildProfile  # noqa: E402


def run_tests():
    with transaction.atomic():
        guild, _ = GuildProfile.objects.get_or_create(id=1)
        logro = Achievement.objects.filter(unlocked_at__isnull=True).order_by('threshold').first()
        assert logro is not None, "No hay ningún logro bloqueado: corre load_achievements primero."

        prestigio_0 = guild.prestige
        nivel_0 = guild.prestige_level
        monedas_0 = getattr(guild, logro.reward_coin)
        print(f"Logro de prueba: {logro.key} ({logro.metric} >= {logro.threshold})")

        # 1. Por debajo del umbral no se desbloquea nada.
        payload = evaluate_achievements({logro.metric: logro.threshold - 1})
        fila = next(f for f in payload if f["key"] == logro.key)
        assert fila["unlocked_at"] is None, "Se desbloqueó por debajo del umbral."
        assert fila["progress"] == logro.threshold - 1, f"Progreso mal reportado: {fila}"
        logro.refresh_from_db()
        assert logro.unlocked_at is None
        print("OK 1/4: por debajo del umbral no desbloquea.")

        # 2. Alcanzar el umbral desbloquea y paga exactamente lo declarado.
        payload = evaluate_achievements({logro.metric: logro.threshold})
        fila = next(f for f in payload if f["key"] == logro.key)
        assert fila["just_unlocked"] is True, "No reportó el desbloqueo."
        assert fila["unlocked_at"] is not None
        logro.refresh_from_db()
        assert logro.unlocked_at is not None, "unlocked_at sigue vacío tras desbloquear."

        guild.refresh_from_db()
        monedas_1 = getattr(guild, logro.reward_coin)
        assert monedas_1 == monedas_0 + logro.reward_amount, (
            f"Pagó {monedas_1 - monedas_0} {logro.reward_coin}, esperaba {logro.reward_amount}.")
        # add_prestige puede subir de nivel y restar la meta, así que el total se compara en
        # bruto: prestigio ganado = lo acumulado + lo consumido por cada nivel que subió.
        ganado = guild.prestige - prestigio_0
        for nivel in range(nivel_0, guild.prestige_level):
            ganado += int(500 * (nivel ** 1.5))
        assert ganado == logro.reward_prestige, (
            f"Prestigio ganado {ganado}, esperaba {logro.reward_prestige}.")
        print(f"OK 2/4: desbloquea y paga {logro.reward_prestige} prestigio "
              f"+ {logro.reward_amount} {logro.reward_coin}.")

        # 3. LA PRUEBA QUE IMPORTA: evaluar de nuevo no vuelve a pagar.
        fecha_1 = logro.unlocked_at
        prestigio_1, nivel_1 = guild.prestige, guild.prestige_level
        payload = evaluate_achievements({logro.metric: logro.threshold * 10})
        fila = next(f for f in payload if f["key"] == logro.key)
        assert fila["just_unlocked"] is False, "Volvió a reportar el desbloqueo."
        logro.refresh_from_db()
        guild.refresh_from_db()
        assert logro.unlocked_at == fecha_1, "unlocked_at cambió en la segunda evaluación."
        assert getattr(guild, logro.reward_coin) == monedas_1, "Pagó monedas dos veces."
        assert (guild.prestige, guild.prestige_level) == (prestigio_1, nivel_1), (
            "Pagó prestigio dos veces.")
        print("OK 3/4: evaluar dos veces no paga dos veces.")

        # 4. Una métrica ausente no desbloquea ni revienta.
        otro = Achievement.objects.filter(unlocked_at__isnull=True).first()
        if otro:
            payload = evaluate_achievements({})
            fila = next(f for f in payload if f["key"] == otro.key)
            assert fila["unlocked_at"] is None and fila["progress"] is None, (
                f"Sin contador no debería haber progreso: {fila}")
            print("OK 4/4: sin contador no desbloquea (y no lanza).")
        else:
            print("SKIP 4/4: no quedan logros bloqueados para probar el caso sin contador.")

        transaction.set_rollback(True)

    print("\nTodo correcto. Nada de esto quedó escrito: la transacción se revirtió.")


if __name__ == '__main__':
    run_tests()
