"""Estado COMBAT — Un tick de combate cada 15 segundos.

Incluye:
- Flavor de combate
- Preparación de iniciativa
- Turno de monstruos (ataques, DoTs, stun, on-hit effects)
- Turno de aventureros (skill eval, ataque básico, sneak attack, on-hit effects)
- Comprobación de muertes y drops
- Resolución del combate (transición a CAMPFIRE o EXPLORING)
"""
import random
import logging

from posada.models import InventorySlot, ItemRarity
from posada.engine.data.loot_tables import COIN_DROPS, ITEM_DROPS


def tick_combat(ctx):
    """Ejecuta un tick de 15 segundos en estado COMBAT."""
    from posada.engine.legacy import (
        roll_d20, is_class_allowed, FLAVOR_ADV, FLAVOR_MONSTER,
        COIN_COLORS, MONSTER_COLORS
    )
    from posada.skills import SkillRegistry

    ctx.current_second += 15
    if ctx.current_second >= ctx.total_seconds:
        return

    adventurers = ctx.adventurers

    # --- INMERSIÓN (1 por ronda) ---
    _combat_flavor(ctx, adventurers)

    # --- PREPARACIÓN DE INICIATIVA ---
    combatants = []
    for m in ctx.active_monsters_group:
        init = random.randint(1, 20) + m['stats']['dex']
        combatants.append({'type': 'monster', 'entity': m, 'init': init})
    for adv in adventurers:
        if ctx.temp_hp[adv.id] > 0:
            init = random.randint(1, 20) + adv.get_stat_modifiers()['dex']
            combatants.append({'type': 'adventurer', 'entity': adv, 'init': init})

    combatants.sort(key=lambda x: x['init'], reverse=True)

    for combatant in combatants:
        if combatant['type'] == 'monster':
            _monster_turn(ctx, combatant['entity'], adventurers)
        else:
            _adventurer_turn(ctx, combatant['entity'], adventurers)

    # --- Comprobación Universal de Muertes ---
    _check_deaths(ctx, adventurers)

    # --- RESOLUCIÓN DEL COMBATE ---
    _resolve_combat_end(ctx, adventurers)


def _combat_flavor(ctx, adventurers):
    """Genera un texto de inmersión de combate (50% aventurero, 50% monstruo)."""
    from posada.engine.legacy import FLAVOR_ADV, FLAVOR_MONSTER

    if random.random() < 0.5:
        f_adv = random.choice(adventurers)
        ctx.script.append({"second": ctx.current_second - 12, "type": "flavor",
                            "message": f"{f_adv.name} {random.choice(FLAVOR_ADV)}"})
    else:
        f_mon = random.choice(ctx.active_monsters_group)
        flav = random.choice(FLAVOR_MONSTER.get(
            f_mon['base'].category, FLAVOR_MONSTER['SML']))
        ctx.script.append({"second": ctx.current_second - 12, "type": "flavor",
                            "message": f"El [bold red]{f_mon['name']}[/bold red] {flav}"})


