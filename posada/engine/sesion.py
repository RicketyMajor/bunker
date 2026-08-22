"""Closing a Deep Work session: loot, XP, levels and the bestiary, then mark it completed.

Moved out of `legacy.py` unchanged (Phase 3, Task 8). Keeps `@transaction.atomic`: without it an
exception halfway left the coins paid and the session open, so it could be completed — and paid —
twice.
"""
import random

from django.db import transaction
from django.utils import timezone

from posada.models import (
    GuildProfile, Adventurer, DeepWorkSession, Monster, DailyStatistic, Item, ItemRarity,
)
from posada.engine.data.tablas import XP_PER_MINUTE, CATEGORY_SYNERGY, COIN_COLORS
from posada.engine.economia import universal_consolidate, add_wealth_from_dict
from posada.engine.inventario import add_item_to_inventory, _auto_equip
from posada.engine.mercado import market_phase
from posada.engine.progresion import (
    distribute_tithe, distribute_random_stats, check_level_up, safe_randint,
)

# Reparte botin, XP, niveles y bestiario y recien al final marca session.completed. Sin la
# transaccion, una excepcion a mitad dejaba las monedas pagadas y la sesion abierta: se podia
# volver a completar y cobrar dos veces.
@transaction.atomic
def process_session_completion(session_id, survived_seconds=None, surrendered=False, focus_lock_broken=False):
    try:
        session = DeepWorkSession.objects.get(id=session_id)
    except DeepWorkSession.DoesNotExist:
        return {"status": "error", "message": "Sesión no encontrada"}

    if session.completed:
        return {"status": "warning", "message": "Esta sesión ya fue procesada"}

    guild, _ = GuildProfile.objects.get_or_create(id=1)
    adventurers = session.adventurers_involved.all()
    event_log = []

    if survived_seconds is None:
        survived_seconds = session.duration_minutes * 60

    # Re-genera el guion exacto usando determinista
    from posada.engine.runner import generate_session_script
    script = generate_session_script(
        session.id, session.duration_minutes, adventurers)

    loot = {
        'iron_half_penny': 0, 'iron_penny': 0, 'ardite': 0, 'drabin': 0,
        'copper_penny': 0, 'iota': 0,
        'silver_penny': 0, 'sueldo': 0, 'talento': 0,
        'real': 0, 'marco': 0
    }

    # Procesar eventos ocurridos dentro del tiempo sobrevivido
    damage_taken = {}
    session_monster_xp = 0
    session_monsters_killed = 0
    killed_monsters_ids = {}
    for event in script:
        if event["second"] <= survived_seconds:
            if event.get("xp_ganada"):
                session_monster_xp += event["xp_ganada"]
                session_monsters_killed += 1
            if event.get("monster_id"):
                m_id = event["monster_id"]
                killed_monsters_ids[m_id] = killed_monsters_ids.get(m_id, 0) + 1
            
            if event["type"] == "loot":
                loot[event["coin"]] += event["amount"]
            elif event["type"] == "damage":
                adv_id = event["adventurer_id"]
                damage_taken[adv_id] = damage_taken.get(adv_id, 0) + event["amount"]
            elif event["type"] == "heal":
                adv_id = event["adventurer_id"]
                damage_taken[adv_id] = damage_taken.get(adv_id, 0) - event["amount"]
            # guardar items en el inventario del aventurero
            elif event["type"] == "item_loot":
                adv = next((a for a in adventurers if a.id ==
                           event["adventurer_id"]), None)
                if adv:
                    try:
                        item_obj = Item.objects.get(id=event["item_id"])
                        add_item_to_inventory(adv, item_obj, event_log)
                    except Item.DoesNotExist:
                        pass

    # Aplicar daño real a los Puntos de Vida
    for adv in adventurers:
        dmg = damage_taken.get(adv.id, 0)
        if dmg > 0:
            adv.current_hp -= dmg
            
        if adv.current_hp <= 0:
            adv.current_hp = 0
            adv.is_recovering = True
            adv.recovery_time_left = 120  # 2 horas de cooldown
            event_log.append(
                f"{adv.name} cayó a 0 HP y fue llevado a la enfermería en camilla.")
        else:
            if dmg > 0:
                event_log.append(
                    f"{adv.name} sobrevivió a las heridas con {adv.current_hp}/{adv.max_hp} HP.")
            adv.sessions_survived += 1
            adv.monsters_killed += session_monsters_killed
            
        adv.save()

    # --- Bestiary Update ---
    from posada.models import BestiaryEntry
    for m_id, count in killed_monsters_ids.items():
        entry, created = BestiaryEntry.objects.get_or_create(
            guild=guild, monster_id=m_id, 
            defaults={'times_killed': 0}
        )
        if created:
            guild.add_prestige(10, 'bestiario',
                               detail=entry.monster.name, ref_id=m_id)
            guild.save()
            event_log.append(f"📖 ¡Nuevo descubrimiento en el Bestiario! (+10 Prestigio)")
        entry.times_killed += count
        entry.save()

    distribute_tithe(guild, adventurers, loot, event_log)
    market_phase(adventurers, event_log)

    # --- EXPERIENCIA DE AVENTUREROS ---
    survived_minutes = survived_seconds // 60
    base_xp = survived_minutes * XP_PER_MINUTE
    cat_lower = session.category.lower()

    # --- Mejoras del Gremio ---
    from posada.models import GuildUnlockedUpgrade
    has_cartography = GuildUnlockedUpgrade.objects.filter(
        guild=guild, upgrade__key='salon_cartografia').exists()

    for adv in adventurers:
        if focus_lock_broken:
            penalty = 50 * adv.level
            adv.experience = max(0, adv.experience - penalty)
            event_log.append(f"❌ ¡FOCUS LOCK ROTO! {adv.name} pierde {penalty} XP por cobardía.")
            adv.session_skills_used = []
            adv.combat_skills_used = []
            adv.class_resources = {}
            adv.save()
            continue

        multiplier = 1.0
        if has_cartography:
            multiplier += 0.10
            
        for key, classes in CATEGORY_SYNERGY.items():
            if key in cat_lower and adv.adv_class in classes:
                multiplier += 0.5
                event_log.append(
                    f"Sinergia: {adv.name} domina esta tarea (+50% XP).")
                break
        wis_bonus = sum(item.bonus_wis for item in adv.get_equipped_items())
        multiplier += (wis_bonus * 0.05)

        # --- EXPERIENCIA HÍBRIDA ---
        # Divide la XP total de los monstruos muertos entre los miembros del grupo
        adv_monster_xp = session_monster_xp // len(
            adventurers) if adventurers else 0
        total_earned_xp = int(base_xp * multiplier) + adv_monster_xp

        adv.experience += total_earned_xp
        # Registro en el log del botín de XP híbrida
        event_log.append(
            f"🎖️ {adv.name} ganó {total_earned_xp} XP ({int(base_xp * multiplier)} por tiempo + {adv_monster_xp} por monstruos).")
        # ------------------------------------

        # Limpia los enfriamientos para la próxima sesión
        adv.session_skills_used = []
        adv.combat_skills_used = []
        adv.class_resources = {}

        adv.save()
        check_level_up(adv, event_log)

    # --- RECUPERACIÓN PASIVA Y CAPILLA ---
    has_capilla = GuildUnlockedUpgrade.objects.filter(
        guild=guild, upgrade__key='capilla_recuperacion').exists()
    all_guild_advs = Adventurer.objects.all()
    for resting_adv in all_guild_advs:
        if resting_adv not in adventurers:
            base_heal = 15 if has_capilla else 5
            heal_amount = (survived_minutes / 60.0) * base_heal
            if heal_amount > 0 and resting_adv.current_hp < resting_adv.max_hp:
                resting_adv.current_hp = min(resting_adv.max_hp, resting_adv.current_hp + int(heal_amount))
                
            if resting_adv.is_recovering:
                # Si recovery_time_left cae a 0 o negativo
                new_time = max(0, resting_adv.recovery_time_left - survived_minutes)
                resting_adv.recovery_time_left = new_time
                if new_time == 0:
                    resting_adv.is_recovering = False
                    resting_adv.current_hp = resting_adv.max_hp
                    
            resting_adv.save()

    guild.save()
    session.event_log = event_log
    session.completed = True
    session.save()

    return {
        "status": "success", "message": "Sesión completada y simulada.",
        "loot": loot, "base_xp": base_xp, "log": event_log
    }
