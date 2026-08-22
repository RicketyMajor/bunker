"""Wealth: consolidation, valuation, and paying with change.

Moved out of `legacy.py` unchanged (Phase 3, Task 4). `pay_with_change` keeps the Phase 2 guard
that refuses to run outside `transaction.atomic()`, and its comment, because the guard is the
invariant `tests/test_posada_invariantes.py` plants against.
"""
import random

from django.db import transaction

from posada.models import GuildProfile

def universal_consolidate(entity):
    """Aplica la consolidación a cualquier entidad (Aventurero o Gremio)."""
    log = []
    # --- Senda de la Mancomunidad ---
    if entity.ardite >= 11:
        n = entity.ardite // 11
        entity.ardite %= 11
        entity.drabin += n
        log.append(f"Fundidos ardites en {n} Drabín.")
    if entity.drabin >= 10:
        n = entity.drabin // 10
        entity.drabin %= 10
        entity.iota += n
    if entity.iota >= 10:
        n = entity.iota // 10
        entity.iota %= 10
        entity.talento += n

    # --- Senda Imperial ---
    if entity.iron_half_penny >= 2:
        n = entity.iron_half_penny // 2
        entity.iron_half_penny %= 2
        entity.iron_penny += n
    if entity.iron_penny >= 5:
        n = entity.iron_penny // 5
        entity.iron_penny %= 5
        entity.copper_penny += n
    if entity.copper_penny >= 10:
        n = entity.copper_penny // 10
        entity.copper_penny %= 10
        entity.silver_penny += n

    # --- Puentes de Alto Valor ---
    from posada.models import GuildUnlockedUpgrade, Adventurer, GuildProfile
    guild = None
    if isinstance(entity, GuildProfile):
        guild = entity
    elif isinstance(entity, Adventurer):
        guild, _ = GuildProfile.objects.get_or_create(id=1)
        
    has_casa = False
    if guild:
        has_casa = GuildUnlockedUpgrade.objects.filter(guild=guild, upgrade__key='casa_de_cambio').exists()

    if has_casa and entity.silver_penny >= 10:
        n = entity.silver_penny // 10
        entity.silver_penny %= 10
        entity.talento += n
        log.append(f"Casa de Cambio: {n*10} Peniques de Plata convertidos a {n} Talento.")

    if entity.sueldo >= 32:
        n = entity.sueldo // 32
        entity.sueldo %= 32
        entity.talento += n
    if entity.talento >= 10:
        n = entity.talento // 10
        entity.talento %= 10
        entity.marco += n

    entity.save()
    return log


def calculate_sell_value(item, pct=0.50):
    """Calcula el valor de venta de un item como porcentaje de su coste real.

    Convierte todo el coste del item a unidades base (ardites = 32 u.b. para
    la Mancomunidad, medios peniques para Imperial), aplica el porcentaje,
    y redistribuye en denominaciones óptimas.

    Returns:
        dict con las 11 monedas y sus cantidades resultantes.
    """
    # --- Valor total en unidades base de la Mancomunidad ---
    cw_total = (
        item.cost_marco * 352000 +
        item.cost_real * 88000 +
        item.cost_talento * 35200 +
        item.cost_sueldo * 1100 +
        item.cost_iota * 3520 +
        item.cost_drabin * 352 +
        item.cost_ardite * 32
    )
    cw_sell = int(cw_total * pct)

    # --- Valor total en unidades base Imperial (medios peniques de hierro) ---
    imp_total = (
        item.cost_silver_penny * 100 +
        item.cost_copper_penny * 10 +
        item.cost_iron_penny * 2 +
        item.cost_iron_half_penny
    )
    imp_sell = int(imp_total * pct)

    # --- Descomponer Mancomunidad en denominaciones óptimas ---
    result = {}
    cw_denominations = [
        ('marco', 352000), ('real', 88000), ('talento', 35200),
        ('sueldo', 1100), ('iota', 3520), ('drabin', 352), ('ardite', 32)
    ]
    remainder = cw_sell
    for coin_name, value in cw_denominations:
        if remainder >= value:
            result[coin_name] = remainder // value
            remainder %= value
        else:
            result[coin_name] = 0

    # --- Descomponer Imperial en denominaciones óptimas ---
    imp_denominations = [
        ('silver_penny', 100), ('copper_penny', 10),
        ('iron_penny', 2), ('iron_half_penny', 1)
    ]
    remainder = imp_sell
    for coin_name, value in imp_denominations:
        if remainder >= value:
            result[coin_name] = remainder // value
            remainder %= value
        else:
            result[coin_name] = 0

    return result


