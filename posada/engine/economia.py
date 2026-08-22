"""Wealth: consolidation, valuation, and paying with change.

Moved out of `legacy.py` unchanged (Phase 3, Task 4). `pay_with_change` keeps the Phase 2 guard
that refuses to run outside `transaction.atomic()`, and its comment, because the guard is the
invariant `tests/test_posada_invariantes.py` plants against.
"""
import random

from django.db import transaction

from posada.models import GuildProfile
from posada.engine.data.tablas import MANCOMUNIDAD, IMPERIAL

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

    Convierte todo el coste del item a unidades base, aplica el porcentaje, y redistribuye en
    denominaciones optimas.

    Las tablas vienen de `data/tablas.py` ordenadas de mayor a menor, y ese orden es lo que hace
    correcta la descomposicion: la lista que vivia aqui tenia sueldo (1100) ANTES que iota
    (3520), asi que vender 4 iotas devolvia 12 sueldos + 2 drabines + 5 ardites — las
    denominaciones equivocadas y 16 unidades base DESTRUIDAS bajo la moneda minima.

    Returns:
        dict con las 11 monedas y sus cantidades resultantes.
    """
    def _descomponer(entity, tabla):
        resto = int(_en_base(entity, tabla) * pct)
        salida = {}
        for moneda, valor in tabla.items():
            salida[moneda], resto = divmod(resto, valor)
        return salida

    return {**_descomponer(item, MANCOMUNIDAD), **_descomponer(item, IMPERIAL)}


def add_wealth_from_dict(entity, wealth_dict):
    """Suma un diccionario de monedas a una entidad (Aventurero o Gremio) y consolida."""
    for coin, amount in wealth_dict.items():
        if amount > 0:
            setattr(entity, coin, getattr(entity, coin) + amount)
    entity.save()
    universal_consolidate(entity)


def _en_base(entity, tabla):
    """Total value of `entity` in base units, per `tabla`.

    `entity` is either a wealth holder (Aventurero/Gremio, fields `marco`) or an Item (fields
    `cost_marco`). Both shapes were already handled by the getattr chains this replaces.
    """
    return sum(getattr(entity, moneda, getattr(entity, f'cost_{moneda}', 0)) * valor
               for moneda, valor in tabla.items())


def get_imperial_value(entity):
    """Convierte toda la riqueza Imperial a Medios Peniques."""
    return _en_base(entity, IMPERIAL)


def get_commonwealth_value(entity):
    """Convierte toda la riqueza de la Mancomunidad a fracciones de Ardite (Base 32)."""
    return _en_base(entity, MANCOMUNIDAD)


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
