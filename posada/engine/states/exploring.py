"""Estado EXPLORING — Un tick de exploración cada 30 segundos.

Incluye:
- Micro-eventos narrativos (skill checks)
- Eventos de consumibles (flavor)
- Tirada de encuentro (transición a COMBAT)
- Loot de exploración
- Evaluación de habilidades de sesión
"""
import random
import logging

from posada.models import InventorySlot, ItemRarity
from posada.engine.data.flavor_tables import EVENT_TEXTS, FLAVOR_DATABASE
from posada.engine.data.loot_tables import COIN_POOL


def tick_exploring(ctx):
    """Ejecuta un tick de 30 segundos en estado EXPLORING."""
    from posada.engine.legacy import (
        get_derived_skills, roll_d20, safe_randint, is_class_allowed,
        COIN_COLORS, MONSTER_COLORS
    )
    from posada.skills import SkillRegistry

    ctx.current_second += 30
    if ctx.current_second >= ctx.total_seconds:
        return

    adventurers = ctx.adventurers
    flavor_adv = random.choice(adventurers)

    # --- MICRO-EVENTOS NARRATIVOS DE EXPLORACIÓN ---
    _narrative_skill_check(ctx, adventurers)

    # --- EVENTOS DE CONSUMIBLES (INMERSIÓN FLAVOR EXTENDIDA) ---
    _consumable_flavor_event(ctx, flavor_adv)

    # --- EVENTOS DE DESCUBRIMIENTO NO-COMBATE ---
    if _discovery_event(ctx, adventurers):
        return  # Si hubo un descubrimiento, consumimos el resto del tick

    # --- Tirada de Encuentro ---
    if ctx.monsters_db and random.random() < 0.08:
        _spawn_encounter(ctx)
        return  # Transición a COMBAT, no seguir explorando

    # --- Exploración (Botín) ---
    _exploration_loot(ctx, adventurers)

    # --- EVALUACIÓN DE HABILIDADES DE SESIÓN (EXPLORACIÓN) ---
    _session_skill_eval(ctx, adventurers)


def _narrative_skill_check(ctx, adventurers):
    """25% de chance de un evento narrativo con skill check."""
    from posada.engine.legacy import get_derived_skills, roll_d20

    if random.random() >= 0.25:
        return

    event_adv = random.choice(adventurers)
    skills = get_derived_skills(event_adv)

    skill_name = random.choice(list(EVENT_TEXTS.keys()))
    action, succ_msg, fail_msg = random.choice(EVENT_TEXTS[skill_name])

    skill_bonus = skills[skill_name]
    dc = random.randint(10, 18)
    roll = roll_d20()["value"]
    total = roll + skill_bonus

    ctx.script.append({"second": ctx.current_second - 45, "type": "flavor",
                        "message": f"🎲 {event_adv.name} intenta {action} (Chequeo de {skill_name}, CD {dc})."})
    if total >= dc:
        ctx.script.append({"second": ctx.current_second - 42, "type": "flavor",
                            "message": f"   -> ¡ÉXITO! ({roll} + {skill_bonus} = {total}). {event_adv.name} {succ_msg}."})
    else:
        ctx.script.append({"second": ctx.current_second - 42, "type": "flavor",
                            "message": f"   -> FALLO ({roll} + {skill_bonus} = {total}). {event_adv.name} {fail_msg}."})


def _consumable_flavor_event(ctx, flavor_adv):
    """15% de chance de usar un consumible con texto inmersivo."""
    if random.random() >= 0.15:
        return

    flavor_slots = list(InventorySlot.objects.filter(
        adventurer=flavor_adv, item__consumable_type__in=['FLV', 'HEL', 'MAN'], quantity__gt=0))
    if not flavor_slots:
        return

    slot = random.choice(flavor_slots)
    slot.quantity -= 1
    if slot.quantity <= 0:
        slot.delete()
    else:
        slot.save()

    item_type = slot.item.consumable_type
    amt_healed = slot.item.consumable_amount
    if item_type == 'HEL':
        ctx.temp_hp[flavor_adv.id] = min(flavor_adv.max_hp, ctx.temp_hp[flavor_adv.id] + amt_healed)
    elif item_type == 'MAN' and hasattr(flavor_adv, 'class_resources'):
        for k in flavor_adv.class_resources:
            flavor_adv.class_resources[k] += amt_healed

    item_name = slot.item.name.lower()
    styled_name = f"[bold cyan]{slot.item.name}[/bold cyan]"

    # Búsqueda por palabra clave en la base de flavor
    message_chosen = None
    for key, lines in FLAVOR_DATABASE.items():
        if key in item_name:
            template = random.choice(lines)
            message_chosen = f"{flavor_adv.name} {template.format(item=styled_name)}"
            break

    # Fallback genérico
    if not message_chosen:
        if item_type == 'HEL':
            message_chosen = f"¡{flavor_adv.name} bebe su {styled_name} y recupera {amt_healed} HP!"
        elif item_type == 'MAN':
            message_chosen = f"¡{flavor_adv.name} consume {styled_name} y siente cómo su poder interno se restaura!"
        else:
            message_chosen = f"Durante la marcha, {flavor_adv.name} decide utilizar su {styled_name} de forma ingeniosa."

    ctx.script.append({"second": ctx.current_second - 15,
                        "type": "flavor", "message": message_chosen})


