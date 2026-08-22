"""The market phase: seeding the catalogue and letting adventurers shop.

Moved out of `legacy.py` unchanged (Phase 3, Task 6). `market_phase` is the only caller of both
seeds, and it declares the atomicity `pay_with_change` refuses to run without.
"""
import random

from django.db import transaction

from posada.models import Item, GuildUpgrade
from posada.engine.economia import universal_consolidate, can_afford, pay_with_change
from posada.engine.inventario import get_item_score, is_class_allowed, _auto_equip
from posada.engine.economia import get_imperial_value, get_commonwealth_value

def _seed_items_if_empty():
    """Ejecuta el catálogo oficial de load_items si la base de datos de objetos está vacía."""
    if not Item.objects.exists():
        from django.core.management import call_command
        call_command('load_items')


def _seed_guild_upgrades():
    """Forja los planos de las mejoras de Gremio (Niveles 1 al 10)."""
    upgrades = [
        {'key': 'mensajeria_arcana', 'name': 'Mensajería Arcana', 'description': 'Envía el excedente de botín al cofre por 1 Drabín.', 'cost_coin': 'marco', 'cost_amount': 1, 'req_prestige_level': 1},
        {'key': 'taberna_ampliada', 'name': 'Taberna Ampliada', 'description': 'Mayor afluencia de reclutas (Inmersión).', 'cost_coin': 'marco', 'cost_amount': 2, 'req_prestige_level': 2},
        {'key': 'mochila_lv2', 'name': 'Mochilas de Contención', 'description': 'Aumenta la mochila de los aventureros a 15 ranuras.', 'cost_coin': 'marco', 'cost_amount': 2, 'req_prestige_level': 2},
        {'key': 'tablon_patroc', 'name': 'Tablón Patrocinado', 'description': '5% prob. de ítem épico al completar hábitos Rango S.', 'cost_coin': 'marco', 'cost_amount': 3, 'req_prestige_level': 3},
        {'key': 'herreria_basica', 'name': 'Herrería Básica', 'description': 'Los aventureros sufren menos daño pasivo (Inmersión/Defensa).', 'cost_coin': 'marco', 'cost_amount': 3, 'req_prestige_level': 3},
        {'key': 'salon_cartografia', 'name': 'Salón de Cartografía', 'description': '+10% de ganancia de experiencia en Deep Work.', 'cost_coin': 'marco', 'cost_amount': 4, 'req_prestige_level': 4},
        {'key': 'guardia_gremio', 'name': 'Guardia del Gremio', 'description': 'La Posada está protegida contra asaltos nocturnos.', 'cost_coin': 'marco', 'cost_amount': 5, 'req_prestige_level': 5},
        {'key': 'capilla_recuperacion', 'name': 'Capilla de Recuperación', 'description': 'Aumenta la curación pasiva de los aventureros.', 'cost_coin': 'marco', 'cost_amount': 6, 'req_prestige_level': 6},
        {'key': 'red_informantes', 'name': 'Red de Informantes', 'description': 'Otorga ventajas al reclutar.', 'cost_coin': 'marco', 'cost_amount': 8, 'req_prestige_level': 7},
        {'key': 'torreon_mago', 'name': 'Torreón del Mago', 'description': 'Aumenta la regeneración de maná global.', 'cost_coin': 'marco', 'cost_amount': 10, 'req_prestige_level': 8},
        {'key': 'boveda_gremio', 'name': 'Bóveda de Gremio', 'description': 'Permite amasar grandes riquezas sin penalización.', 'cost_coin': 'marco', 'cost_amount': 12, 'req_prestige_level': 9},
        {'key': 'ciudadela', 'name': 'Ciudadela del Gremio', 'description': 'El gremio se convierte en el gobernante de la región.', 'cost_coin': 'marco', 'cost_amount': 15, 'req_prestige_level': 10},
    ]
    for up in upgrades:
        GuildUpgrade.objects.update_or_create(
            key=up['key'],
            defaults={
                'name': up['name'],
                'description': up['description'],
                'cost_coin': up['cost_coin'],
                'cost_amount': up['cost_amount'],
                'req_prestige_level': up['req_prestige_level']
            }
        )


