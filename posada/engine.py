import random
from django.db.models import Sum
from .models import GuildProfile, Adventurer, DeepWorkSession, Item

XP_PER_MINUTE = 10
# Bono si la clase del aventurero hace sinergia con la tarea
XP_MULTIPLIER_CLASS_MATCH = 1.5


def generate_session_script(session_id, duration_minutes, adventurers_qs):
    random.seed(session_id)
    script = []
    total_seconds = duration_minutes * 60
    adventurers = list(adventurers_qs)

    if not adventurers:
        random.seed()
        return script

    # Eventos de Botín Menor (Ardites)
    for m in range(duration_minutes):
        sec = (m * 60) + random.randint(5, 55)
        adv = random.choice(adventurers)

        # Aumenta la cantidad de ardites base
        weapon_bonus = adv.equipped_weapon.stat_modifier if adv.equipped_weapon else 0.0
        # Ej: stat 0.10 -> +1 ardite
        amount = random.randint(1, 3) + int(weapon_bonus * 10)

        script.append({
            "second": sec, "type": "loot", "coin": "ardite", "amount": amount,
            "message": f"{adv.name} ha encontrado {amount} ardite(s)."
        })

    # 2. Eventos de Botín Mayor (Cobre, Plata)
    if duration_minutes >= 25:
        blocks = duration_minutes // 25
        for i in range(blocks):
            adv = random.choice(adventurers)
            weapon_bonus = adv.equipped_weapon.stat_modifier if adv.equipped_weapon else 0.0

            # BONUS DE ARMA: Aumenta la probabilidad de drop (ej: 0.60 + 0.10 = 70%)
            if random.random() < (0.60 + weapon_bonus):
                sec = random.randint(i * 1500, (i+1) * 1500 - 1)
                script.append({
                    "second": sec, "type": "loot", "coin": "iota", "amount": 1,
                    "message": f"{adv.name} ha desenterrado 1 Iota brillante."
                })

    if duration_minutes >= 50:
        blocks = duration_minutes // 50
        for i in range(blocks):
            adv = random.choice(adventurers)
            weapon_bonus = adv.equipped_weapon.stat_modifier if adv.equipped_weapon else 0.0
            sec = random.randint(i * 3000, (i+1) * 3000 - 1)

            if random.random() < (0.30 + (weapon_bonus / 2)):
                script.append({"second": sec, "type": "loot", "coin": "sueldo",
                              "amount": 1, "message": f"{adv.name} encontró 1 Sueldo de plata."})
            elif random.random() < (0.05 + (weapon_bonus / 5)):
                script.append({"second": sec, "type": "loot", "coin": "talento",
                              "amount": 1, "message": f"¡UN TALENTO! {adv.name} ríe de alegría."})

    # Revisa el historial total de esfuerzo de tu Gremio
    total_history = DeepWorkSession.objects.filter(completed=True).aggregate(
        Sum('duration_minutes'))['duration_minutes__sum'] or 0

    # Si esta sesión hace que cruces un umbral de 10 horas (600 minutos), fuerza un Marco
    if (total_history % 600) + duration_minutes >= 600:
        adv = random.choice(adventurers)
        sec = random.randint(10, total_seconds - 10)
        script.append({"second": sec, "type": "loot", "coin": "marco", "amount": 1,
                      "message": f"¡GLORIA! La persistencia rinde frutos. {adv.name} ha desenterrado un MARCO DE ORO."})

    # Emboscadas (Riesgo de Enfermería)
    ambush_blocks = duration_minutes // 20
    for i in range(ambush_blocks):
        adv = random.choice(adventurers)
        # Reduce la probabilidad matemática de la emboscada
        armor_bonus = adv.equipped_armor.stat_modifier if adv.equipped_armor else 0.0
        ambush_chance = max(0.01, 0.25 - armor_bonus)

        if random.random() < ambush_chance:
            sec = random.randint(i * 1200, (i+1) * 1200 - 1)
            script.append({
                "second": sec, "type": "injury", "adventurer_id": adv.id,
                "message": f"¡EMBOSCADA! {adv.name} no pudo bloquear el golpe y está gravemente herido."
            })
        else:
            sec = random.randint(i * 1200, (i+1) * 1200 - 1)
            script.append({"second": sec, "type": "flavor",
                          "message": f"Una trampa saltó, pero la armadura de {adv.name} resistió el impacto perfectamente."})

    # 4. Eventos de Ambientación
    flavor_texts = [
        "{} revisa el mapa de la mazmorra con una antorcha.",
        "Se escucha un aullido a lo lejos. {} se pone en guardia.",
        "El silencio inunda la sala mientras {} lidera la marcha."
    ]
    flavor_count = duration_minutes // 10
    for _ in range(flavor_count):
        sec = random.randint(10, total_seconds - 10)
        adv = random.choice(adventurers)
        msg = random.choice(flavor_texts).format(adv.name)
        script.append(
            {"second": sec, "type": "flavor", "message": f"{msg}"})

    script.sort(key=lambda x: x["second"])
    random.seed()
    return script


