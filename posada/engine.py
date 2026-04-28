import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .models import GuildProfile, Adventurer, DeepWorkSession, Item, DailyHabit, DailyStatistic, InventorySlot, Monster

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
    'SML': ["ríe maliciosamente en la penumbra.", "se escabulle entre las sombras rápidamente.", "emite un chillido agudo y molesto."],
    'MED': ["gruñe mostrando los colmillos.", "golpea su arma contra el suelo amenazantemente.", "te observa con ojos sedientos de sangre."],
    'LRG': ["suelta un rugido que hace temblar la sala.", "toma aire pesadamente, preparándose para aplastar.", "destroza parte del escenario con su tamaño."],
    'EPC': ["irradia un aura de terror insoportable.", "te mira como si fueras un simple insecto.", "levita levemente mientras el aire se distorsiona."]
}

FLAVOR_ADV = [
    "toma firmemente su arma, listo para cualquier cosa.",
    "se limpia el sudor de la frente sin apartar la mirada.",
    "calcula la distancia exacta entre él y el enemigo.",
    "murmura una pequeña plegaria al destino.",
    "adopta una postura defensiva, esperando el impacto.",
    "hace crujir sus nudillos con una sonrisa confiada."
]


def generate_session_script(session_id, duration_minutes, adventurers_qs):
    random.seed(session_id)
    script = []
    total_seconds = duration_minutes * 60
    adventurers = list(adventurers_qs)

    if not adventurers:
        random.seed()
        return script

    monsters_db = list(Monster.objects.all())
    all_items_db = list(Item.objects.all())

    state = "EXPLORING"
    current_second = 0
    active_monsters_group = []  # Lista para manejar a los grupos

    # --- Tablas de Botín por Categoría ---
    # (moneda, cant_max, probabilidad)
    coin_drops = {
        'SML': [('iron_penny', 5, 0.8), ('ardite', 3, 0.5), ('copper_penny', 1, 0.1)],
        'MED': [('copper_penny', 5, 0.8), ('drabin', 3, 0.5), ('silver_penny', 1, 0.2)],
        'LRG': [('silver_penny', 6, 0.9), ('sueldo', 2, 0.6), ('talento', 1, 0.1)],
        'EPC': [('sueldo', 5, 1.0), ('talento', 3, 0.8), ('real', 1, 0.3), ('marco', 1, 0.05)]
    }
    # (rareza, prob_base) -> luk_bonus sube la prob
    item_drops = {
        'SML': [('COM', 0.05), ('UNC', 0.01)],
        'MED': [('UNC', 0.10), ('RAR', 0.02)],
        'LRG': [('RAR', 0.15), ('EPC', 0.05)],
        'EPC': [('EPC', 0.25), ('LEG', 0.10)]
    }

    def get_adv_for_item(item):
        """Busca quién necesita más el ítem o puede usarlo."""
        if item.item_type == 'MSC':
            return random.choice(adventurers)
        valid_advs = [a for a in adventurers if is_class_allowed(a, item)]
        if not valid_advs:
            return random.choice(adventurers)
        # El que tenga menos items equipados tiene prioridad
        valid_advs.sort(key=lambda a: len(a.get_equipped_items()))
        return valid_advs[0]

    while current_second < total_seconds:
        if state == "EXPLORING":
            current_second += 60
            if current_second >= total_seconds:
                break

            adv = random.choice(adventurers)
            luk_bonus = adv.base_luk + \
                sum(item.bonus_luk for item in adv.get_equipped_items())

            # Tirada de Encuentro
            if monsters_db and random.random() < 0.15:
                base_monster = random.choice(monsters_db)
                spawn_count = random.randint(
                    base_monster.min_spawn, base_monster.max_spawn)

                # Genera cada individuo del grupo
                for i in range(spawn_count):
                    pts_map = {'SML': 15, 'MED': 25, 'LRG': 45, 'EPC': 65}
                    pts = pts_map.get(base_monster.category, 15)
                    m_stats = {'str': 0, 'dex': 0, 'con': 0,
                               'int': 0, 'wis': 0, 'cha': 0, 'luk': 0}
                    keys = list(m_stats.keys())
                    for _ in range(pts):
                        m_stats[random.choice(keys)] += 1

                    hp = base_monster.base_hp + (m_stats['con'] * 2)
                    name = f"{base_monster.name} {'ABCDEF'[i]}" if spawn_count > 1 else base_monster.name

                    active_monsters_group.append({
                        'name': name, 'hp': hp, 'stats': m_stats, 'base': base_monster
                    })

                msg = f"¡EMBOSCADA! Un grupo de {spawn_count} [bold red]{base_monster.name}s[/bold red] corta el paso." if spawn_count > 1 else f"¡PELIGRO! Un [bold red]{base_monster.name}[/bold red] bloquea el camino."
                script.append({"second": current_second,
                              "type": "flavor", "message": msg})
                state = "COMBAT"
                continue

            # Exploración (Botín)
            hp_amount = random.randint(2, 5) + luk_bonus
            script.append({"second": current_second - 30, "type": "loot", "coin": "iron_half_penny",
                          "amount": hp_amount, "message": f"{adv.name} recogió {hp_amount} medio(s) penique(s) de hierro."})
            if random.random() < (0.30 + (luk_bonus * 0.02)):
                script.append({"second": current_second - 15, "type": "loot", "coin": "drabin",
                              "amount": 1, "message": f"{adv.name} desenterró 1 Drabín."})

        elif state == "COMBAT":
            current_second += 15
            if current_second >= total_seconds:
                break

            # --- INMERSIÓN (1 por ronda) ---
            if random.random() < 0.5:  # 50% aventurero, 50% monstruo
                f_adv = random.choice(adventurers)
                script.append({"second": current_second - 12, "type": "flavor",
                              "message": f"{f_adv.name} {random.choice(FLAVOR_ADV)}"})
            else:
                f_mon = random.choice(active_monsters_group)
                flav = random.choice(FLAVOR_MONSTER.get(
                    f_mon['base'].category, FLAVOR_MONSTER['SML']))
                script.append({"second": current_second - 12, "type": "flavor",
                              "message": f"El [bold red]{f_mon['name']}[/bold red] {flav}"})

            # --- TURNO DE LOS MONSTRUOS ---
            for m in active_monsters_group:
                target = random.choice(adventurers)
                adv_mods = target.get_stat_modifiers()
                m_roll = random.randint(1, 20) + m['stats']['dex']
                adv_evasion = 10 + adv_mods['dex']

                if m_roll >= adv_evasion:
                    base_m = m['base']
                    m_dmg_dice = sum(random.randint(1, base_m.damage_dice_sides)
                                     for _ in range(base_m.damage_dice_count))
                    m_dmg = m_dmg_dice + \
                        base_m.bonus_damage + m['stats']['str']
                    final_dmg = max(1, m_dmg - adv_mods['armor'])
                    script.append({"second": current_second - 8, "type": "damage", "adventurer_id": target.id, "amount": final_dmg,
                                  "message": f"[bold red]{m['name']}[/bold red] golpea a {target.name} ({final_dmg} daño)."})
                else:
                    script.append({"second": current_second - 8, "type": "flavor",
                                  "message": f"{target.name} esquivó el ataque de [bold red]{m['name']}[/bold red]."})

            # --- TURNO DE LOS AVENTUREROS ---
            for i, adv in enumerate(adventurers):
                if not active_monsters_group:
                    break  # Si murieron todos, paran de atacar

                target_m = random.choice(active_monsters_group)
                adv_mods = adv.get_stat_modifiers()
                a_roll = random.randint(1, 20) + adv_mods['dex']
                m_evasion = 10 + target_m['stats']['dex']

                if a_roll >= m_evasion:
                    sides = adv_mods.get('weapon_dice_sides', 4) or 4
                    count = adv_mods.get('weapon_dice_count', 1) or 1
                    a_dmg = sum(random.randint(1, sides) for _ in range(
                        count)) + adv_mods['damage'] + adv_mods['str']

                    target_m['hp'] -= a_dmg
                    script.append({"second": current_second - 4, "type": "flavor",
                                  "message": f"{adv.name} asesta un golpe de {a_dmg} daño a [bold red]{target_m['name']}[/bold red]."})

                    # Si el monstruo muere, soltar botín y remover del grupo
                    if target_m['hp'] <= 0:
                        script.append({"second": current_second - 2, "type": "flavor",
                                      "message": f"[bold red]{target_m['name']}[/bold red] muerde el polvo."})

                        # Generar Monedas
                        for coin, max_amt, prob in coin_drops.get(target_m['base'].category, []):
                            if random.random() < prob:
                                amt = random.randint(1, max_amt)
                                script.append({"second": current_second - 1, "type": "loot", "coin": coin, "amount": amt,
                                              "message": f"El monstruo soltó {amt} {coin.replace('_', ' ').title()}."})

                        # Generar Items Raros
                        for rarity, base_prob in item_drops.get(target_m['base'].category, []):
                            if random.random() < (base_prob + (adv.base_luk * 0.01)):
                                pool = [
                                    it for it in all_items_db if it.rarity == rarity]
                                if pool:
                                    drop_item = random.choice(pool)
                                    winner = get_adv_for_item(drop_item)
                                    script.append({"second": current_second, "type": "item_loot", "item_id": drop_item.id,
                                                  "adventurer_id": winner.id, "message": f"¡BOTÍN RARO! {winner.name} obtuvo [{drop_item.name}]."})

                        active_monsters_group.remove(target_m)
                else:
                    script.append({"second": current_second - 4, "type": "flavor",
                                  "message": f"{adv.name} falla su ataque contra [bold red]{target_m['name']}[/bold red]."})

            if not active_monsters_group:
                script.append({"second": current_second, "type": "flavor",
                              "message": "¡VICTORIA! La zona está despejada."})
                state = "EXPLORING"

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
    """Forjamos los primeros objetos con el nuevo sistema granular de 8 slots."""
    if not Item.objects.exists():
        # Armas y Escudos
        Item.objects.create(name="Daga de Hierro", item_type='W1H',
                            rarity='COM', cost_in_copper=10, bonus_damage=2, bonus_dex=1)
        Item.objects.create(name="Mandoble Pesado", item_type='W2H',
                            rarity='UNC', cost_in_copper=50, bonus_damage=5, bonus_str=2)
        Item.objects.create(name="Escudo de Roble", item_type='OFF',
                            rarity='COM', cost_in_copper=15, bonus_armor=2, bonus_con=1)
        # Armadura
        Item.objects.create(name="Casco de Cuero", item_type='HED',
                            rarity='COM', cost_in_copper=10, bonus_armor=1)
        Item.objects.create(name="Cota de Malla", item_type='TRS',
                            rarity='UNC', cost_in_copper=50, bonus_armor=3)
        Item.objects.create(name="Botas Ligeras", item_type='FET',
                            rarity='COM', cost_in_copper=10, bonus_dex=1)
        # Accesorios y Consumibles
        Item.objects.create(name="Amuleto de Erudito", item_type='ACC',
                            rarity='RAR', cost_in_copper=100, bonus_int=3, bonus_wis=2)
        Item.objects.create(name="Poción de Salud Menor", item_type='CNS',
                            rarity='COM', cost_in_copper=5, description="Cura 10 HP")