def _monster_turn(ctx, m, adventurers):
    """Ejecuta el turno de un monstruo."""
    from posada.engine.legacy import roll_d20

    if m['hp'] <= 0:
        return

    # --- DoT al monstruo ---
    dot_damage = 0
    if 'PSN' in m['status']:
        dot_damage += random.randint(1, 4)
    if 'BRN' in m['status']:
        dot_damage += random.randint(1, 6)
    if 'BLD' in m['status']:
        dot_damage += random.randint(1, 4)
    if dot_damage > 0:
        m['hp'] -= dot_damage
        ctx.script.append({"second": ctx.current_second - 10, "type": "flavor",
                            "message": f"🩸 [bold red]{m['name']}[/bold red] sufre {dot_damage} de daño por estados alterados."})
        if m['hp'] <= 0:
            return

    if 'STUNNED' in m['status']:
        m['status'].remove('STUNNED')
        ctx.script.append({"second": ctx.current_second - 8, "type": "flavor",
                            "message": f"💫 [bold red]{m['name']}[/bold red] está aturdido y no puede moverse."})
        return

    valid_targets = [a for a in adventurers if ctx.temp_hp[a.id] > 0]
    if not valid_targets:
        return
    target = random.choice(valid_targets)
    adv_mods = target.get_stat_modifiers()
    adv_evasion = 8 + max(adv_mods['dex'], adv_mods['armor'])
    adv_on_attack = 'BLINDED' in ctx.adv_status_tracker[target.id] or 'RECKLESS' in ctx.adv_status_tracker[target.id]
    disadv_on_attack = 'BLINDED' in m['status'] or 'DODGING' in ctx.adv_status_tracker[target.id]

    m_raw_roll = roll_d20(advantage=adv_on_attack, disadvantage=disadv_on_attack)["value"]
    m_roll_total = m_raw_roll + m['stats']['dex']

    is_hit = False
    if m_raw_roll == 20:
        is_hit = True
    elif m_raw_roll == 1:
        is_hit = False
    else:
        is_hit = (m_roll_total >= adv_evasion)

    if is_hit:
        base_m = m['base']
        m_dmg_dice = sum(random.randint(1, base_m.damage_dice_sides) for _ in range(base_m.damage_dice_count))
        m_extra_dice = sum(random.randint(1, getattr(base_m, 'bonus_damage_dice_sides', 4)) for _ in range(getattr(base_m, 'bonus_damage_dice_count', 0))) if getattr(base_m, 'bonus_damage_dice_count', 0) > 0 else 0
        m_dmg = m_dmg_dice + m_extra_dice + base_m.bonus_damage + m['stats']['str']

        if target.adv_class == 'ROG' and target.level >= 5 and 'REACTION_USED' not in ctx.adv_status_tracker[target.id]:
            m_dmg = m_dmg // 2
            ctx.adv_status_tracker[target.id].add('REACTION_USED')
            ctx.script.append({"second": ctx.current_second - 8, "type": "flavor", "message": f"🛡️ {target.name} usa [bold yellow]Esquiva Asombrosa[/bold yellow] y mitiga el impacto."})

        if 'RAGING' in ctx.adv_status_tracker[target.id]:
            m_dmg = m_dmg // 2

        eff_m = getattr(base_m, 'on_hit_effect', 'NON')
        if eff_m != 'NON' and random.randint(1, 100) <= getattr(base_m, 'effect_chance', 0):
            if eff_m == 'LFS':
                heal = sum(random.randint(1, getattr(base_m, 'effect_dice_sides', 4)) for _ in range(getattr(base_m, 'effect_dice_count', 1)))
                m['hp'] = min(m['max_hp'], m['hp'] + heal)
                ctx.script.append({"second": ctx.current_second - 8, "type": "flavor", "message": f"¡[bold red]{m['name']}[/bold red] drena {heal} HP de {target.name}!"})
            else:
                ctx.adv_status_tracker[target.id].add(eff_m)
                ctx.script.append({"second": ctx.current_second - 8, "type": "flavor", "message": f"¡[bold red]{m['name']}[/bold red] inyecta el estado {eff_m} a {target.name}!"})

        eff_adv = adv_mods.get('on_hit_effect', 'NON')
        if eff_adv == 'THN' and random.randint(1, 100) <= adv_mods.get('effect_chance', 0):
            thorns_dmg = random.randint(1, 4)
            m['hp'] -= thorns_dmg
            ctx.script.append({"second": ctx.current_second - 7, "type": "flavor", "message": f"La armadura de {target.name} devuelve {thorns_dmg} daño a [bold red]{m['name']}[/bold red]."})

        final_dmg = max(1, m_dmg - adv_mods['con'])
        ctx.temp_hp[target.id] -= final_dmg

        crit_msg = "[bold magenta]¡CRÍTICO![/bold magenta] " if m_raw_roll == 20 else ""
        ctx.script.append({"second": ctx.current_second - 8, "type": "damage", "adventurer_id": target.id, "amount": final_dmg,
                            "message": f"{crit_msg}[bold red]{m['name']}[/bold red] golpea a {target.name} ({final_dmg} daño)."})
        if ctx.temp_hp[target.id] <= 0:
            ctx.script.append({"second": ctx.current_second - 7, "type": "flavor", "message": f"⚠️ [bold yellow]{target.name}[/bold yellow] ha caído inconsciente en combate."})
    else:
        fail_msg = "falla estrepitosamente" if m_raw_roll == 1 else "falla su ataque"
        ctx.script.append({"second": ctx.current_second - 8, "type": "flavor", "message": f"[bold red]{m['name']}[/bold red] {fail_msg} contra {target.name}."})