# Its only caller is `process_session_completion`, which is already atomic, so this changes
# nothing today — a nested atomic() is just a savepoint. It exists so the guarantee survives the
# second caller, which would otherwise inherit nothing and trip the guard in `pay_with_change`.
@transaction.atomic
def market_phase(adventurers_qs, event_log):
    """Simula las compras inteligentes del mercado."""
    _seed_items_if_empty()
    _seed_guild_upgrades()
    all_items = list(Item.objects.all())

    for adv in adventurers_qs:
        universal_consolidate(adv)
        if adv.is_recovering:
            continue

        valid_items = [i for i in all_items if is_class_allowed(adv, i)]
        
        shopping = True
        purchases = 0
        while shopping and purchases < 5:
            # Se asegura de que no tengan valor 0 absoluto para evitar comprar items default de pruebas
            affordable_items = [i for i in valid_items if can_afford(adv, i) and (get_imperial_value(i) > 0 or get_commonwealth_value(i) > 0)]
            if not affordable_items:
                break
            
            # Inteligencia de Ahorro: Revisar si hay objetos deseables (vacíos o mejoras) que el aventurero aún no puede pagar.
            is_saving = False
            unaffordable_items = [i for i in valid_items if not can_afford(adv, i) and i.item_type not in ['CNS', 'MSC']]
            for item in unaffordable_items:
                score_new = get_item_score(item)
                curr_score = -1
                if item.item_type == 'RNG':
                    if not adv.equip_ring_1 or not adv.equip_ring_2:
                        is_saving = True
                        break
                    s1 = get_item_score(adv.equip_ring_1)
                    s2 = get_item_score(adv.equip_ring_2)
                    curr_score = min(s1, s2)
                else:
                    slot_map = {
                        'W1H': 'equip_main_hand', 'W2H': 'equip_main_hand', 'OFF': 'equip_off_hand',
                        'HED': 'equip_head', 'TRS': 'equip_torso', 'LEG': 'equip_legs',
                        'HND': 'equip_hands', 'FET': 'equip_feet', 'NCK': 'equip_necklace',
                        'BRC': 'equip_bracelet', 'EAR': 'equip_earring'
                    }
                    slot_name = slot_map.get(item.item_type)
                    if slot_name:
                        if not getattr(adv, slot_name):
                            is_saving = True
                            break
                        curr_item = getattr(adv, slot_name)
                        curr_score = get_item_score(curr_item) if curr_item else -1
                        if item.item_type == 'OFF' and getattr(adv, 'equip_main_hand') and getattr(adv, 'equip_main_hand').item_type == 'W2H':
                            continue

                if score_new > curr_score:
                    is_saving = True
                    break

            purchased_item = None

            # 1. Prioridad: Supervivencia
            if adv.current_hp < (adv.max_hp * 0.4):
                potions = [i for i in affordable_items if i.item_type == 'CNS']
                if potions:
                    purchased_item = max(potions, key=lambda x: get_item_score(x))

            # 2. Prioridad: Llenar espacios vacíos
            if not purchased_item:
                for item in affordable_items:
                    if item.item_type in ['CNS', 'MSC']:
                        continue
                    
                    if item.item_type == 'RNG':
                        if not adv.equip_ring_1 or not adv.equip_ring_2:
                            purchased_item = item
                            break
                    else:
                        slot_map = {
                            'W1H': 'equip_main_hand', 'W2H': 'equip_main_hand', 'OFF': 'equip_off_hand',
                            'HED': 'equip_head', 'TRS': 'equip_torso', 'LEG': 'equip_legs',
                            'HND': 'equip_hands', 'FET': 'equip_feet', 'NCK': 'equip_necklace',
                            'BRC': 'equip_bracelet', 'EAR': 'equip_earring'
                        }
                        slot_name = slot_map.get(item.item_type)
                        if slot_name and not getattr(adv, slot_name):
                            # Si está comprando un OFF, validar que no tenga un W2H
                            if item.item_type == 'OFF' and getattr(adv, 'equip_main_hand') and getattr(adv, 'equip_main_hand').item_type == 'W2H':
                                continue
                            purchased_item = item
                            break

            # 3. Prioridad: Mejoras significativas
            if not purchased_item:
                best_upgrade = None
                best_score_diff = 0

                for item in affordable_items:
                    if item.item_type in ['CNS', 'MSC']:
                        continue

                    score_new = get_item_score(item)
                    curr_score = -1

                    if item.item_type == 'RNG':
                        s1 = get_item_score(adv.equip_ring_1) if adv.equip_ring_1 else -1
                        s2 = get_item_score(adv.equip_ring_2) if adv.equip_ring_2 else -1
                        curr_score = min(s1, s2)
                    else:
                        slot_map = {
                            'W1H': 'equip_main_hand', 'W2H': 'equip_main_hand', 'OFF': 'equip_off_hand',
                            'HED': 'equip_head', 'TRS': 'equip_torso', 'LEG': 'equip_legs',
                            'HND': 'equip_hands', 'FET': 'equip_feet', 'NCK': 'equip_necklace',
                            'BRC': 'equip_bracelet', 'EAR': 'equip_earring'
                        }
                        slot_name = slot_map.get(item.item_type)
                        if slot_name:
                            curr_item = getattr(adv, slot_name)
                            curr_score = get_item_score(curr_item) if curr_item else -1

                            if item.item_type == 'OFF' and getattr(adv, 'equip_main_hand') and getattr(adv, 'equip_main_hand').item_type == 'W2H':
                                continue

                    if score_new > curr_score:
                        diff = score_new - curr_score
                        if diff > best_score_diff:
                            best_score_diff = diff
                            best_upgrade = item

                if best_upgrade:
                    purchased_item = best_upgrade

            # 4. Prioridad: Misceláneos o consumibles si no hay más equipo útil
            # Si el aventurero está ahorrando para algo caro, la probabilidad de malgastar dinero en misceláneos baja drásticamente (del 40% al 5%).
            buy_chance = 0.05 if is_saving else 0.40
            if not purchased_item and random.random() < buy_chance:
                misc_items = [i for i in affordable_items if i.item_type in ['CNS', 'MSC']]
                if misc_items:
                    purchased_item = random.choice(misc_items)

            # Ejecutar transacción
            if purchased_item:
                if pay_with_change(adv, purchased_item):
                    _auto_equip(adv, purchased_item, event_log, "Mercado")
                    purchases += 1
            else:
                shopping = False