def get_item_score(item):
    """Calcula el 'Poder Total' de un objeto sumando todas sus estadísticas."""
    if not item:
        return -1
    return (item.bonus_damage * 2) + (item.bonus_armor * 2) + \
        item.bonus_str + item.bonus_dex + item.bonus_con + \
        item.bonus_int + item.bonus_wis + item.bonus_cha + item.bonus_luk


def _auto_equip(adv, item, event_log, pull_type):
    """Evalúa si el objeto es mejor y guarda lo sobrante en la mochila."""
    if not is_class_allowed(adv, item):
        InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)
        event_log.append(
            f"{adv.name} guardó [{item.name}] (Su clase no puede usarlo).")
        return

    # Consumibles y Misceláneos
    if item.item_type == 'CNS':
        if adv.current_hp < adv.max_hp:
            adv.current_hp = min(adv.max_hp, adv.current_hp + 10)
            event_log.append(
                f"{adv.name} bebió [{item.name}] y recuperó HP.")
        else:
            InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)
        return
    elif item.item_type == 'MSC':
        InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)
        event_log.append(
            f"{adv.name} guardó el objeto de lujo [{item.name}].")
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
                InventorySlot.objects.create(
                    adventurer=adv, item=old_item, quantity=1)
            event_log.append(f"💍 {adv.name} se equipó [{item.name}].")
            adv.save()
        else:
            InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)
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
        InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)
        return

    if score_new > score_current:
        if current_item:
            InventorySlot.objects.create(
                adventurer=adv, item=current_item, quantity=1)
        setattr(adv, slot_name, item)

        if item.item_type == 'W2H' and adv.equip_off_hand:
            InventorySlot.objects.create(
                adventurer=adv, item=adv.equip_off_hand, quantity=1)
            adv.equip_off_hand = None

        event_log.append(f"{adv.name} se equipó [{item.name}].")
        adv.save()
    else:
        InventorySlot.objects.create(adventurer=adv, item=item, quantity=1)


