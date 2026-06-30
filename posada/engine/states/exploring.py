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

    category_weights = {'SML': 60, 'MED': 30, 'LRG': 8, 'EPC': 2}
    weights = [category_weights.get(m.category, 10) for m in ctx.monsters_db]
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
