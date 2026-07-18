import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from posada.models import GuildProfile, Adventurer, DeepWorkSession, Item, DailyHabit, DailyStatistic, InventorySlot, Monster, ItemRarity, CustomChart, ChartDataPoint, GuildUpgrade, JournalEntry, CalendarEvent
from posada.skills import SkillRegistry

COIN_COLORS = {
    'iron_half_penny': '#8b5a2b',
    'iron_penny': '#8b5a2b',
    'copper_penny': '#cd7f32',
    'ardite': '#b87333',
    'silver_penny': '#c0c0c0',
    'drabin': '#d3d3d3',
    'sueldo': '#e5e4e2',
    'iota': '#87ceeb',
    'talento': '#4682b4',
    'real': '#4169e1',
    'marco': '#ffd700'
}

MONSTER_COLORS = {
    'SML': 'dim white',
    'MED': '#4169e1',
    'LRG': '#8a2be2',
    'EPC': 'bold red'
}


def safe_randint(a, b):
    """randint seguro que no falla si los rangos están invertidos."""
    return random.randint(min(a, b), max(a, b))

XP_PER_MINUTE = 10
# Bono si la clase del aventurero hace sinergia con la tarea
XP_MULTIPLIER_CLASS_MATCH = 1.5

# --- SINERGIAS DE CATEGORÍA ---
# Si la tarea escrita en la TUI coincide con una clave, las clases listadas ganan +50% XP
CATEGORY_SYNERGY = {
    "programacion": ["WIZ", "ART"],
    "sistemas distribuidos": ["ART", "WIZ", "SOR"],
    "telecomunicaciones": ["ART", "BRD"],
    "codigo": ["WIZ", "ART"],
    "gimnasio": ["BBN", "FTR", "MNK"],
    "ejercicio": ["BBN", "FTR", "MNK"],
    "ingles": ["BRD", "SOR", "WLK"],
    "idiomas": ["BRD", "SOR", "WLK"],
    "estudio": ["CLR", "PAL", "WIZ"],
    "lectura": ["WIZ", "BRD", "CLR"],
    "matematicas": ["ART", "WIZ"],
    "ayudantia": ["BRD", "CLR", "PAL"]
}

FLAVOR_MONSTER = {
    'SML': [
        "ríe maliciosamente en la penumbra.",
        "se escabulle entre las sombras rápidamente.",
        "emite un chillido agudo y molesto.",
        "clava sus uñas en la tierra, listo para abalanzarse.",
        "te lanza una mirada furtiva, buscando un punto débil.",
        "se ríe a carcajadas con una voz rasposa.",
        "babosea el suelo, mostrando sus dientes afilados.",
        "salta nerviosamente de un pie al otro.",
        "desaparece un instante y reaparece desde otro ángulo.",
        "enseña los dientes y gruñe como un perro rabioso.",
    ],
    'MED': [
        "gruñe mostrando los colmillos.",
        "golpea su arma contra el suelo amenazantemente.",
        "te observa con ojos sedientos de sangre.",
        "lanza un alarido de guerra que hiela la sangre.",
        "se golpea el pecho en señal de desafío.",
        "analiza tus movimientos, ajustando su postura de combate.",
        "escupe al suelo con desprecio.",
        "blande su arma dibujando un círculo mortal en el aire.",
        "maldice en una lengua incomprensible.",
        "acorta la distancia con pasos pesados y decididos.",
    ],
    'LRG': [
        "suelta un rugido que hace temblar la sala.",
        "toma aire pesadamente, preparándose para aplastar.",
        "destroza parte del escenario con su tamaño.",
        "sacude la cabeza, rompiendo pilares cercanos.",
        "suelta un resoplido que levanta nubes de polvo.",
        "te observa desde arriba con absoluto desdén.",
        "carga con todo su peso, haciendo vibrar el suelo.",
        "barre todo a su alrededor con un movimiento colosal.",
        "rompe la roca bajo sus pies al prepararse para atacar.",
        "proyecta una sombra gigantesca que oscurece el lugar.",
    ],
    'EPC': [
        "irradia un aura de terror insoportable.",
        "te mira como si fueras un simple insecto.",
        "levita levemente mientras el aire se distorsiona.",
        "hace que la realidad misma parezca resquebrajarse a su alrededor.",
        "habla directamente en tu mente con una voz atronadora.",
        "desvía la luz a su alrededor, creando un aura de oscuridad absoluta.",
        "hace que el tiempo parezca detenerse por un microsegundo.",
        "exhala magia pura que calcina las paredes de la habitación.",
        "te condena a la perdición con un simple ademán de su mano.",
        "invoca la furia de fuerzas antiguas e incomprensibles.",
    ]
}

