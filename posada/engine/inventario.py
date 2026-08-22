"""Inventory and equipment: scoring an item, storing it, and deciding what to wear.

Moved out of `legacy.py` unchanged (Phase 3, Task 5). Equipment and the backpack are DISJOINT
containers here — the `equip` branch deletes the inventory slot — which is why `_auto_equip`
hands the displaced item back to `add_item_to_inventory` rather than leaving it in both.
"""
from django.utils import timezone

from posada.models import GuildProfile, InventorySlot, ItemRarity, JournalEntry
from posada.engine.data.tablas import CLASS_PROFICIENCIES
from posada.engine.economia import universal_consolidate

def get_item_score(item):
    """Calcula el 'Poder Total' de un objeto sumando todas sus estadísticas."""
    if not item:
        return -1
    return (item.bonus_damage * 2) + (item.bonus_armor * 2) + \
        item.bonus_str + item.bonus_dex + item.bonus_con + \
        item.bonus_int + item.bonus_wis + item.bonus_cha + item.bonus_luk


def add_item_to_inventory(adv, item, event_log=None):
    """Maneja la lógica de stacks, mejoras de Gremio, y comisión de Mensajería Arcana."""
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    is_stackable = item.item_type in ['CNS', 'MSC']
    color = ItemRarity.get_color(item.rarity)

    # Intentar agrupar si es stackeable
    if is_stackable:
        slots = InventorySlot.objects.filter(
            adventurer=adv, item=item, quantity__lt=16)
        if slots.exists():
            slot = slots.first()
            slot.quantity += 1
            slot.save()
            if event_log is not None:
                event_log.append(
                    f"{adv.name} guardó [[{color}]{item.name}[/]] (x{slot.quantity}).")
            return

    # Intentar usar un nuevo slot en la mochila (usa la propiedad dinámica)
    if adv.inventory.count() < adv.inventory_capacity:
        InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)
        if event_log is not None:
            event_log.append(
                f"{adv.name} guardó [[{color}]{item.name}[/]] en su mochila.")
    else:
        # if Mochila llena, intentar usar Mensajería Arcana
        has_mensajeria = guild.unlocked_upgrades.filter(
            upgrade__key='mensajeria_arcana').exists()
        if not has_mensajeria:
            if event_log is not None:
                event_log.append(
                    f"Mochila de {adv.name} llena. [[{color}]{item.name}[/]] fue abandonado (Requiere Mensajería Arcana).")
            return

        # Verificar Buff "Claridad Mental" (Escribir en el diario hoy)
        today = timezone.localdate()
        claridad_mental = JournalEntry.objects.filter(
            created_at__date=today).exists()

        fee_paid = False
        fee_msg = ""

        if claridad_mental:
            fee_paid = True
            fee_msg = "(Gratis por Claridad Mental)"
        else:
            # Intentar pagar 1 Drabín rompiendo monedas si es necesario
            if guild.drabin >= 1:
                guild.drabin -= 1
                fee_paid = True
            elif guild.iota >= 1:
                guild.iota -= 1
                guild.drabin += 9
                fee_paid = True
            elif guild.talento >= 1:
                guild.talento -= 1
                guild.iota += 9
                guild.drabin += 9
                fee_paid = True

            if fee_paid:
                fee_msg = "(-1 Drabín)"

        if not fee_paid:
            if event_log is not None:
                event_log.append(
                    f"Mochila llena. El Gremio no tiene fondos para el envío de [[{color}]{item.name}[/]]. Objeto perdido.")
            return

        # Si pagó o es gratis, se envía al cofre
        if not claridad_mental:
            guild.save()
            universal_consolidate(guild)  # Ordenar el vuelto

        if event_log is not None:
            event_log.append(
                f"Mochila llena. Mensajeros llevaron [[{color}]{item.name}[/]] al Cofre {fee_msg}.")

        if is_stackable:
            g_slot, creado = InventorySlot.objects.get_or_create(
                guild=guild, item=item, adventurer=None, defaults={'quantity': 1})
            if not creado:
                g_slot.quantity += 1
                g_slot.save()
        else:
            InventorySlot.objects.create(
                guild=guild, item=item, adventurer=None, quantity=1)


