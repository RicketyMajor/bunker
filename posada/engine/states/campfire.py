"""Estado CAMPFIRE — Un tick de descanso cada 30 segundos.

El grupo descansa y los aventureros recuperan HP gradualmente.
Una vez todos están al máximo, se transiciona de vuelta a EXPLORING.
"""
import random


def tick_campfire(ctx):
    """Ejecuta un tick de 30 segundos en estado CAMPFIRE."""
    ctx.current_second += 30
    if ctx.current_second >= ctx.total_seconds:
        return

    all_healed = True
    for adv in ctx.adventurers:
        if ctx.temp_hp[adv.id] < adv.max_hp:
            all_healed = False
            heal = random.randint(adv.level, (adv.level * 3) + adv.base_con)
            ctx.temp_hp[adv.id] = min(adv.max_hp, ctx.temp_hp[adv.id] + heal)
            ctx.script.append({"second": ctx.current_second, "type": "heal", "adventurer_id": adv.id, "amount": heal, "message": f"🔥 {adv.name} descansa y recupera [bold green]{heal} HP[/]."})

    if all_healed:
        ctx.script.append({"second": ctx.current_second, "type": "flavor", "message": "🔥 El grupo se ha recuperado por completo. ¡La aventura continúa!"})
        ctx.state = "EXPLORING"
