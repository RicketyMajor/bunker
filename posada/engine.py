import random
from .models import GuildProfile, Adventurer, DeepWorkSession, GuildProfile

XP_PER_MINUTE = 10
# Bono si la clase del aventurero hace sinergia con la tarea
XP_MULTIPLIER_CLASS_MATCH = 1.5


def calculate_loot(duration_minutes):
    """
    Calcula el botín basado en la duración de la sesión.
    Usa probabilidades (drop rates) que mejoran con el tiempo.
    """
    loot = {
        'iron_half_penny': 0, 'iron_penny': 0, 'ardite': 0, 'drabin': 0,
        'copper_penny': 0, 'iota': 0,
        'silver_penny': 0, 'sueldo': 0, 'talento': 0,
        'real': 0, 'marco': 0
    }

    # Por cada minuto de estudio, 1 a 3 ardites
    loot['ardite'] = sum(random.randint(1, 3) for _ in range(duration_minutes))

    # Recompensas de Cobre (Sesiones de más de 25 min)
    if duration_minutes >= 25:
        # Probabilidad de 1 iota por cada bloque de 25 mins
        blocks = duration_minutes // 25
        for _ in range(blocks):
            if random.random() < 0.60:  # 60% drop rate
                loot['iota'] += 1

    # Recompensas de Plata (Sesiones de Deep Work, > 50 min)
    if duration_minutes >= 50:
        blocks = duration_minutes // 50
        for _ in range(blocks):
            if random.random() < 0.30:  # 30% drop rate
                loot['sueldo'] += 1
            elif random.random() < 0.05:  # 5% drop rate de un Talento directo
                loot['talento'] += 1

    # Recompensas de Oro (Sesiones titánicas, > 120 min)
    if duration_minutes >= 120:
        if random.random() < 0.10:  # 10% drop rate
            loot['real'] += 1
        elif random.random() < 0.02:  # 2% drop rate mítico
            loot['marco'] += 1

    return loot


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


def market_phase(adventurers_qs, event_log):
    """
    Simula las decisiones de los aventureros en sus ratos libres.
    Revisan sus bolsillos y compran mejoras pasivas si tienen suficiente dinero.
    """
    for adv in adventurers_qs:
        # Tendencias de compra basadas en la clase
        is_martial = adv.adv_class in ['FTR', 'BBN', 'PAL', 'RGR']
        is_magic = adv.adv_class in ['WIZ', 'SOR', 'WLK', 'CLR', 'DRD']

        # ¿Tiene plata para comprar algo legendario?
        if adv.talento >= 1 or adv.sueldo >= 5:
            if is_martial:
                item = "Espada Larga Rúnica"
            else:
                item = "Tomo de Sabiduría Ancestral"

            # Paga el precio
            if adv.sueldo >= 5:
                adv.sueldo -= 5
            else:
                adv.talento -= 1

            event_log.append(
                f"Mercado: {adv.name} gastó plata en una reliquia: [{item}].")

        # ¿Tiene cobre para equipo decente?
        elif adv.iota >= 2 or adv.copper_penny >= 5:
            item = "Armadura de Malla" if is_martial else "Báculo de Roble"

            if adv.copper_penny >= 5:
                adv.copper_penny -= 5
            else:
                adv.iota -= 1

            event_log.append(
                f"Mercado: {adv.name} fue al herrero y compró: [{item}].")

        # Gasto de calderilla de hierro en consumibles o taberna
        elif adv.ardite >= 5:
            adv.ardite -= 5
            event_log.append(
                f"Mercado: {adv.name} gastó 5 ardites en raciones de viaje y pociones menores.")

        adv.save()


def process_session_completion(session_id):
    try:
        session = DeepWorkSession.objects.get(id=session_id)
    except DeepWorkSession.DoesNotExist:
        return {"status": "error", "message": "Sesión no encontrada"}

    if session.completed:
        return {"status": "warning", "message": "Esta sesión ya fue procesada"}

    guild, _ = GuildProfile.objects.get_or_create(id=1)
    event_log = []
    adventurers = session.adventurers_involved.all()

    # Calcular Botín General
    loot = calculate_loot(session.duration_minutes)

    # El Diezmo
    distribute_tithe(guild, adventurers, loot, event_log)

    # Fase de Mercado Autónomo
    market_phase(adventurers, event_log)

    # Experiencia (XP)
    base_xp = session.duration_minutes * 10
    guild.experience += base_xp
    event_log.append(f"El Gremio gana {base_xp} XP.")

    for adv in adventurers:
        adv.experience += base_xp
        adv.save()

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


def consolidate_wealth(guild_id):
    """
    Ejecuta las conversiones de la Mancomunidad de El Nombre del Viento.
    Procesa las monedas de menor valor y las empaqueta en divisas mayores.
    """
    try:
        guild = GuildProfile.objects.get(id=guild_id)
    except GuildProfile.DoesNotExist:
        return {"status": "error", "message": "Gremio no encontrado"}

    event_log = []

    # 11 Ardites = 1 Drabín
    if guild.ardite >= 11:
        new_drabines = guild.ardite // 11
        guild.ardite = guild.ardite % 11
        guild.drabin += new_drabines
        event_log.append(f"Se fundieron ardites en {new_drabines} Drabín(es).")

    # 10 Drabines = 1 Iota
    if guild.drabin >= 10:
        new_iotas = guild.drabin // 10
        guild.drabin = guild.drabin % 10
        guild.iota += new_iotas
        event_log.append(
            f"Se intercambiaron drabines por {new_iotas} Iota(s).")

    # 10 Iotas = 1 Talento
    if guild.iota >= 10:
        new_talentos = guild.iota // 10
        guild.iota = guild.iota % 10
        guild.talento += new_talentos
        event_log.append(
            f"Se consolidaron iotas en {new_talentos} Talento(s).")

    # 2 Medios peniques = 1 Penique de hierro
    if guild.iron_half_penny >= 2:
        new_iron = guild.iron_half_penny // 2
        guild.iron_half_penny = guild.iron_half_penny % 2
        guild.iron_penny += new_iron

    # 5 Peniques de hierro = 1 Penique de cobre
    if guild.iron_penny >= 5:
        new_copper = guild.iron_penny // 5
        guild.iron_penny = guild.iron_penny % 5
        guild.copper_penny += new_copper

    # 10 Peniques de cobre = 1 Penique de plata
    if guild.copper_penny >= 10:
        new_silver = guild.copper_penny // 10
        guild.copper_penny = guild.copper_penny % 10
        guild.silver_penny += new_silver

    # 32 Sueldos = 1 Talento
    if guild.sueldo >= 32:
        new_talentos_from_sueldo = guild.sueldo // 32
        guild.sueldo = guild.sueldo % 32
        guild.talento += new_talentos_from_sueldo
        event_log.append(
            f"Los sueldos se han convertido en {new_talentos_from_sueldo} Talento(s).")

    # 10 Talentos = 1 Marco
    if guild.talento >= 10:
        new_marcos = guild.talento // 10
        guild.talento = guild.talento % 10
        guild.marco += new_marcos
        event_log.append(f"¡Has acuñado {new_marcos} Marco(s) de Oro!")

    guild.save()

    return {
        "status": "success",
        "message": "Economía consolidada",
        "log": event_log
    }