def _auto_equip(adv, item, event_log, pull_type):
    """Evalúa si el objeto es mejor y guarda lo sobrante en la mochila."""
    color = ItemRarity.get_color(item.rarity)  # Color según la rareza

    if not is_class_allowed(adv, item):
        add_item_to_inventory(adv, item, event_log)
        event_log.append(
            f"{adv.name} guardó [[{color}]{item.name}[/]] (Incompatible).")
        return

    # Consumibles
    if item.item_type == 'CNS':
        if adv.current_hp < adv.max_hp:
            adv.current_hp = min(adv.max_hp, adv.current_hp + 10)
            event_log.append(
                f"{adv.name} bebió [[{color}]{item.name}[/]] y recuperó HP.")
        else:
            add_item_to_inventory(adv, item, event_log)
            event_log.append(
                f"{adv.name} guardó el objeto [[{color}]{item.name}[/]].")
        return

    # Misceláneos
    elif item.item_type == 'MSC':
        add_item_to_inventory(adv, item, event_log)
        event_log.append(
            f"{adv.name} guardó el objeto de lujo [[{color}]{item.name}[/]].")
        return

    score_new = get_item_score(item)

    # los 2 Anillos
    if item.item_type == 'RNG':
        s1 = get_item_score(adv.equip_ring_1) if adv.equip_ring_1 else -1
        s2 = get_item_score(adv.equip_ring_2) if adv.equip_ring_2 else -1

        if score_new > min(s1, s2):
            if s1 <= s2:
                old_item = adv.equip_ring_1
                adv.equip_ring_1 = item
            else:
                old_item = adv.equip_ring_2
                adv.equip_ring_2 = item

            if old_item:
                add_item_to_inventory(adv, old_item)
            event_log.append(
                f"{adv.name} se equipó [[{color}]{item.name}[/]].")
            adv.save()
        else:
            add_item_to_inventory(adv, item, event_log)
        return

    # el resto del equipo
    slot_map = {
        'W1H': 'equip_main_hand', 'W2H': 'equip_main_hand', 'OFF': 'equip_off_hand',
        'HED': 'equip_head', 'TRS': 'equip_torso', 'LEG': 'equip_legs',
        'HND': 'equip_hands', 'FET': 'equip_feet', 'NCK': 'equip_necklace',
        'BRC': 'equip_bracelet', 'EAR': 'equip_earring'
    }

    slot_name = slot_map.get(item.item_type)
    if not slot_name:
        return

    current_item = getattr(adv, slot_name)
    score_current = get_item_score(current_item) if current_item else -1

    # Bloqueo de Escudo si usa Mandoble
    if item.item_type == 'OFF' and getattr(adv, 'equip_main_hand') and getattr(adv, 'equip_main_hand').item_type == 'W2H':
        add_item_to_inventory(adv, item, event_log)
        return

    if score_new > score_current:
        if current_item:
            add_item_to_inventory(adv, current_item, event_log)
        setattr(adv, slot_name, item)

        if item.item_type == 'W2H' and adv.equip_off_hand:
            add_item_to_inventory(adv, adv.equip_off_hand)
            adv.equip_off_hand = None

        event_log.append(f"{adv.name} se equipó [[{color}]{item.name}[/]].")
        adv.save()
    else:
        add_item_to_inventory(adv, item, event_log)


def is_class_allowed(adv, item):
    """Verifica si la clase del aventurero puede usar el objeto cruzando las etiquetas."""
    # Consumibles, accesorios y misceláneos pueden ser usados por todos
    if item.item_type in ['CNS', 'MSC', 'NCK', 'RNG', 'BRC', 'EAR']:
        return True

    prof = CLASS_PROFICIENCIES.get(adv.adv_class)
    if not prof:
        return False

    # Filtro de Material (Ej: Druida choca con armaduras de metal)
    if item.material in prof['forbidden_materials']:
        return False

    # Filtro de Armas
    if item.item_type in ['W1H', 'W2H']:
        # Clérigo choca con una espada (Cortante = SLS, y está en forbidden_materials)
        if item.weapon_type in prof['forbidden_materials']:
            return False
        if item.weapon_type not in prof['weapons']:
            return False

    # Filtro de Armaduras / Escudos
    elif item.item_type in ['HED', 'TRS', 'LGS', 'HND', 'FET', 'OFF']:
        if item.armor_weight not in prof['armor']:
            return False

    return True