# --- MAPEO DE HABILIDADES D&D 5E ---
SKILL_STAT_MAP = {
    "Acrobacias": "dex", "Atletismo": "str", "Arcano": "int", "Engaño": "cha",
    "Historia": "int", "Perspicacia": "wis", "Intimidación": "cha", "Investigación": "int",
    "Medicina": "wis", "Naturaleza": "wis", "Percepción": "wis", "Interpretación": "cha",
    "Persuasión": "cha", "Religión": "int", "Juego de Manos": "dex", "Sigilo": "dex",
    "Supervivencia": "wis", "Trato con Animales": "wis"
}

CLASS_SKILL_PROFICIENCIES = {
    'ART': ['Arcano', 'Historia', 'Investigación', 'Medicina', 'Naturaleza'],
    'BBN': ['Trato con Animales', 'Atletismo', 'Intimidación', 'Naturaleza', 'Percepción', 'Supervivencia'],
    'BRD': ['Acrobacias', 'Arcano', 'Engaño', 'Historia', 'Interpretación', 'Persuasión', 'Juego de Manos', 'Sigilo'],
    'CLR': ['Historia', 'Perspicacia', 'Medicina', 'Persuasión', 'Religión'],
    'DRD': ['Arcano', 'Trato con Animales', 'Perspicacia', 'Medicina', 'Naturaleza', 'Percepción', 'Religión', 'Supervivencia'],
    'FTR': ['Acrobacias', 'Trato con Animales', 'Atletismo', 'Historia', 'Perspicacia', 'Intimidación', 'Percepción', 'Supervivencia'],
    'MNK': ['Acrobacias', 'Atletismo', 'Historia', 'Perspicacia', 'Religión', 'Sigilo'],
    'PAL': ['Atletismo', 'Perspicacia', 'Intimidación', 'Medicina', 'Persuasión', 'Religión'],
    'RGR': ['Trato con Animales', 'Atletismo', 'Perspicacia', 'Investigación', 'Naturaleza', 'Percepción', 'Sigilo', 'Supervivencia'],
    'ROG': ['Acrobacias', 'Atletismo', 'Engaño', 'Perspicacia', 'Intimidación', 'Investigación', 'Percepción', 'Interpretación', 'Persuasión', 'Juego de Manos', 'Sigilo'],
    'SOR': ['Arcano', 'Engaño', 'Perspicacia', 'Intimidación', 'Persuasión', 'Religión'],
    'WLK': ['Arcano', 'Engaño', 'Historia', 'Intimidación', 'Investigación', 'Naturaleza', 'Religión'],
    'WIZ': ['Arcano', 'Historia', 'Perspicacia', 'Investigación', 'Medicina', 'Religión']
}


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


FLAVOR_ADV = [
    "toma firmemente su arma, listo para cualquier cosa.",
    "se limpia el sudor de la frente sin apartar la mirada.",
    "calcula la distancia exacta entre él y el enemigo.",
    "murmura una pequeña plegaria al destino.",
    "adopta una postura defensiva, esperando el impacto.",
    "hace crujir sus nudillos con una sonrisa confiada.",
    "agudiza la vista, buscando huecos en la armadura rival.",
    "ajusta las correas de su armadura apresuradamente.",
    "exhala largamente para calmar los latidos de su corazón.",
    "se pasa la lengua por los labios secos, tenso.",
    "brinda una mirada desafiante a su oponente.",
    "murmura insultos entre dientes hacia los monstruos.",
    "revisa el filo de su arma con el pulgar.",
    "hace un gesto provocador para atraer la atención del rival.",
    "susurra palabras mágicas para darse valor.",
    "siente la adrenalina corriendo por sus venas a gran velocidad.",
    "evalúa a sus compañeros, cerciorándose de que estén listos.",
]


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