def evaluate_daily_penalties():
    """
    Evaluación Perezosa: Revisa si hay hábitos sin marcar de días anteriores.
    Aplica fatiga por cada día fallido y devuelve un log de lo sucedido.
    """
    today = timezone.now().date()
    habits = DailyHabit.objects.all()
    adventurers = Adventurer.objects.all()

    total_fatigue_added = 0
    penalty_log = []

    for habit in habits:
        # Si nunca se ha completado, usa la fecha de creación como referencia
        ref_date = habit.last_completed_date if habit.last_completed_date else habit.created_at
        delta = (today - ref_date).days

        # Si pasaron más de 1 día (es decir, mínimo ayer no se hizo)
        if delta > 1:
            missed_days = delta - 1
            total_fatigue_added += missed_days

            # Avanza la fecha a "ayer" para cobrar la deuda pero no castigar el día de hoy aún
            habit.last_completed_date = today - timedelta(days=1)
            habit.save()
            penalty_log.append(
                f"Hábito roto: '{habit.name}' omitido por {missed_days} día(s).")

    if total_fatigue_added > 0:
        for adv in adventurers:
            adv.fatigue_stacks += total_fatigue_added
            adv.save()
        penalty_log.append(
            f"El Gremio se debilita. Todos reciben {total_fatigue_added} pila(s) de Fatiga (-{total_fatigue_added} a todos los stats).")

    return penalty_log


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
    damage_taken = {}
    for event in script:
        if event["second"] <= survived_seconds:
            if event["type"] == "loot":
                loot[event["coin"]] += event["amount"]
            elif event["type"] == "damage":
                adv_id = event["adventurer_id"]
                damage_taken[adv_id] = damage_taken.get(
                    adv_id, 0) + event["amount"]
            # guardar items en el inventario del aventurero
            elif event["type"] == "item_loot":
                adv = next((a for a in adventurers if a.id ==
                           event["adventurer_id"]), None)
                if adv:
                    try:
                        item_obj = Item.objects.get(id=event["item_id"])
                        InventorySlot.objects.create(
                            adventurer=adv, item=item_obj, quantity=1)
                        event_log.append(
                            f"{adv.name} guardó [{item_obj.name}] en su mochila.")
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
                event_log.append(
                    f"{adv.name} sobrevivió a las heridas con {adv.current_hp}/{adv.max_hp} HP.")
            adv.save()

    distribute_tithe(guild, adventurers, loot, event_log)
    market_phase(adventurers, event_log)

    # --- EXPERIENCIA Y SINERGIA ---
    survived_minutes = survived_seconds // 60
    base_xp = survived_minutes * XP_PER_MINUTE
    guild.experience += base_xp
    check_guild_level_up(guild, event_log)
    event_log.append(
        f"El Gremio gana {base_xp} XP base por sobrevivir {survived_minutes} min.")

    cat_lower = session.category.lower()

    for adv in adventurers:
        multiplier = 1.0

        # Evaluar Sinergia de Categoría
        for key, classes in CATEGORY_SYNERGY.items():
            if key in cat_lower and adv.adv_class in classes:
                multiplier += 0.5  # +50% XP
                event_log.append(
                    f"Sinergia de Clase: {adv.name} domina esta tarea (+50% XP).")
                break

        # Bonus de Sabiduría para aprender más rápido
        wis_bonus = sum(item.bonus_wis for item in adv.get_equipped_items())
        multiplier += (wis_bonus * 0.05)

        adv_xp = int(base_xp * multiplier)
        adv.experience += adv_xp
        adv.save()
        check_level_up(adv, event_log)

    # --- REGISTRO HISTÓRICO PARA LOS GRÁFICOS ---
    today = timezone.now().date()
    daily_stat, _ = DailyStatistic.objects.get_or_create(date=today)
    daily_stat.deep_work_minutes += survived_minutes
    daily_stat.save()

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


