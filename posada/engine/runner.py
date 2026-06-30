"""Runner — Loop principal de generate_session_script.

Orquesta la State Machine delegando cada tick al módulo de estado correspondiente.
"""
import random

from posada.models import Monster, Item
from posada.engine.context import SessionContext, ScriptList
from posada.engine.data.loot_tables import COIN_DROPS, ITEM_DROPS
from posada.engine.states.exploring import tick_exploring
from posada.engine.states.combat import tick_combat
from posada.engine.states.campfire import tick_campfire


def generate_session_script(session_id, duration_minutes, adventurers_qs):
    """Genera el guion determinista de una sesión de Deep Work.

    Usa el session_id como semilla para que la misma sesión siempre
    produzca exactamente el mismo resultado (reproducibilidad).

    Args:
        session_id: ID de la sesión (semilla del RNG).
        duration_minutes: Duración en minutos.
        adventurers_qs: QuerySet o lista de aventureros participantes.

    Returns:
        Lista de eventos (dicts) ordenados por segundo.
    """
    random.seed(session_id)

    # --- Inicialización del Contexto ---
    ctx = SessionContext()
    ctx.total_seconds = duration_minutes * 60
    ctx.adventurers = list(adventurers_qs)

    # ScriptList que auto-inyecta el estado actual
    ctx.script = ScriptList(lambda: ctx.state)

    if not ctx.adventurers:
        random.seed()
        return ctx.script

    # --- Inicialización dinámica de recursos de clase ---
    for adv in ctx.adventurers:
        res = {}
        if adv.adv_class in ['WIZ', 'SOR', 'WLK', 'CLR', 'DRD', 'BRD']:
            res['mana'] = adv.level * 3
        elif adv.adv_class == 'PAL':
            res['mana'] = adv.level * 2
            res['sanacion'] = adv.level * 5
        elif adv.adv_class == 'MNK':
            res['ki'] = adv.level * 2
        elif adv.adv_class == 'BBN':
            res['furia'] = 2 + (adv.level // 3)
        else:  # FTR, ROG, RGR, ART
            res['stamina'] = adv.level * 2
        adv.class_resources = res

    # --- Carga de datos ---
    ctx.monsters_db = list(Monster.objects.all())
    ctx.all_items_db = list(Item.objects.all())

    # --- Trackers ---
    ctx.session_skills_tracker = {adv.id: set() for adv in ctx.adventurers}
    ctx.combat_skills_tracker = {adv.id: set() for adv in ctx.adventurers}
    ctx.adv_status_tracker = {adv.id: set() for adv in ctx.adventurers}
    ctx.temp_hp = {adv.id: adv.current_hp for adv in ctx.adventurers}

    # --- Tablas de Botín ---
    ctx.coin_drops = COIN_DROPS
    ctx.item_drops = ITEM_DROPS

    # --- STATE MACHINE LOOP ---
    while ctx.current_second < ctx.total_seconds:
        if ctx.state == "EXPLORING":
            tick_exploring(ctx)
        elif ctx.state == "COMBAT":
            tick_combat(ctx)
        elif ctx.state == "CAMPFIRE":
            tick_campfire(ctx)

    ctx.script.sort(key=lambda x: x["second"])
    random.seed()
    return ctx.script