def calculate_save_dc(adv):
    mods = adv.get_stat_modifiers()
    spellcasting_stat = {'WIZ': 'int', 'ART': 'int', 'CLR': 'wis', 'DRD': 'wis', 'RGR': 'wis',
                         'BRD': 'cha', 'PAL': 'cha', 'SOR': 'cha', 'WLK': 'cha'}.get(adv.adv_class, 'int')
    spellcasting_mod = mods.get(spellcasting_stat, 0)
    prof_bonus = 2 + ((adv.level - 1) // 4)
    return 6 + spellcasting_mod + prof_bonus  # CA Base de Hechizos bajada a 6



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
            g_slot, _ = InventorySlot.objects.get_or_create(
                guild=guild, item=item, adventurer=None, defaults={'quantity': 0})
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


def evaluate_daily_penalties():
    """Resta prestigio por pereza o PREMIA por evitar malos hábitos.
    
    Usa `last_evaluated_date` como marcador de la última fecha procesada.
    `last_completed_date` queda exclusivamente para acciones del usuario.
    """
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    habits = DailyHabit.objects.all()
    guild, _ = GuildProfile.objects.get_or_create(id=1)

    total_prestige_change = 0
    penalty_log = []

    for habit in habits:
        # El marcador de evaluación indica hasta qué fecha ya se procesó
        eval_ref = habit.last_evaluated_date if habit.last_evaluated_date else habit.created_at
        eval_delta = (today - eval_ref).days

        if eval_delta < 1:
            continue  # Ya evaluado hoy, nada que hacer

        if habit.is_bad_habit:
            # --- MALOS HÁBITOS: Recompensar por cada día válido sobrevivido ---
            # Verificar cada día desde eval_ref+1 hasta ayer (inclusive).
            # Si el usuario recayó en alguno de esos días (last_completed_date cae en el rango),
            # los días DESPUÉS de la recaída no cuentan.
            relapse_date = habit.last_completed_date  # None si nunca recayó

            survived_valid_days = 0
            check_date = eval_ref + timedelta(days=1)
            while check_date <= yesterday:
                if relapse_date and check_date == relapse_date:
                    # Recayó este día. No hay recompensa y la racha se reinicia.
                    habit.current_streak = 0
                elif str(check_date.weekday()) in habit.valid_days:
                    survived_valid_days += 1
                    habit.current_streak += 1
                check_date += timedelta(days=1)

            if survived_valid_days > 0:
                reward_map = {'S': 50, 'A': 25, 'B': 10, 'C': 5}
                prestige_gain = reward_map.get(
                    habit.difficulty, 5) * survived_valid_days
                total_prestige_change += prestige_gain
                penalty_log.append(
                    f"Evitaste '{habit.name}' por {survived_valid_days} día(s) (+{prestige_gain} Prestigio).")

            # Avanza el marcador de evaluación a ayer
            habit.last_evaluated_date = yesterday
            habit.save()

        else:
            # --- BUENOS HÁBITOS: Penalizar por días válidos no completados ---
            # Solo penalizar si hay días no cubiertos entre la última evaluación y hoy.
            # La referencia real es el máximo entre last_evaluated_date y last_completed_date,
            # ya que completar un hábito "cubre" ese día.
            completed_ref = habit.last_completed_date or habit.created_at
            ref_date = max(eval_ref, completed_ref)
            delta = (today - ref_date).days

            if delta > 1:
                missed_valid_days = 0
                for i in range(1, delta):
                    check_date = ref_date + timedelta(days=i)
                    if str(check_date.weekday()) in habit.valid_days:
                        missed_valid_days += 1

                if missed_valid_days > 0:
                    prestige_loss = missed_valid_days * 15
                    total_prestige_change -= prestige_loss
                    habit.current_streak = 0
                    
                    coin_hierarchy = [
                        'marco', 'real', 'talento', 'iota', 'sueldo', 'drabin', 
                        'silver_penny', 'ardite', 'copper_penny', 'iron_penny', 'iron_half_penny'
                    ]
                    
                    coins_lost = []
                    for _ in range(missed_valid_days):
                        for coin in coin_hierarchy:
                            if getattr(guild, coin) > 0:
                                setattr(guild, coin, getattr(guild, coin) - 1)
                                coins_lost.append(coin)
                                break
                    
                    if coins_lost:
                        from collections import Counter
                        lost_counts = Counter(coins_lost)
                        lost_str = ", ".join(f"{count} {c.replace('_', ' ').title()}" for c, count in lost_counts.items())
                        penalty_log.append(
                            f"Hábito roto: '{habit.name}' (-{prestige_loss} Prestigio, -{lost_str}).")
                    else:
                        penalty_log.append(
                            f"Hábito roto: '{habit.name}' (-{prestige_loss} Prestigio).")

            habit.last_evaluated_date = yesterday
            habit.save()

    # --- EVALUACIÓN DEL CALENDARIO DE EVENTOS ---
    events = CalendarEvent.objects.filter(status__in=['PENDING', 'TODAY'])
    for event in events:
        if event.date == today and event.status == 'PENDING':
            event.status = 'TODAY'
            event.save()
            penalty_log.append(f"📅 El evento '{event.title}' es HOY.")
        elif event.date < today:
            event.status = 'DONE'
            event.save()
            
            # Dynamic rewards
            prestige_gain = random.randint(5, 15)
            coins = ['iron_penny', 'iron_half_penny', 'copper_penny']
            reward_coin = random.choice(coins)
            reward_amt = random.randint(1, 10)
            
            total_prestige_change += prestige_gain
            setattr(guild, reward_coin, getattr(guild, reward_coin) + reward_amt)
            penalty_log.append(
                f"✅ Evento completado: '{event.title}' (+{prestige_gain} Prestigio, +{reward_amt} {reward_coin.replace('_', ' ').title()})."
            )


    if total_prestige_change != 0:
        guild.add_prestige(total_prestige_change)
        
        if total_prestige_change < 0:
            penalty_log.append(
                f"El Gremio pierde influencia. (Impacto Neto: {total_prestige_change})")

    return penalty_log


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
            guild.add_prestige(10)
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


# --- REGLAS MAESTRAS DE CLASE ---
CLASS_PROFICIENCIES = {
    'ART': {'armor': ['NON', 'LGT', 'MED'], 'weapons': ['SLS', 'PRC', 'BLD', 'MAG'], 'forbidden_materials': []},
    'BBN': {'armor': ['NON', 'LGT', 'MED'], 'weapons': ['SLS', 'PRC', 'BLD'], 'forbidden_materials': []},
    'BRD': {'armor': ['NON', 'LGT'], 'weapons': ['SLS', 'PRC', 'MAG'], 'forbidden_materials': []},
    # Clérigos no usan filos
    'CLR': {'armor': ['NON', 'LGT', 'MED'], 'weapons': ['BLD', 'MAG'], 'forbidden_materials': ['SLS', 'PRC']},
    # Druidas no usan metal
    'DRD': {'armor': ['NON', 'LGT', 'MED'], 'weapons': ['BLD', 'PRC', 'MAG'], 'forbidden_materials': ['MTL']},
    'FTR': {'armor': ['NON', 'LGT', 'MED', 'HVY'], 'weapons': ['SLS', 'PRC', 'BLD'], 'forbidden_materials': []},
    # Monjes no usan armadura
    'MNK': {'armor': ['NON'], 'weapons': ['BLD', 'PRC'], 'forbidden_materials': []},
    'PAL': {'armor': ['NON', 'LGT', 'MED', 'HVY'], 'weapons': ['SLS', 'PRC', 'BLD'], 'forbidden_materials': []},
    'RGR': {'armor': ['NON', 'LGT', 'MED'], 'weapons': ['SLS', 'PRC', 'BLD'], 'forbidden_materials': []},
    'ROG': {'armor': ['NON', 'LGT'], 'weapons': ['SLS', 'PRC'], 'forbidden_materials': []},
    'SOR': {'armor': ['NON'], 'weapons': ['MAG', 'BLD'], 'forbidden_materials': []},
    'WLK': {'armor': ['NON', 'LGT'], 'weapons': ['MAG', 'BLD', 'SLS'], 'forbidden_materials': []},
    'WIZ': {'armor': ['NON'], 'weapons': ['MAG', 'BLD'], 'forbidden_materials': []},
}


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


def get_chart_completion_status(chart):
    """Analiza el progreso de un gráfico: qué puntos enteros del eje X están cubiertos y cuáles faltan."""
    x_start = int(chart.x_min)
    x_end = int(chart.goal_x_value)
    expected = set(range(x_start, x_end + 1))

    points = chart.data_points.all().order_by('x_value')
    covered = set()
    for p in points:
        int_x = int(p.x_value)
        if int_x in expected:
            covered.add(int_x)

    missing = sorted(expected - covered)
    return {
        "total_expected": len(expected),
        "covered_count": len(covered),
        "covered": sorted(covered),
        "missing": missing,
        "is_complete": len(missing) == 0
    }


def calculate_chart_reward(chart):
    """Calcula el Área bajo la curva usando proporciones sobre el área total del lienzo."""
    points = list(chart.data_points.all().order_by('x_value'))
    if not points:
        return {"status": "error", "message": "El gráfico está vacío."}

    # Verificar que TODOS los enteros del rango estén cubiertos
    completion = get_chart_completion_status(chart)
    if not completion["is_complete"]:
        missing_str = ", ".join(str(d) for d in completion["missing"][:10])
        suffix = f" (y {len(completion['missing']) - 10} más)" if len(completion["missing"]) > 10 else ""
        return {
            "status": "warning",
            "message": f"Faltan {len(completion['missing'])} puntos: {missing_str}{suffix}. Progreso: {completion['covered_count']}/{completion['total_expected']}."
        }

    # Área máxima teórica del rectángulo del gráfico
    total_area = (chart.goal_x_value - chart.x_min) * \
        (chart.y_max - chart.y_min)
    if total_area <= 0:
        total_area = 1.0  # Evita división por cero

    # Cálculo del área real del usuario, Suma de Riemann trapezoidal
    area = 0
    for i in range(1, len(points)):
        dx = points[i].x_value - points[i-1].x_value
        # La altura se mide desde el "suelo" del gráfico (y_min)
        h1 = max(0.0, points[i-1].y_value - chart.y_min)
        h2 = max(0.0, points[i].y_value - chart.y_min)
        dy = (h1 + h2) / 2.0
        area += dx * dy

    rendimiento = area / total_area

    # Evaluación del Rango basado en Porcentajes
    grade = 'C'
    if chart.polarity == 'POS':
        if rendimiento >= 0.80:
            grade = 'S'     # se llenó el 80% o más del gráfico
        elif rendimiento >= 0.50:
            grade = 'A'   # se llenó el 50% o más
        elif rendimiento >= 0.25:
            grade = 'B'
    else:  # Gráficos Negativos
        if rendimiento <= 0.20:
            grade = 'S'     # se llenó un 20% o menos
        elif rendimiento <= 0.50:
            grade = 'A'
        elif rendimiento <= 0.75:
            grade = 'B'

    # --- Recompensas de Gráfico ---
    guild, _ = GuildProfile.objects.get_or_create(id=1)

    # Recompensa base por duración
    base_prestige = chart.goal_x_value * 15
    prestige_reward = {
        'S': base_prestige * 2,
        'A': base_prestige,
        'B': int(base_prestige * 0.5),
        'C': int(base_prestige * 0.2)
    }[grade]

    # Monedas dinámicas según duración de la meta
    if chart.goal_x_value >= 30:
        coin_reward = {'S': ('marco', 2), 'A': ('marco', 1), 'B': ('talento', 2), 'C': ('real', 1)}[grade]
    else:
        coin_reward = {'S': ('talento', 1), 'A': ('real', 2), 'B': ('sueldo', 5), 'C': ('sueldo', 1)}[grade]

    leveled_up = guild.add_prestige(prestige_reward)
    setattr(guild, coin_reward[0], getattr(guild, coin_reward[0]) + coin_reward[1])
    guild.save()
    universal_consolidate(guild)

    # --- Drops de Cofre por Gráfico ---
    import random
    from posada.models import Item, InventorySlot, ItemRarity
    
    rarity = 'COM'
    if grade == 'S':
        rarity = 'LEG' if random.random() < 0.2 else 'EPC'
    elif grade == 'A':
        rarity = 'RAR'
    elif grade == 'B':
        rarity = 'UNC'
        
    pool = Item.objects.filter(rarity=rarity)
    if not pool.exists() and rarity in ['EPC', 'LEG']:
        pool = Item.objects.filter(rarity='RAR')
        
    drop_msg = ""
    if pool.exists():
        drop = random.choice(pool)
        g_slot, _ = InventorySlot.objects.get_or_create(guild=guild, item=drop, adventurer=None, defaults={'quantity': 0})
        g_slot.quantity += 1
        g_slot.save()
        color = ItemRarity.get_color(drop.rarity)
        drop_msg = f"\n🎁 Además, encontraste un cofre: [[{color}]{drop.name}[/]]."

    chart.data_points.all().delete()  # Reinicia el gráfico

    return {
        "status": "success",
        "grade": grade,
        "rendimiento": round(rendimiento * 100, 1),
        "prestige_reward": prestige_reward,
        "coin_type": coin_reward[0].title(),
        "coin_amount": coin_reward[1],
        "message": f"¡Ciclo completado! Rango {grade} ({rendimiento*100:.1f}% del área). Gremio gana +{prestige_reward} Prestigio y {coin_reward[1]} {coin_reward[0].title()}.{drop_msg}"
    }
