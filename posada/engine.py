import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .models import GuildProfile, Adventurer, DeepWorkSession, Item, DailyHabit, DailyStatistic, InventorySlot, Monster, ItemRarity, CustomChart, ChartDataPoint, GuildUpgrade, JournalEntry
from .skills import SkillRegistry

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


def roll_d20(advantage=False, disadvantage=False):
    """Realiza una tirada D20 aplicando reglas de Ventaja o Desventaja."""
    r1, r2 = random.randint(1, 20), random.randint(1, 20)
    if advantage and not disadvantage:
        return max(r1, r2)
    if disadvantage and not advantage:
        return min(r1, r2)
    return random.randint(1, 20)


def calculate_save_dc(adv):
    """
    Dificultad de Salvación (Save DC) = 8 + Modificador Principal + Bono de Competencia.
    Se usa para que los enemigos resistan hechizos o efectos del aventurero.
    """
    mods = adv.get_stat_modifiers()
    # Identifica la mejor estadística mágica/táctica del personaje
    spellcasting_mod = max(mods.get('int', 0), mods.get(
        'wis', 0), mods.get('cha', 0))
    # Competencia en D&D 5e escala con el nivel: +2 (niveles 1-4), +3 (5-8), +4 (9+)
    prof_bonus = 2 + ((adv.level - 1) // 4)
    return 8 + spellcasting_mod + prof_bonus


def generate_session_script(session_id, duration_minutes, adventurers_qs):
    random.seed(session_id)
    script = []
    total_seconds = duration_minutes * 60
    adventurers = list(adventurers_qs)

    if not adventurers:
        random.seed()
        return script

    # --- INICIALIZACIÓN DINÁMICA DE RECURSOS ---
    for adv in adventurers:
        res = {}
        if adv.adv_class in ['WIZ', 'SOR', 'WLK', 'CLR', 'DRD', 'BRD']:
            res['mana'] = adv.level * 3
        elif adv.adv_class == 'PAL':
            res['mana'] = adv.level * 2
            res['sanacion'] = adv.level * 5
        elif adv.adv_class == 'MNK':
            res['ki'] = adv.level * 2
        elif adv.adv_class == 'BBN':
            res['furia'] = 2 + (adv.level // 3)
        else:  # FTR, ROG, RGR, ART
            res['stamina'] = adv.level * 2
        adv.class_resources = res

    monsters_db = list(Monster.objects.all())
    all_items_db = list(Item.objects.all())

    state = "EXPLORING"
    current_second = 0
    active_monsters_group = []  # Lista para manejar a los grupos

    # --- TRACKERS TEMPORALES DE HABILIDADES ---
    session_skills_tracker = {adv.id: set() for adv in adventurers}
    combat_skills_tracker = {adv.id: set() for adv in adventurers}
    adv_status_tracker = {adv.id: set() for adv in adventurers}

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

                # Genera cada individuo del grupo con su propio registro de estados
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
                        'name': name, 'hp': hp, 'stats': m_stats, 'base': base_monster,
                        # <-- NUEVO: Los monstruos pueden ser Cegados, Aturdidos, etc.
                        'status': set()
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
            if random.random() < 0.5:
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
            # --- TURNO DE LOS MONSTRUOS ---
            for m in active_monsters_group:
                # --- APLICAR DAÑO EN EL TIEMPO (DoT) AL MONSTRUO ---
                dot_damage = 0
                if 'PSN' in m['status']:
                    dot_damage += random.randint(1, 4)
                if 'BRN' in m['status']:
                    dot_damage += random.randint(1, 6)
                if 'BLD' in m['status']:
                    dot_damage += random.randint(1, 4)
                if dot_damage > 0:
                    m['hp'] -= dot_damage
                    script.append({"second": current_second - 10, "type": "flavor",
                                  "message": f"🩸 [bold red]{m['name']}[/bold red] sufre {dot_damage} de daño por estados alterados."})
                    if m['hp'] <= 0:
                        continue  # Si muere por DoT, pierde su turno

                # Si el monstruo está aturdido, pierde el turno
                if 'STUNNED' in m['status']:
                    m['status'].remove('STUNNED')
                    script.append({"second": current_second - 8, "type": "flavor",
                                  "message": f"💫 [bold red]{m['name']}[/bold red] está aturdido y no puede moverse."})
                    continue

                target = random.choice(adventurers)
                adv_mods = target.get_stat_modifiers()
                adv_evasion = 10 + adv_mods['dex']

                adv_on_attack = 'BLINDED' in adv_status_tracker[
                    target.id] or 'RECKLESS' in adv_status_tracker[target.id]
                disadv_on_attack = 'BLINDED' in m['status'] or 'DODGING' in adv_status_tracker[target.id]

                m_roll = roll_d20(
                    advantage=adv_on_attack, disadvantage=disadv_on_attack) + m['stats']['dex']

                if m_roll >= adv_evasion:
                    base_m = m['base']
                    # Daño Base
                    m_dmg_dice = sum(random.randint(1, base_m.damage_dice_sides)
                                     for _ in range(base_m.damage_dice_count))
                    # Daño Extra Dinámico
                    m_extra_dice = sum(random.randint(1, getattr(base_m, 'bonus_damage_dice_sides', 4)) for _ in range(
                        getattr(base_m, 'bonus_damage_dice_count', 0))) if getattr(base_m, 'bonus_damage_dice_count', 0) > 0 else 0

                    m_dmg = m_dmg_dice + m_extra_dice + \
                        base_m.bonus_damage + m['stats']['str']

                    # --- HOOK DE REACCIONES Y PASIVAS DEFENSIVAS ---
                    if target.adv_class == 'ROG' and target.level >= 5 and 'REACTION_USED' not in adv_status_tracker[target.id]:
                        m_dmg = m_dmg // 2
                        adv_status_tracker[target.id].add('REACTION_USED')
                        script.append({"second": current_second - 8, "type": "flavor",
                                       "message": f"🛡️ {target.name} usa [bold yellow]Esquiva Asombrosa[/bold yellow] y mitiga el impacto."})

                    if 'RAGING' in adv_status_tracker[target.id]:
                        m_dmg = m_dmg // 2

                    # --- EFECTOS AL IMPACTAR (PROCS MONSTRUO) ---
                    eff_m = getattr(base_m, 'on_hit_effect', 'NON')
                    if eff_m != 'NON' and random.randint(1, 100) <= getattr(base_m, 'effect_chance', 0):
                        if eff_m == 'LFS':
                            heal = sum(random.randint(1, getattr(base_m, 'effect_dice_sides', 4)) for _ in range(
                                getattr(base_m, 'effect_dice_count', 1)))
                            max_hp = base_m.base_hp + (m['stats']['con'] * 2)
                            m['hp'] = min(max_hp, m['hp'] + heal)
                            script.append({"second": current_second - 8, "type": "flavor",
                                          "message": f"🦇 ¡[bold red]{m['name']}[/bold red] drena {heal} HP de {target.name}!"})
                        else:
                            adv_status_tracker[target.id].add(eff_m)
                            script.append({"second": current_second - 8, "type": "flavor",
                                          "message": f"🦠 ¡[bold red]{m['name']}[/bold red] inyecta el estado {eff_m} a {target.name}!"})

                    # --- PINCHOS (THORNS) DEL AVENTURERO ---
                    eff_adv = adv_mods.get('on_hit_effect', 'NON')
                    if eff_adv == 'THN' and random.randint(1, 100) <= adv_mods.get('effect_chance', 0):
                        thorns_dmg = random.randint(1, 4)
                        m['hp'] -= thorns_dmg
                        script.append({"second": current_second - 7, "type": "flavor",
                                      "message": f"La armadura de {target.name} devuelve {thorns_dmg} daño a [bold red]{m['name']}[/bold red]."})

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

                adv_mods = adv.get_stat_modifiers()

                # --- APLICAR DAÑO EN EL TIEMPO (DoT) AL AVENTURERO ---
                dot_damage = 0
                if 'PSN' in adv_status_tracker[adv.id]:
                    dot_damage += random.randint(1, 4)
                if 'BRN' in adv_status_tracker[adv.id]:
                    dot_damage += random.randint(1, 6)
                if 'BLD' in adv_status_tracker[adv.id]:
                    dot_damage += random.randint(1, 4)
                if dot_damage > 0:
                    script.append({"second": current_second - 6, "type": "damage", "adventurer_id": adv.id,
                                  "amount": dot_damage, "message": f"🩸 {adv.name} sufre {dot_damage} de daño continuo."})

                # 1. Identificar Habilidades Disponibles en el Grimorio
                available_skills = []
                for skill_id, skill_data in SkillRegistry.get_all_skills().items():
                    if adv.adv_class in skill_data["allowed_classes"] and adv.level >= skill_data["req_level"]:
                        if skill_data["type"] == "COMBAT" and skill_id not in combat_skills_tracker[adv.id]:
                            available_skills.append(skill_data)
                        elif skill_data["type"] == "SESSION" and skill_id not in session_skills_tracker[adv.id]:
                            available_skills.append(skill_data)

                # 2. IA de Utilidad: ¿Qué hacer en este turno?
                best_action = "BASIC_ATTACK"
                best_score = 50  # Puntuación base para un ataque normal

                context = {
                    'caster': adv,
                    'allies': adventurers,
                    'enemies': active_monsters_group,
                    'adv_status': adv_status_tracker,
                    'current_second': current_second - 4,
                    'log': script,
                    'eval_mode': True  # Modo evaluación silencioso
                }

                # El aventurero simula mentalmente cada habilidad para ver su utilidad actual
                for skill in available_skills:
                    score = skill["execute"](context)
                    if score > best_score:
                        best_score = score
                        best_action = skill

                # Apagamos el modo evaluación para la acción real
                context['eval_mode'] = False

                # 3. Ejecutar la Mejor Decisión
                if best_action == "BASIC_ATTACK":
                    # --- ATAQUE BÁSICO Y MULTIATAQUE ---

                    # Limpiamos la Reacción para que el Pícaro la vuelva a tener disponible
                    adv_status_tracker[adv.id].discard('REACTION_USED')

                    # Nivel 5: Clases Marciales atacan dos veces
                    attacks = 2 if adv.level >= 5 and adv.adv_class in [
                        'FTR', 'BBN', 'RGR', 'PAL', 'MNK'] else 1

                    for _ in range(attacks):
                        if not active_monsters_group:
                            break

                        target_m = random.choice(active_monsters_group)
                        attack_stat = max(adv_mods['str'], adv_mods['dex'])

                        # Lógica de Ventaja/Desventaja
                        adv_on_attack = 'BLINDED' in target_m['status'] or 'RECKLESS' in adv_status_tracker[adv.id]
                        disadv_on_attack = 'BLINDED' in adv_status_tracker[adv.id]

                        a_roll = roll_d20(
                            advantage=adv_on_attack, disadvantage=disadv_on_attack) + attack_stat
                        m_evasion = 10 + target_m['stats']['dex']

                        if a_roll >= m_evasion:
                            sides = adv_mods.get('weapon_dice_sides', 4) or 4
                            count = adv_mods.get('weapon_dice_count', 1) or 1
                            a_dmg = sum(random.randint(1, sides) for _ in range(
                                count)) + adv_mods['damage'] + adv_mods['str']

                            # --- DADOS EXTRA DINÁMICOS ---
                            extra_count = adv_mods.get(
                                'bonus_dmg_dice_count', 0)
                            if extra_count > 0:
                                extra_sides = adv_mods.get(
                                    'bonus_dmg_dice_sides', 4) or 4
                                a_dmg += sum(random.randint(1, extra_sides)
                                             for _ in range(extra_count))

                            # --- PASIVAS OFENSIVAS ---
                            # Ataque Furtivo del Pícaro
                            if adv.adv_class == 'ROG' and adv_on_attack:
                                sneak_dice = (adv.level + 1) // 2
                                sneak_dmg = sum(random.randint(1, 6)
                                                for _ in range(sneak_dice))
                                a_dmg += sneak_dmg
                                script.append({"second": current_second - 5, "type": "flavor",
                                               "message": f"🗡️ ¡Ataque Furtivo brutal de {adv.name}! (+{sneak_dmg} daño extra)"})

                            # Bono de Furia
                            if 'RAGING' in adv_status_tracker[adv.id]:
                                a_dmg += 2

                            # Arma Infundida del Artificiero
                            if 'INFUSED_WEAPON' in adv_status_tracker[adv.id]:
                                a_dmg += 1

                            # Inspiración Bárdica (Suma 1d6 al ataque y luego se gasta)
                            if 'INSPIRED' in adv_status_tracker[adv.id]:
                                bard_dice = random.randint(1, 6)
                                a_roll += bard_dice  # Modificamos el dado que tiró para asegurar que golpee
                                adv_status_tracker[adv.id].remove('INSPIRED')
                                script.append({"second": current_second - 5, "type": "flavor",
                                               "message": f"🎵 ¡La música del Bardo guía el golpe de {adv.name}! (+{bard_dice} precisión)"})

                            # --- EFECTOS AL IMPACTAR (PROCS AVENTURERO) ---
                            eff = adv_mods.get('on_hit_effect', 'NON')
                            if eff != 'NON' and eff != 'THN':
                                if random.randint(1, 100) <= adv_mods.get('effect_chance', 0):
                                    if eff == 'LFS':
                                        # Usa el dado de efecto asignado
                                        heal = sum(random.randint(1, adv_mods['effect_dice_sides']) for _ in range(
                                            adv_mods['effect_dice_count']))
                                        script.append({"second": current_second - 4, "type": "damage", "adventurer_id": adv.id,
                                                      "amount": -heal, "message": f"🦇 {adv.name} drena {heal} HP de su enemigo."})
                                    else:
                                        target_m['status'].add(eff)
                                        eff_names = {
                                            'PSN': 'Veneno', 'BLD': 'Sangrado', 'BRN': 'Quemaduras', 'STN': 'Aturdimiento', 'BLN': 'Ceguera'}
                                        script.append({"second": current_second - 4, "type": "flavor",
                                                      "message": f"🦠 ¡{adv.name} inflige {eff_names.get(eff, eff)} a [bold red]{target_m['name']}[/bold red]!"})

                            target_m['hp'] -= a_dmg
                            script.append({"second": current_second - 4, "type": "flavor",
                                          "message": f"{adv.name} asesta un golpe de {a_dmg} daño a [bold red]{target_m['name']}[/bold red]."})
                        else:
                            script.append({"second": current_second - 4, "type": "flavor",
                                          "message": f"{adv.name} falla su ataque contra [bold red]{target_m['name']}[/bold red]."})
                else:
                    # --- EJECUCIÓN DE HABILIDAD ---
                    success = best_action["execute"](context)
                    if success:
                        # Coloca la habilidad en enfriamiento temporal
                        if best_action["type"] == "COMBAT":
                            combat_skills_tracker[adv.id].add(
                                best_action["id"])
                        elif best_action["type"] == "SESSION":
                            session_skills_tracker[adv.id].add(
                                best_action["id"])

                # Comprobación Universal de Muertes (Aplica tanto para ataques como daño de área)
                for m in list(active_monsters_group):
                    if m['hp'] <= 0:
                        script.append({"second": current_second - 2, "type": "flavor",
                                      "message": f"[bold red]{m['name']}[/bold red] muerde el polvo."})

                        # Generar Monedas
                        for coin, max_amt, prob in coin_drops.get(m['base'].category, []):
                            if random.random() < prob:
                                amt = random.randint(1, max_amt)
                                script.append({"second": current_second - 1, "type": "loot", "coin": coin, "amount": amt,
                                              "message": f"El monstruo soltó {amt} {coin.replace('_', ' ').title()}."})

                        # Generar Items Raros
                        for rarity, base_prob in item_drops.get(m['base'].category, []):
                            if random.random() < (base_prob + (adv.base_luk * 0.01)):
                                pool = [
                                    it for it in all_items_db if it.rarity == rarity]
                                if pool:
                                    drop_item = random.choice(pool)
                                    color = ItemRarity.get_color(
                                        drop_item.rarity)
                                    winner = get_adv_for_item(drop_item)
                                    script.append({
                                        "second": current_second, "type": "item_loot", "item_id": drop_item.id,
                                        "adventurer_id": winner.id,
                                        "message": f"¡BOTÍN RARO! {winner.name} obtuvo [[{color}]{drop_item.name}[/]]."
                                    })

                        active_monsters_group.remove(m)

            if not active_monsters_group:
                # Reseteo del enfriamiento de habilidades de combate
                for adv_id in combat_skills_tracker:
                    combat_skills_tracker[adv_id].clear()
                    # Limpia los estados negativos al terminar el combate
                    adv_status_tracker[adv_id].clear()

                script.append({"second": current_second, "type": "flavor",
                              "message": "¡VICTORIA! La zona está despejada."})
                state = "EXPLORING"

    script.sort(key=lambda x: x["second"])
    random.seed()
    return script


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


def _seed_guild_upgrades():
    """Forja los planos de las mejoras de Gremio si no existen."""
    if not GuildUpgrade.objects.exists():
        GuildUpgrade.objects.create(key='mensajeria_arcana', name='Mensajería Arcana',
                                    description='Envía el excedente de botín al cofre por 1 Drabín.', cost_coin='sueldo', cost_amount=5, req_prestige_level=1)
        GuildUpgrade.objects.create(key='mochila_lv2', name='Mochilas de Contención',
                                    description='Aumenta la mochila de los aventureros a 15 ranuras.', cost_coin='talento', cost_amount=2, req_prestige_level=2)
        GuildUpgrade.objects.create(key='tablon_patroc', name='Tablón Patrocinado',
                                    description='5% prob. de ítem épico al completar hábitos Rango S.', cost_coin='marco', cost_amount=1, req_prestige_level=3)


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
        today = timezone.now().date()
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
    """Resta prestigio por pereza o PREMIA por evitar malos hábitos."""
    today = timezone.now().date()
    habits = DailyHabit.objects.all()
    guild, _ = GuildProfile.objects.get_or_create(id=1)

    total_prestige_change = 0
    penalty_log = []

    for habit in habits:
        ref_date = habit.last_completed_date if habit.last_completed_date else habit.created_at
        delta = (today - ref_date).days

        if delta > 1:
            missed_valid_days = 0
            for i in range(1, delta):
                check_date = ref_date + timedelta(days=i)
                if str(check_date.weekday()) in habit.valid_days:
                    missed_valid_days += 1

            if missed_valid_days > 0:
                if habit.is_bad_habit:
                    # ¡Resististe la tentación!
                    reward_map = {'S': 50, 'A': 25, 'B': 10, 'C': 5}
                    prestige_gain = reward_map.get(
                        habit.difficulty, 5) * missed_valid_days
                    total_prestige_change += prestige_gain
                    habit.current_streak += missed_valid_days
                    penalty_log.append(
                        f"Evitaste '{habit.name}' por {missed_valid_days} día(s) (+{prestige_gain} Prestigio).")
                else:
                    # CASTIGO: Pereza en un buen hábito
                    prestige_loss = missed_valid_days * 15
                    total_prestige_change -= prestige_loss
                    habit.current_streak = 0
                    penalty_log.append(
                        f"Hábito roto: '{habit.name}' (-{prestige_loss} Prestigio).")

            habit.last_completed_date = today - timedelta(days=1)
            habit.save()

    if total_prestige_change != 0:
        guild.prestige += total_prestige_change

        # Verifica si las resistencias silenciosas suben de nivel al gremio
        while True:
            meta = guild.prestige_level * 100
            if guild.prestige >= meta:
                guild.prestige -= meta
                guild.prestige_level += 1
            else:
                break

        guild.save()
        if total_prestige_change < 0:
            penalty_log.append(
                f"El Gremio pierde influencia. (Impacto Neto: {total_prestige_change})")

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
                event_log.append(
                    f"{adv.name} sobrevivió a las heridas con {adv.current_hp}/{adv.max_hp} HP.")
            adv.save()

    distribute_tithe(guild, adventurers, loot, event_log)
    market_phase(adventurers, event_log)

    # --- EXPERIENCIA DE AVENTUREROS ---
    survived_minutes = survived_seconds // 60
    base_xp = survived_minutes * XP_PER_MINUTE
    cat_lower = session.category.lower()

    for adv in adventurers:
        multiplier = 1.0
        for key, classes in CATEGORY_SYNERGY.items():
            if key in cat_lower and adv.adv_class in classes:
                multiplier += 0.5
                event_log.append(
                    f"Sinergia: {adv.name} domina esta tarea (+50% XP).")
                break
        wis_bonus = sum(item.bonus_wis for item in adv.get_equipped_items())
        multiplier += (wis_bonus * 0.05)

        adv.experience += int(base_xp * multiplier)

        # Limpia los enfriamientos para la próxima sesión
        adv.session_skills_used = []
        adv.combat_skills_used = []
        adv.class_resources = {}

        adv.save()
        check_level_up(adv, event_log)

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


def calculate_chart_reward(chart):
    """Calcula el Área bajo la curva usando proporciones sobre el área total del lienzo."""
    points = list(chart.data_points.all().order_by('x_value'))
    if not points:
        return {"status": "error", "message": "El gráfico está vacío."}

    if points[-1].x_value < chart.goal_x_value:
        return {"status": "warning", "message": f"Aún no llegas a la meta (Día {chart.goal_x_value})."}

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

    # da prestigio masivo
    prestige_reward = {'S': 200, 'A': 100, 'B': 50, 'C': 10}[grade]
    coin_reward = {'S': ('marco', 1), 'A': ('talento', 2), 'B': (
        'sueldo', 5), 'C': ('silver_penny', 10)}[grade]

    guild.prestige += prestige_reward
    setattr(guild, coin_reward[0], getattr(
        guild, coin_reward[0]) + coin_reward[1])
    guild.save()
    universal_consolidate(guild)

    chart.data_points.all().delete()  # Reinicia el gráfico

    return {
        "status": "success",
        "message": f"¡Ciclo completado! Rango {grade} ({rendimiento*100:.1f}% del área). Gremio gana +{prestige_reward} Prestigio y {coin_reward[1]} {coin_reward[0].title()}."
    }