def add_wealth_from_dict(entity, wealth_dict):
    """Suma un diccionario de monedas a una entidad (Aventurero o Gremio) y consolida."""
    for coin, amount in wealth_dict.items():
        if amount > 0:
            setattr(entity, coin, getattr(entity, coin) + amount)
    entity.save()
    universal_consolidate(entity)


def get_imperial_value(entity):
    """Convierte toda la riqueza Imperial a Medios Peniques."""
    silver = getattr(entity, 'silver_penny', getattr(entity, 'cost_silver_penny', 0))
    copper = getattr(entity, 'copper_penny', getattr(entity, 'cost_copper_penny', 0))
    iron = getattr(entity, 'iron_penny', getattr(entity, 'cost_iron_penny', 0))
    half_iron = getattr(entity, 'iron_half_penny', getattr(entity, 'cost_iron_half_penny', 0))
    return (silver * 100) + (copper * 10) + (iron * 2) + half_iron


def get_commonwealth_value(entity):
    """Convierte toda la riqueza de la Mancomunidad a fracciones de Ardite (Base 32)."""
    marco = getattr(entity, 'marco', getattr(entity, 'cost_marco', 0))
    real = getattr(entity, 'real', getattr(entity, 'cost_real', 0))
    talento = getattr(entity, 'talento', getattr(entity, 'cost_talento', 0))
    sueldo = getattr(entity, 'sueldo', getattr(entity, 'cost_sueldo', 0))
    iota = getattr(entity, 'iota', getattr(entity, 'cost_iota', 0))
    drabin = getattr(entity, 'drabin', getattr(entity, 'cost_drabin', 0))
    ardite = getattr(entity, 'ardite', getattr(entity, 'cost_ardite', 0))

    val = 0
    val += marco * 352000
    val += real * 88000
    val += talento * 35200
    val += sueldo * 1100
    val += iota * 3520
    val += drabin * 352
    val += ardite * 32
    return val


def can_afford(adv, item):
    """Comprueba si el aventurero puede pagar el ítem."""
    if get_imperial_value(adv) < get_imperial_value(item):
        return False
    if get_commonwealth_value(adv) < get_commonwealth_value(item):
        return False
    return True


def pay_with_change(adv, item):
    """Paga el coste exacto rompiendo monedas grandes y calculando el vuelto."""
    # Every caller pairs this debit with a delivery (`_auto_equip`). Outside a transaction that
    # pair is two independent commits, and a failure between them charges for nothing delivered.
    # Today the only caller inherits atomicity from `process_session_completion`; this refuses to
    # let a future caller inherit nothing and find out in production. One guard in the shared
    # function, not a decorator on every call site.
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError(
            "pay_with_change debe correr dentro de transaction.atomic(): "
            "cobra antes de entregar, y sin transaccion el cobro sobrevive al fallo de la entrega.")
    if not can_afford(adv, item):
        return False

    # Pago Imperial
    rem_imp = get_imperial_value(adv) - get_imperial_value(item)
    adv.silver_penny = adv.copper_penny = adv.iron_penny = 0
    adv.iron_half_penny = rem_imp  # Dejamos todo en sencillo

    # Pago de la Mancomunidad
    rem_cw = get_commonwealth_value(adv) - get_commonwealth_value(item)
    adv.marco = adv.real = adv.talento = adv.sueldo = adv.iota = adv.drabin = 0
    adv.ardite = rem_cw // 32  # Dejamos todo en ardites
    
    # Mantenemos el residuo de la fracción de ardite pasándolo a la economía imperial
    adv.iron_half_penny += rem_cw % 32

    adv.save()
    # El motor re-ensambla las monedas automáticamente
    universal_consolidate(adv)
    return True


def consolidate_wealth(guild_id):
    """Wrapper para la API: Consolidar la bóveda del Gremio."""
    try:
        guild = GuildProfile.objects.get(id=guild_id)
        log_msgs = universal_consolidate(guild)
        return {
            "status": "success",
            "message": "Economía consolidada",
            "log": log_msgs if log_msgs else ["La bóveda ya está optimizada."]
        }
    except GuildProfile.DoesNotExist:
        return {"status": "error", "message": "Gremio no encontrado"}