def _adventurer_turn(ctx, adv, adventurers):
    """Ejecuta el turno de un aventurero."""
    from posada.engine.legacy import roll_d20, is_class_allowed
    from posada.skills import SkillRegistry

    if ctx.temp_hp[adv.id] <= 0:
        return
    if not ctx.active_monsters_group:
        return

    adv_mods = adv.get_stat_modifiers()

    # Auto-poción si HP bajo
    if ctx.temp_hp[adv.id] < (adv.max_hp * 0.3):
        heal_slots = list(InventorySlot.objects.filter(adventurer=adv, item__consumable_type='HEL', quantity__gt=0))
        if heal_slots:
            slot = heal_slots[0]
            slot.quantity -= 1
            if slot.quantity <= 0:
                slot.delete()
            else:
                slot.save()
            heal_amount = slot.item.consumable_amount if slot.item.consumable_amount > 0 else random.randint(10, 20)
            ctx.temp_hp[adv.id] = min(adv.max_hp, ctx.temp_hp[adv.id] + heal_amount)
            ctx.script.append({"second": ctx.current_second - 5, "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                "message": f"¡Salud Crítica! {adv.name} bebe desesperadamente una [bold cyan]{slot.item.name}[/bold cyan] (+{heal_amount} HP)."})
            return

    # DoT al aventurero
    dot_damage = 0
    if 'PSN' in ctx.adv_status_tracker[adv.id]:
        dot_damage += random.randint(1, 4)
    if 'BRN' in ctx.adv_status_tracker[adv.id]:
        dot_damage += random.randint(1, 6)
    if 'BLD' in ctx.adv_status_tracker[adv.id]:
        dot_damage += random.randint(1, 4)
    if dot_damage > 0:
        ctx.temp_hp[adv.id] -= dot_damage
        ctx.script.append({"second": ctx.current_second - 6, "type": "damage", "adventurer_id": adv.id,
                            "amount": dot_damage, "message": f"{adv.name} sufre {dot_damage} de daño continuo."})
        if ctx.temp_hp[adv.id] <= 0:
            ctx.script.append({"second": ctx.current_second - 5, "type": "flavor", "message": f"⚠️ [bold yellow]{adv.name}[/bold yellow] ha caído inconsciente por sus heridas."})
            return

    # Evaluación de habilidades de combate
    available_skills = []
    for skill_id, skill_data in SkillRegistry.get_all_skills().items():
        if adv.adv_class in skill_data["allowed_classes"] and adv.level >= skill_data["req_level"]:
            if skill_data["type"] == "COMBAT" and skill_id not in ctx.combat_skills_tracker[adv.id]:
                available_skills.append(skill_data)

    best_action = "BASIC_ATTACK"
    best_score = 50

    context = {
        'caster': adv,
        'allies': adventurers,
        'enemies': ctx.active_monsters_group,
        'adv_status': ctx.adv_status_tracker,
        'current_second': ctx.current_second - 4,
        'log': ctx.script,
        'eval_mode': True
    }

    for skill in available_skills:
        try:
            score = skill["execute"](context)
            if score > best_score:
                best_score = score
                best_action = skill
        except Exception as e:
            logging.warning(f"Skill eval error: {e}")

    context['eval_mode'] = False

    if best_action == "BASIC_ATTACK":
        _basic_attack(ctx, adv, adv_mods, adventurers)
    else:
        success = best_action["execute"](context)
        if success:
            ctx.combat_skills_tracker[adv.id].add(best_action["id"])


def _basic_attack(ctx, adv, adv_mods, adventurers):
    """Ejecuta un ataque básico del aventurero."""
    from posada.engine.legacy import roll_d20

    ctx.adv_status_tracker[adv.id].discard('REACTION_USED')
    attacks = 2 if adv.level >= 5 and adv.adv_class in ['FTR', 'BBN', 'RGR', 'PAL', 'MNK'] else 1

    for _ in range(attacks):
        if not ctx.active_monsters_group:
            break
        target_m = random.choice(ctx.active_monsters_group)
        attack_stat = max(adv_mods['str'], adv_mods['dex'])

        adv_on_attack = 'BLINDED' in target_m['status'] or 'RECKLESS' in ctx.adv_status_tracker[adv.id]
        disadv_on_attack = 'BLINDED' in ctx.adv_status_tracker[adv.id]

        m_evasion = 8 + max(target_m['stats']['dex'], target_m['stats'].get('armor', 0))
        a_raw_roll = roll_d20(advantage=adv_on_attack, disadvantage=disadv_on_attack)["value"]
        a_roll_total = a_raw_roll + attack_stat

        if 'INSPIRED' in ctx.adv_status_tracker[adv.id]:
            bard_dice = random.randint(1, 6)
            a_roll_total += bard_dice
            ctx.adv_status_tracker[adv.id].remove('INSPIRED')
            ctx.script.append({"second": ctx.current_second - 5, "type": "flavor", "message": f"🎵 ¡La música del Bardo guía el golpe! (+{bard_dice})"})

        is_hit = False
        if a_raw_roll == 20:
            is_hit = True
        elif a_raw_roll == 1:
            is_hit = False
        else:
            is_hit = (a_roll_total >= m_evasion)

        if is_hit:
            sides = adv_mods.get('weapon_dice_sides', 4) or 4
            count = adv_mods.get('weapon_dice_count', 1) or 1
            a_dmg = sum(random.randint(1, sides) for _ in range(count)) + adv_mods['damage'] + adv_mods['str']

            extra_count = adv_mods.get('bonus_dmg_dice_count', 0)
            if extra_count > 0:
                extra_sides = adv_mods.get('bonus_dmg_dice_sides', 4) or 4
                a_dmg += sum(random.randint(1, extra_sides) for _ in range(extra_count))

            if adv.adv_class == 'ROG' and adv_on_attack:
                sneak_dice = (adv.level + 1) // 2
                sneak_dmg = sum(random.randint(1, 6) for _ in range(sneak_dice))
                a_dmg += sneak_dmg
                ctx.script.append({"second": ctx.current_second - 5, "type": "flavor", "message": f"🗡️ ¡Ataque Furtivo de {adv.name}! (+{sneak_dmg})"})

            if 'RAGING' in ctx.adv_status_tracker[adv.id]:
                a_dmg += 2
            if 'INFUSED_WEAPON' in ctx.adv_status_tracker[adv.id]:
                a_dmg += 1

            eff = adv_mods.get('on_hit_effect', 'NON')
            if eff != 'NON' and eff != 'THN':
                if random.randint(1, 100) <= adv_mods.get('effect_chance', 0):
                    if eff == 'LFS':
                        heal = sum(random.randint(1, adv_mods['effect_dice_sides']) for _ in range(adv_mods['effect_dice_count']))
                        ctx.temp_hp[adv.id] = min(adv.max_hp, ctx.temp_hp[adv.id] + heal)
                        ctx.script.append({"second": ctx.current_second - 4, "type": "heal", "adventurer_id": adv.id, "amount": heal, "message": f"🦇 {adv.name} drena {heal} HP."})
                    else:
                        target_m['status'].add(eff)
                        eff_names = {'PSN': 'Veneno', 'BLD': 'Sangrado', 'BRN': 'Quemaduras', 'STN': 'Aturdimiento', 'BLN': 'Ceguera'}
                        ctx.script.append({"second": ctx.current_second - 4, "type": "flavor", "message": f"¡{adv.name} inflige {eff_names.get(eff, eff)}!"})

            final_dmg = max(1, a_dmg - target_m['stats']['con'])
            target_m['hp'] -= final_dmg

            crit_msg = "[bold magenta]¡CRÍTICO![/bold magenta] " if a_raw_roll == 20 else ""
            ctx.script.append({"second": ctx.current_second - 4, "type": "flavor",
                                "message": f"{crit_msg}{adv.name} asesta un golpe de {final_dmg} daño a [bold red]{target_m['name']}[/bold red]."})
        else:
            fail_msg = "falla catastróficamente" if a_raw_roll == 1 else "falla su ataque"
            ctx.script.append({"second": ctx.current_second - 4, "type": "flavor", "message": f"{adv.name} {fail_msg} contra [bold red]{target_m['name']}[/bold red]."})


def _check_deaths(ctx, adventurers):
    """Comprueba muertes de monstruos, genera drops y XP."""
    from posada.engine.legacy import COIN_COLORS, MONSTER_COLORS, is_class_allowed

    for m in list(ctx.active_monsters_group):
        if m['hp'] <= 0:
            xp_ganada = getattr(m['base'], 'xp_reward', 0)
            m_color = MONSTER_COLORS.get(m['base'].category, 'red')
            ctx.script.append({"second": ctx.current_second - 2, "type": "flavor",
                                "message": f"💀 [[{m_color}]{m['name']}[/]] cae derrotado (+{xp_ganada} XP).", "xp_ganada": xp_ganada})
            ctx.active_monsters_group.remove(m)

            # Generar Monedas
            for coin, max_amt, prob in COIN_DROPS.get(m['base'].category, []):
                if random.random() < prob:
                    amt = random.randint(1, max_amt)
                    c_color = COIN_COLORS.get(coin, 'white')
                    display_name = coin.replace('_', ' ').title()
                    if coin == 'iron_half_penny':
                        display_name = "Medio Penique de Hierro"
                    ctx.script.append({"second": ctx.current_second - 1, "type": "loot", "coin": coin, "amount": amt,
                                        "message": f"El monstruo soltó {amt} [[{c_color}]{display_name}[/]]."})

            # Generar Items Raros
            adv = random.choice(adventurers) if adventurers else None
            for rarity, base_prob in ITEM_DROPS.get(m['base'].category, []):
                luk_bonus = adv.base_luk * 0.01 if adv else 0
                if random.random() < (base_prob + luk_bonus):
                    pool = [it for it in ctx.all_items_db if it.rarity == rarity]
                    if pool:
                        drop_item = random.choice(pool)
                        color = ItemRarity.get_color(drop_item.rarity)

                        # Busca quién necesita más el ítem
                        def get_adv_for_item(item):
                            if item.item_type == 'MSC':
                                return random.choice(adventurers)
                            valid_advs = [a for a in adventurers if is_class_allowed(a, item)]
                            if not valid_advs:
                                return random.choice(adventurers)
                            valid_advs.sort(key=lambda a: len(a.get_equipped_items()))
                            return valid_advs[0]

                        winner = get_adv_for_item(drop_item)
                        ctx.script.append({
                            "second": ctx.current_second, "type": "item_loot", "item_id": drop_item.id,
                            "adventurer_id": winner.id,
                            "message": f"¡BOTÍN RARO! {winner.name} obtuvo [[{color}]{drop_item.name}[/]]."
                        })


def _resolve_combat_end(ctx, adventurers):
    """Resuelve el final del combate (victoria, derrota, campfire)."""
    all_dead = all(ctx.temp_hp[a.id] <= 0 for a in adventurers)
    if not ctx.active_monsters_group or all_dead:
        # Reseteo del enfriamiento de habilidades de combate
        for adv_id in ctx.combat_skills_tracker:
            ctx.combat_skills_tracker[adv_id].clear()
            ctx.adv_status_tracker[adv_id].clear()

        if all_dead:
            ctx.script.append({"second": ctx.current_second, "type": "flavor", "message": "💀 ¡DERROTA! Todo el grupo ha caído."})
            ctx.active_monsters_group.clear()
            ctx.state = "CAMPFIRE"
        else:
            ctx.script.append({"second": ctx.current_second, "type": "flavor", "message": "¡VICTORIA! La zona está despejada."})
            if any(ctx.temp_hp[a.id] <= 0 for a in adventurers):
                ctx.script.append({"second": ctx.current_second + 1, "type": "flavor", "message": "🏕️ El grupo decide montar un campamento para atender a los heridos."})
                ctx.state = "CAMPFIRE"
            else:
                ctx.state = "EXPLORING"