def _spawn_encounter(ctx):
    """Genera un grupo de monstruos y transiciona a COMBAT."""
    from posada.engine.legacy import safe_randint, MONSTER_COLORS

    avg_level = sum(a.level for a in ctx.adventurers) / len(ctx.adventurers) if ctx.adventurers else 1
    
    if avg_level <= 3:
        category_weights = {'SML': 80, 'MED': 20, 'LRG': 0, 'EPC': 0}
    elif avg_level <= 6:
        category_weights = {'SML': 60, 'MED': 30, 'LRG': 10, 'EPC': 0}
    elif avg_level <= 9:
        category_weights = {'SML': 10, 'MED': 60, 'LRG': 30, 'EPC': 0}
    else:
        category_weights = {'SML': 20, 'MED': 40, 'LRG': 30, 'EPC': 10}

    weights = [category_weights.get(m.category, 0) for m in ctx.monsters_db]
    if sum(weights) == 0:
        weights = [1] * len(ctx.monsters_db)
    base_monster = random.choices(ctx.monsters_db, weights=weights, k=1)[0]

    spawn_count = random.randint(base_monster.min_spawn, base_monster.max_spawn)

    for i in range(spawn_count):
        m_stats = {
            'str': safe_randint(base_monster.min_str, base_monster.max_str),
            'dex': safe_randint(base_monster.min_dex, base_monster.max_dex),
            'con': safe_randint(base_monster.min_con, base_monster.max_con),
            'int': safe_randint(base_monster.min_int, base_monster.max_int),
            'wis': safe_randint(base_monster.min_wis, base_monster.max_wis),
            'cha': safe_randint(base_monster.min_cha, base_monster.max_cha),
            'armor': safe_randint(base_monster.min_armor, base_monster.max_armor),
            'luk': 0
        }
        base_hp_roll = safe_randint(base_monster.min_hp, base_monster.max_hp)
        hp = base_hp_roll + (m_stats['con'] * 2)
        name = f"{base_monster.name} {'ABCDEF'[i]}" if spawn_count > 1 else base_monster.name

        ctx.active_monsters_group.append({
            'name': name, 'hp': hp, 'max_hp': hp, 'stats': m_stats, 'base': base_monster,
            'status': set()
        })

    m_color = MONSTER_COLORS.get(base_monster.category, 'red')
    msg = f"¡EMBOSCADA! Un grupo de {spawn_count} [[{m_color}]{base_monster.name}s[/]] corta el paso." if spawn_count > 1 else f"¡PELIGRO! Un [[{m_color}]{base_monster.name}[/]] bloquea el camino."
    ctx.script.append({"second": ctx.current_second, "type": "flavor", "message": msg})
    ctx.state = "COMBAT"