def check_guild_level_up(guild, event_log):
    """Comprueba si el Gremio (Usuario) sube de nivel (cada 500 XP fijos)."""
    leveled_up = False
    while guild.experience >= 500:
        guild.level += 1
        guild.experience -= 500
        leveled_up = True

    if leveled_up:
        event_log.append(
            f"¡Ascenso! Tu Gremio sube al Nivel {guild.level}. Ahora puedes reclutar más aventureros.")
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


def get_imperial_value(entity):
    """Convierte toda la riqueza Imperial a Medios Peniques."""
    return (entity.silver_penny * 100) + (entity.copper_penny * 10) + (entity.iron_penny * 2) + entity.iron_half_penny


def get_commonwealth_value(entity):
    """Convierte toda la riqueza de la Mancomunidad a fracciones de Ardite (Base 32)."""
    val = 0
    val += entity.marco * 352000
    val += entity.real * 88000
    val += entity.talento * 35200
    val += entity.sueldo * 1100
    val += entity.iota * 3520
    val += entity.drabin * 352
    val += entity.ardite * 32
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
    adv.ardite = rem_cw // 32  # Dejam todo en ardites

    adv.save()
    # El motor re-ensambla las monedas automáticamente
    universal_consolidate(adv)
    return True


def is_class_allowed(adv, item):
    """Verifica si la clase del aventurero puede usar el objeto."""
    # Si no hay restricciones, todos pueden usarlo.
    if not item.allowed_classes:
        return True
    # Si hay restricciones, verifica si la clase del aventurero está en la lista.
    return adv.adv_class in item.allowed_classes


