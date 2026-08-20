"""Evaluación de logros: desbloquea lo que los contadores hayan ganado y paga una sola vez.

Toda la lógica está aquí y no en el BFF porque el BFF ya calcula los contadores por otras
razones; esto solo los interpreta. La regla que sostiene el sistema entero está en `_unlock`:
el UPDATE condicionado es lo que hace que evaluar dos veces no pague dos veces.
"""

import logging

from django.db import transaction
from django.utils import timezone

from .models import Achievement, GuildProfile

logger = logging.getLogger(__name__)


@transaction.atomic
def _unlock(logro):
    """Marca el logro y paga. Devuelve True si esta llamada fue la que lo desbloqueó.

    El filtro `unlocked_at__isnull=True` dentro del UPDATE es la garantía de idempotencia: si
    toca 0 filas es que ya estaba desbloqueado y no se paga nada. Comprobar y luego escribir en
    dos pasos dejaría una ventana para pagar dos veces.
    """
    ahora = timezone.now()
    tocadas = (Achievement.objects
               .filter(pk=logro.pk, unlocked_at__isnull=True)
               .update(unlocked_at=ahora))
    if not tocadas:
        return False

    guild, _ = GuildProfile.objects.get_or_create(id=1)
    if logro.reward_amount and hasattr(guild, logro.reward_coin):
        # ponytail: lectura-modificación-escritura en vez de F(). Es un único usuario y esto
        # corre dentro de la transacción; si algún día hay concurrencia real, F() + refresh.
        actual = getattr(guild, logro.reward_coin)
        setattr(guild, logro.reward_coin, actual + logro.reward_amount)
    # add_prestige() guarda la fila entera, así que persiste también la moneda de arriba.
    guild.add_prestige(logro.reward_prestige, 'logro',
                       detail=logro.name, ref_id=logro.id)

    logro.unlocked_at = ahora
    logger.info("Logro desbloqueado: %s (%s)", logro.key, logro.name)
    return True


def evaluate_achievements(counters):
    """Evalúa el catálogo contra los contadores y devuelve el payload del panel.

    `counters` es un dict {metric: valor}. Una métrica ausente (porque su módulo falló en el
    dashboard) deja el logro intacto: sin dato no se desbloquea ni se rompe nada.

    Una sola consulta al catálogo; solo escribe cuando algo se desbloquea de verdad.
    """
    payload = []
    for logro in Achievement.objects.all():
        progreso = counters.get(logro.metric)
        recien = False

        if logro.unlocked_at is None and progreso is not None and progreso >= logro.threshold:
            recien = _unlock(logro)

        payload.append({
            "key": logro.key,
            "name": logro.name,
            "icon": logro.icon,
            "module": logro.module,
            "threshold": logro.threshold,
            "progress": min(progreso, logro.threshold) if progreso is not None else None,
            "unlocked_at": logro.unlocked_at.isoformat() if logro.unlocked_at else None,
            "just_unlocked": recien,
        })
    return payload