def distribute_tithe(guild, adventurers_qs, loot_dict, event_log):
    """
    Divide el botín: 70% al Cofre del Gremio, 30% dividido entre los aventureros.
    """
    num_adventurers = adventurers_qs.count()
    if num_adventurers == 0:
        for coin, amount in loot_dict.items():
            setattr(guild, coin, getattr(guild, coin) + amount)
        event_log.append("El Gremio ha reclamado el 100% del botín.")
        return

    event_log.append(
        f"El Gremio retiene el 70% del botín. El 30% se divide entre {num_adventurers} aventureros.")

    for coin, amount in loot_dict.items():
        if amount == 0:
            continue

        guild_share = int(amount * 0.70)
        adventurer_pool = amount - guild_share

        # El gremio guarda su parte
        setattr(guild, coin, getattr(guild, coin) + guild_share)

        # Repartir el sobrante a los aventureros
        if adventurer_pool > 0:
            share_per_adv = adventurer_pool // num_adventurers
            remainder = adventurer_pool % num_adventurers

            for index, adv in enumerate(adventurers_qs):
                # El resto se lo lleva el primer aventurero
                extra = remainder if index == 0 else 0
                setattr(adv, coin, getattr(adv, coin) + share_per_adv + extra)
                adv.save()

            # El Gremio se queda con el pico si nadie puede dividirlo bien
            if share_per_adv == 0 and remainder > 0:
                setattr(guild, coin, getattr(guild, coin) + remainder)


def _seed_items_if_empty():
    """Si la armería está vacía, forjamos los primeros objetos base del juego."""
    if not Item.objects.exists():
        Item.objects.create(name="Espada Corta Oxidada", item_type='WPN',
                            rarity='COM', cost_in_copper=10, stat_modifier=0.05)
        Item.objects.create(name="Báculo de Roble", item_type='WPN',
                            rarity='COM', cost_in_copper=10, stat_modifier=0.05)
        Item.objects.create(name="Túnica de Aprendiz", item_type='AMR',
                            rarity='COM', cost_in_copper=10, stat_modifier=0.05)
        Item.objects.create(name="Cota de Malla", item_type='AMR',
                            rarity='UNC', cost_in_copper=50, stat_modifier=0.10)
        Item.objects.create(name="Amuleto del Búho", item_type='ACC',
                            rarity='RAR', cost_in_copper=100, stat_modifier=0.15)
        Item.objects.create(name="Excalibur", item_type='WPN',
                            rarity='LEG', cost_in_copper=1000, stat_modifier=0.30)


def _auto_equip(adv, item, event_log, pull_type):
    """Lógica de auto-equipamiento: Solo se equipa si es una mejora real (stat mayor)."""
    replaced = False
    old_item_name = None

    if item.item_type == 'WPN':
        if not adv.equipped_weapon or adv.equipped_weapon.stat_modifier < item.stat_modifier:
            old_item_name = adv.equipped_weapon.name if adv.equipped_weapon else None
            adv.equipped_weapon = item
            replaced = True
    elif item.item_type == 'AMR':
        if not adv.equipped_armor or adv.equipped_armor.stat_modifier < item.stat_modifier:
            old_item_name = adv.equipped_armor.name if adv.equipped_armor else None
            adv.equipped_armor = item
            replaced = True
    elif item.item_type == 'ACC':
        if not adv.equipped_accessory or adv.equipped_accessory.stat_modifier < item.stat_modifier:
            old_item_name = adv.equipped_accessory.name if adv.equipped_accessory else None
            adv.equipped_accessory = item
            replaced = True

    if replaced:
        if old_item_name:
            event_log.append(
                f"Gacha ({pull_type}): {adv.name} obtuvo [{item.name}] y descartó su viejo {old_item_name}.")
        else:
            event_log.append(
                f"Gacha ({pull_type}): {adv.name} obtuvo y equipó [{item.name}].")
    else:
        event_log.append(
            f"Gacha ({pull_type}): {adv.name} sacó [{item.name}] pero ya tenía algo mejor. Lo vendió por chatarra.")


