"""Dice, derived skills, XP and levelling — everything `states/` reaches back into.

Moved out of `legacy.py` unchanged (Phase 3, Task 7). This is the seam the state machine imports
from, which is why it holds no model writes beyond the adventurer it levels up.
"""
import random

from django.db.models import Sum

from posada.models import GuildProfile
from posada.engine.data.tablas import SKILL_STAT_MAP, CLASS_SKILL_PROFICIENCIES

def safe_randint(a, b):
    """randint seguro que no falla si los rangos están invertidos."""
    return random.randint(min(a, b), max(a, b))


def get_derived_skills(adv):
    """Calcula el valor de las 18 habilidades de D&D."""
    mods = adv.get_stat_modifiers()
    prof_bonus = 2 + ((adv.level - 1) // 4)

    skills = {}
    is_bard = adv.adv_class == 'BRD'  # Regla de 'Jack of All Trades'
    proficiencies = CLASS_SKILL_PROFICIENCIES.get(adv.adv_class, [])

    for skill, stat in SKILL_STAT_MAP.items():
        stat_val = mods.get(stat, 0)
        if skill in proficiencies:
            skills[skill] = stat_val + prof_bonus
        elif is_bard:
            skills[skill] = stat_val + (prof_bonus // 2)
        else:
            skills[skill] = stat_val

    return skills


def roll_d20(advantage=False, disadvantage=False):
    """
    Devuelve un diccionario con el valor del dado y si fue crítico.
    """
    r1, r2 = random.randint(1, 20), random.randint(1, 20)

    if advantage and not disadvantage:
        val = max(r1, r2)
    elif disadvantage and not advantage:
        val = min(r1, r2)
    else:
        val = r1  # Tirada normal

    return {"value": val, "is_crit": val == 20, "is_fail": val == 1}


def distribute_tithe(guild, adventurers_qs, loot_dict, event_log):
    """El Gremio ya no cobra diezmo. El 100% del botín se divide entre los aventureros."""
    num_adventurers = adventurers_qs.count()
    if num_adventurers == 0:
        return

    event_log.append(
        "Los aventureros retienen el 100% del botín de su expedición.")
    for coin, amount in loot_dict.items():
        if amount == 0:
            continue
        share_per_adv = amount // num_adventurers
        remainder = amount % num_adventurers
        for index, adv in enumerate(adventurers_qs):
            extra = remainder if index == 0 else 0
            setattr(adv, coin, getattr(adv, coin) + share_per_adv + extra)
            adv.save()


def distribute_random_stats(adv, points_to_distribute):
    """Reparte una cantidad de puntos aleatoriamente entre los 7 atributos base."""
    stats = ['base_str', 'base_dex', 'base_con',
             'base_int', 'base_wis', 'base_cha', 'base_luk']
    for _ in range(points_to_distribute):
        stat = random.choice(stats)
        current_val = getattr(adv, stat)
        setattr(adv, stat, current_val + 1)
    adv.save()


def get_xp_requirement(level):
    """
    Calcula la experiencia necesaria para el SIGUIENTE nivel.
    Fórmula de curva cuadrática: (Nivel^2 * 500) + 500
    Lv 1->2: 1000 XP | Lv 2->3: 1500 XP | Lv 3->4: 2500 XP | Lv 4->5: 4000 XP
    """
    return (level ** 2) * 500 + 500


def check_level_up(adv, log):
    leveled_up = False
    # Evalua usando la nueva curva de dificultad
    while adv.experience >= get_xp_requirement(adv.level):
        adv.experience -= get_xp_requirement(adv.level)
        adv.level += 1
        leveled_up = True

        # Rebalanceo de HP según el rol
        if adv.adv_class in ['BBN', 'FTR', 'PAL']:
            hp_gain = random.randint(8, 12) + adv.base_con
        elif adv.adv_class in ['CLR', 'DRD', 'BRD', 'ART']:
            hp_gain = random.randint(5, 8) + adv.base_con
        else: # ROG, RGR, MNK, SOR, WLK, WIZ
            hp_gain = random.randint(3, 6) + adv.base_con
            
        adv.max_hp += hp_gain
        adv.current_hp = adv.max_hp

        stats = ['base_str', 'base_dex', 'base_con',
                 'base_int', 'base_wis', 'base_cha']
        chosen_stat = random.choice(stats)
        setattr(adv, chosen_stat, getattr(adv, chosen_stat) + 1)

        log.append(
            f"🎉 ¡[bold yellow]{adv.name}[/bold yellow] ha alcanzado el Nivel {adv.level}! (+{hp_gain} HP, +{chosen_stat.split('_')[1].upper()})")

    if leveled_up:
        adv.save()
        
    return leveled_up