def _exploration_loot(ctx, adventurers):
    """Cada aventurero vivo busca botín por su cuenta."""
    from posada.engine.legacy import COIN_COLORS, is_class_allowed

    for explore_adv in adventurers:
        if ctx.temp_hp[explore_adv.id] <= 0:
            continue
        adv_luk = explore_adv.base_luk + sum(item.bonus_luk for item in explore_adv.get_equipped_items())

        # Roll for coins
        found_coin = None
        roll = random.random()
        for coin_name, prob in COIN_POOL:
            if roll < (prob + (adv_luk * 0.002)):
                found_coin = coin_name
                break

        if found_coin:
            if found_coin in ['iron_half_penny', 'iron_penny', 'copper_penny']:
                amt = random.randint(2, 5) + adv_luk
            elif found_coin in ['ardite', 'silver_penny', 'drabin']:
                amt = random.randint(1, 3) + (adv_luk // 2)
            else:
                amt = 1

            color = COIN_COLORS.get(found_coin, 'white')
            display_name = found_coin.replace('_', ' ').title()
            if found_coin == 'iron_half_penny':
                display_name = "Medio Penique de Hierro"

            ctx.script.append({"second": ctx.current_second - 10, "type": "loot", "coin": found_coin,
                                "amount": amt, "message": f"{explore_adv.name} encontró {amt} [[{color}]{display_name}[/]]."})

        # Drops aleatorios
        if ctx.all_items_db and random.random() < (0.025 + (adv_luk * 0.01)):
            roll = random.random()
            rarity = 'COM'
            if roll < 0.05:
                rarity = 'RAR'
            elif roll < 0.25:
                rarity = 'UNC'

            pool = [i for i in ctx.all_items_db if i.rarity == rarity]
            if not pool:
                pool = ctx.all_items_db
            drop_item = random.choice(pool)
            ctx.script.append({"second": ctx.current_second - 5, "type": "item_loot", "item_id": drop_item.id, "adventurer_id": explore_adv.id,
                                "message": f"🎁 {explore_adv.name} encontró algo brillando: [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]"})


def _session_skill_eval(ctx, adventurers):
    """Evalúa y ejecuta habilidades de tipo SESSION en exploración."""
    from posada.skills import SkillRegistry

    for skill_adv in adventurers:
        if ctx.temp_hp[skill_adv.id] <= 0:
            continue
        available_session_skills = []
        for skill_id, skill_data in SkillRegistry.get_all_skills().items():
            if skill_data["type"] == "SESSION" and skill_adv.adv_class in skill_data["allowed_classes"] and skill_adv.level >= skill_data["req_level"]:
                if skill_id not in ctx.session_skills_tracker[skill_adv.id]:
                    available_session_skills.append(skill_data)

        if available_session_skills:
            context = {
                'caster': skill_adv,
                'allies': adventurers,
                'enemies': [],
                'adv_status': ctx.adv_status_tracker,
                'current_second': ctx.current_second - 2,
                'log': ctx.script,
                'eval_mode': True,
                'session_duration': ctx.total_seconds
            }
            best_action = None
            best_score = 50
            for skill in available_session_skills:
                try:
                    score = skill["execute"](context)
                    if isinstance(score, bool):
                        score = 0
                    if score > best_score:
                        best_score = score
                        best_action = skill
                except Exception as e:
                    logging.warning(f"Skill eval error: {e}")

            if best_action:
                context['eval_mode'] = False
                try:
                    success = best_action["execute"](context)
                    if success:
                        ctx.session_skills_tracker[skill_adv.id].add(best_action["id"])
                except Exception as e:
                    logging.warning(f"Skill exec error: {e}")


def _discovery_event(ctx, adventurers):
    """8% de chance de un evento de descubrimiento interactivo especial."""
    if random.random() >= 0.08:
        return False

    # Filtra muertos
    living = [a for a in adventurers if ctx.temp_hp[a.id] > 0]
    if not living:
        return False

    events = [
        _event_magic_spring,
        _event_trapped_chest,
        _event_ancient_inscription,
        _event_wandering_merchant
    ]
    random.choice(events)(ctx, living)
    return True


def _event_magic_spring(ctx, adventurers):
    """Cura entre 20% y 40% del HP a todo el grupo vivo."""
    import random
    ctx.script.append({"second": ctx.current_second - 20, "type": "flavor", 
                        "message": "✨ El grupo descubre un claro oculto con una [bold cyan]Fuente Mágica Silvestre[/bold cyan]. Sus aguas cristalinas emiten un brillo relajante."})
    
    for adv in adventurers:
        heal_pct = random.uniform(0.20, 0.40)
        heal_amt = max(1, int(adv.max_hp * heal_pct))
        # Ensure we do not heal past max_hp
        actual_heal = min(heal_amt, adv.max_hp - ctx.temp_hp[adv.id])
        if actual_heal > 0:
            ctx.temp_hp[adv.id] += actual_heal
            ctx.script.append({"second": ctx.current_second - 18, "type": "heal", "adventurer_id": adv.id, "amount": actual_heal,
                                "message": f"{adv.name} bebe de la fuente y recupera {actual_heal} HP."})


def _event_trapped_chest(ctx, adventurers):
    """El aventurero con mayor DEX intenta abrir un cofre trampa."""
    from posada.engine.legacy import roll_d20
    from posada.models import ItemRarity
    import random

    best_adv = max(adventurers, key=lambda a: a.get_stat_modifiers()['dex'])
    mods = best_adv.get_stat_modifiers()
    
    ctx.script.append({"second": ctx.current_second - 20, "type": "flavor", 
                        "message": f"🧰 El grupo encuentra un [bold yellow]Cofre Misterioso[/bold yellow] medio enterrado. {best_adv.name} se adelanta para inspeccionarlo."})
    
    dc = random.randint(12, 16)
    roll = roll_d20()["value"]
    total = roll + mods['dex']
    
    if total >= dc:
        # Éxito: Drop raro
        ctx.script.append({"second": ctx.current_second - 15, "type": "flavor", 
                            "message": f"   -> ¡ÉXITO! ({roll} + {mods['dex']} = {total}). {best_adv.name} desactiva la trampa de gas y abre la cerradura."})
        if ctx.all_items_db:
            rarity = 'RAR' if random.random() < 0.2 else 'UNC'
            pool = [i for i in ctx.all_items_db if i.rarity == rarity]
            if not pool:
                pool = ctx.all_items_db
            drop_item = random.choice(pool)
            ctx.script.append({"second": ctx.current_second - 10, "type": "item_loot", "item_id": drop_item.id, "adventurer_id": best_adv.id,
                                "message": f"🎁 ¡El cofre contenía [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]!"})
    else:
        # Fallo: Daño por veneno o fuego
        dmg = random.randint(3, 8)
        ctx.script.append({"second": ctx.current_second - 15, "type": "flavor", 
                            "message": f"   -> FALLO ({roll} + {mods['dex']} = {total}). *¡CLICK!* Una aguja envenenada salta del cerrojo."})
        ctx.temp_hp[best_adv.id] -= dmg
        ctx.script.append({"second": ctx.current_second - 12, "type": "damage", "adventurer_id": best_adv.id, "amount": dmg,
                            "message": f"{best_adv.name} sufre {dmg} daño por la trampa."})


def _event_ancient_inscription(ctx, adventurers):
    """El aventurero con mayor INT o WIS descifra runas para ganar XP."""
    from posada.engine.legacy import roll_d20
    import random

    best_adv = max(adventurers, key=lambda a: max(a.get_stat_modifiers()['int'], a.get_stat_modifiers()['wis']))
    mods = best_adv.get_stat_modifiers()
    bonus = max(mods['int'], mods['wis'])
    
    ctx.script.append({"second": ctx.current_second - 20, "type": "flavor", 
                        "message": f"🏛️ El grupo halla una [bold purple]Inscripción Antigua[/bold purple] en una estela de piedra. {best_adv.name} se acerca a estudiarla."})
    
    dc = random.randint(12, 16)
    roll = roll_d20()["value"]
    total = roll + bonus
    
    if total >= dc:
        xp_bonus = random.randint(30, 80)
        ctx.script.append({"second": ctx.current_second - 15, "type": "flavor", "xp_ganada": xp_bonus,
                            "message": f"   -> ¡ÉXITO! ({roll} + {bonus} = {total}). {best_adv.name} descifra los secretos del pasado (+{xp_bonus} XP)."})
        # Buff al personaje
        ctx.adv_status_tracker[best_adv.id].add('INSPIRED')
        ctx.script.append({"second": ctx.current_second - 10, "type": "flavor", 
                            "message": f"💡 {best_adv.name} se siente profundamente [bold yellow]INSPIRADO[/bold yellow] por la revelación."})
    else:
        ctx.script.append({"second": ctx.current_second - 15, "type": "flavor", 
                            "message": f"   -> FALLO ({roll} + {bonus} = {total}). Las runas están demasiado erosionadas para comprender su significado."})


def _event_wandering_merchant(ctx, adventurers):
    """Un mercader agradece al grupo y les dona monedas valiosas."""
    from posada.engine.legacy import COIN_COLORS
    import random

    ctx.script.append({"second": ctx.current_second - 20, "type": "flavor", 
                        "message": "🐫 Un excéntrico [bold yellow]Mercader Errante[/bold yellow] con una mula cargada se cruza en su camino."})
    ctx.script.append({"second": ctx.current_second - 15, "type": "flavor", 
                        "message": "\"¡Benditos sean los viajeros! Gracias por despejar estos caminos. Tomen, por su valentía.\""})
    
    # Recompensa alta
    rewards = [
        ('silver_penny', random.randint(1, 3)),
        ('ardite', random.randint(2, 5)),
        ('drabin', random.randint(1, 2))
    ]
    coin, amt = random.choice(rewards)
    color = COIN_COLORS.get(coin, 'white')
    display_name = coin.replace('_', ' ').title()
    
    ctx.script.append({"second": ctx.current_second - 10, "type": "loot", "coin": coin, "amount": amt,
                        "message": f"El Mercader obsequia al grupo {amt} [[{color}]{display_name}[/]]."})