def process_session_completion(session_id, survived_seconds=None):
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
    script = generate_session_script(
        session.id, session.duration_minutes, adventurers)

    loot = {
        'iron_half_penny': 0, 'iron_penny': 0, 'ardite': 0, 'drabin': 0,
        'copper_penny': 0, 'iota': 0,
        'silver_penny': 0, 'sueldo': 0, 'talento': 0,
        'real': 0, 'marco': 0
    }

    # Procesar eventos ocurridos dentro del tiempo sobrevivido
    injured_ids = set()
    for event in script:
        if event["second"] <= survived_seconds:
            if event["type"] == "loot":
                loot[event["coin"]] += event["amount"]
            elif event["type"] == "injury":
                injured_ids.add(event["adventurer_id"])

    # Aplicar heridas
    for adv in adventurers:
        if adv.id in injured_ids:
            adv.is_recovering = True
            adv.recovery_time_left = 120  # 2 horas de cooldown
            adv.save()
            event_log.append(
                f"{adv.name} fue enviado a la enfermería en camilla.")

    # El Diezmo
    distribute_tithe(guild, adventurers, loot, event_log)

    # Fase de Mercado Autónomo
    market_phase(adventurers, event_log)

    # Experiencia (XP) - basada en minutos sobrevividos reales
    survived_minutes = survived_seconds // 60
    if survived_minutes < 1:
        survived_minutes = 1

    base_xp = survived_minutes * XP_PER_MINUTE
    guild.experience += base_xp
    event_log.append(
        f"El Gremio gana {base_xp} XP base por sobrevivir {survived_minutes} min.")

    for adv in adventurers:
        # Multiplicador de experiencia personal
        acc_bonus = adv.equipped_accessory.stat_modifier if adv.equipped_accessory else 0.0
        adv_xp = int(base_xp * (1.0 + acc_bonus))

        adv.experience += adv_xp
        adv.save()

        if acc_bonus > 0:
            event_log.append(
                f"{adv.name} ganó {adv_xp} XP (Bonus de Accesorio).")

        # Verifica si sube de nivel tras ganar XP ---
        check_level_up(adv, event_log)

    guild.save()
    session.event_log = event_log
    session.completed = True
    session.save()

    return {
        "status": "success",
        "message": "Sesión completada y simulada.",
        "loot": loot,
        "base_xp": base_xp,
        "log": event_log
    }

# --- LÓGICA DE ESTADÍSTICAS Y NIVEL ---


def distribute_random_stats(adv, points_to_distribute):
    """Reparte una cantidad de puntos aleatoriamente entre los 7 atributos base."""
    stats = ['base_str', 'base_dex', 'base_con',
             'base_int', 'base_wis', 'base_cha', 'base_luk']
    for _ in range(points_to_distribute):
        stat = random.choice(stats)
        current_val = getattr(adv, stat)
        setattr(adv, stat, current_val + 1)
    adv.save()


def check_level_up(adv, event_log):
    """Comprueba si el aventurero tiene suficiente XP para subir de nivel."""
    xp_needed = adv.level * 100  # Escala simple: Nv 1->2 pide 100XP, Nv 2->3 pide 200XP

    if adv.experience >= xp_needed:
        adv.level += 1
        adv.experience -= xp_needed
        adv.max_hp += 2
        adv.current_hp = adv.max_hp  # Cura completa al subir de nivel

        distribute_random_stats(adv, 3)  # +3 puntos aleatorios

        event_log.append(
            f"¡Sube de Nivel! {adv.name} alcanza el Nivel {adv.level} (+2 HP, +3 Stats).")

        # Llamada recursiva por si ganó muchísima XP de golpe
        check_level_up(adv, event_log)

# --- LÓGICA BANCARIA Y MERCADO ---


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


def pay_with_change(adv, cost_in_copper):
    """Intenta pagar un coste dando cambio si es necesario."""
    total_value_in_half_pennies = (
        adv.copper_penny * 10) + (adv.iron_penny * 2) + adv.iron_half_penny
    cost_in_half_pennies = cost_in_copper * 2

    if total_value_in_half_pennies < cost_in_half_pennies:
        return False

    remaining = total_value_in_half_pennies - cost_in_half_pennies

    adv.copper_penny = remaining // 10
    remaining %= 10
    adv.iron_penny = remaining // 2
    adv.iron_half_penny = remaining % 2
    adv.save()
    return True


def market_phase(adventurers_qs, event_log):
    """Simula las compras automáticas de los aventureros."""
    _seed_items_if_empty()
    all_items = list(Item.objects.all())

    for adv in adventurers_qs:
        universal_consolidate(adv)  # Consolidan su propia billetera primero

        if adv.is_recovering:
            continue

        if adv.silver_penny >= 1:
            adv.silver_penny -= 1
            pool = [i for i in all_items if i.rarity in ['RAR', 'EPC', 'LEG']]
            if not pool:
                pool = all_items
            item = random.choice(pool)
            _auto_equip(adv, item, event_log, "Premium")

        elif adv.copper_penny >= 10:
            item = random.choice(
                [i for i in all_items if i.cost_in_copper <= 10])
            # Compran solo si pueden pagar y recibir vuelto exacto
            if pay_with_change(adv, item.cost_in_copper):
                _auto_equip(adv, item, event_log, "Común")


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