def market_phase(adventurers_qs, event_log):
    """Simula las compras inteligentes del mercado."""
    _seed_items_if_empty()
    all_items = list(Item.objects.all())

    for adv in adventurers_qs:
        universal_consolidate(adv)
        if adv.is_recovering:
            continue

        valid_items = [i for i in all_items if is_class_allowed(adv, i)]
        affordable_items = [i for i in valid_items if can_afford(adv, i)]

        if not affordable_items:
            continue

        purchased_item = None

        # primera prioridad: supervivencia
        if adv.current_hp < (adv.max_hp * 0.4):
            potions = [i for i in affordable_items if i.item_type == 'CNS']
            if potions:
                purchased_item = max(potions, key=lambda x: get_item_score(x))

        # segunda prioridad: busca el mayor salto de estadísticas
        if not purchased_item:
            best_upgrade = None
            best_score_diff = 0

            for item in affordable_items:
                if item.item_type in ['CNS', 'MSC']:
                    continue

                score_new = get_item_score(item)
                curr_score = -1

                if item.item_type == 'RNG':
                    s1 = get_item_score(
                        adv.equip_ring_1) if adv.equip_ring_1 else -1
                    s2 = get_item_score(
                        adv.equip_ring_2) if adv.equip_ring_2 else -1
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
                        curr_score = get_item_score(
                            curr_item) if curr_item else -1

                        if item.item_type == 'OFF' and getattr(adv, 'equip_main_hand') and getattr(adv, 'equip_main_hand').item_type == 'W2H':
                            continue

                if score_new > curr_score:
                    diff = score_new - curr_score
                    if diff > best_score_diff:
                        best_score_diff = diff
                        best_upgrade = item

            if best_upgrade:
                purchased_item = best_upgrade

        # Ejecutar transacción
        if purchased_item:
            if pay_with_change(adv, purchased_item):
                _auto_equip(adv, purchased_item, event_log, "Mercado")


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
