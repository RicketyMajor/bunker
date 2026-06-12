from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import GuildProfile, Adventurer, DeepWorkSession, AdventurerClass, AdventurerRace, AdventurerGender, DailyHabit, DailyStatistic, HabitDifficulty, InventorySlot, ItemRarity, CustomChart, ChartDataPoint, ChartPolarity, JournalEntry, Item, GuildUpgrade, GuildUnlockedUpgrade
import random
from .engine import process_session_completion, generate_session_script, consolidate_wealth, distribute_random_stats, evaluate_daily_penalties, universal_consolidate, calculate_chart_reward, get_chart_completion_status, is_class_allowed, get_derived_skills
from django.utils import timezone
from datetime import timedelta
from .skills import SkillRegistry


def get_item_info(item, default="Vacío"):
    """Devuelve el nombre formateado y su descripción rica con lore y stats."""
    if not item:
        return {"name": default, "desc": "Ranura vacía. No hay equipo para inspeccionar."}

    color = ItemRarity.get_color(item.rarity)
    name_rich = f"[[{color}]{item.name}[/]]"

    desc = item.description or "Un objeto común sin propiedades especiales registradas."
    stats = []

    # Recopilar estadísticas para el Tooltip
    if item.damage_dice_count > 0 or item.bonus_damage > 0:
        stats.append(
            f"Daño: {item.damage_dice_count}d{item.damage_dice_sides} + {item.bonus_damage}")
    if item.bonus_damage_dice_count > 0:
        stats.append(
            f"Daño Mágico: {item.bonus_damage_dice_count}d{item.bonus_damage_dice_sides}")
    if item.bonus_armor > 0:
        stats.append(f"Armadura: +{item.bonus_armor}")
    if item.on_hit_effect != 'NON':
        stats.append(
            f"Efecto: {item.get_on_hit_effect_display()} ({item.effect_chance}%)")

    if stats:
        desc += f"\n\n[bold cyan]Atributos:[/] " + " | ".join(stats)

    return {"name": name_rich, "desc": desc}


@api_view(['GET'])
def guild_status(request):
    """Devuelve el estado general del Gremio y la lista de aventureros con sus stats de RPG."""
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    adventurers = Adventurer.objects.all()

    adv_data = []
    for adv in adventurers:
        mods = adv.get_stat_modifiers()

        def fmt_stat(base, stat_key):
            """Genera el texto enriquecido para la TUI (Ej: 15 [+2])"""
            mod = mods.get(stat_key, 0)
            total = base + mod
            if mod > 0:
                return f"{total} [bold green](+{mod})[/bold green]"
            elif mod < 0:
                return f"{total} [bold red]({mod})[/bold red]"
            return str(total)

        # --- Recopilar Grimorio ---
        grimoire = []
        for skill_id, skill_data in SkillRegistry.get_all_skills().items():
            if adv.adv_class in skill_data["allowed_classes"] and adv.level >= skill_data["req_level"]:
                grimoire.append({
                    "name": skill_data["name"],
                    "type": "Pasiva/Apoyo" if skill_data["type"] == "SESSION" else "Combate",
                    "req_level": skill_data["req_level"]
                })

        adv_data.append({
            "id": adv.id,
            "name": adv.name,
            "class_name": adv.get_adv_class_display(),
            "race": adv.get_race_display(),
            "level": adv.level,
            "xp": adv.experience,
            "hp": f"{adv.current_hp}/{adv.max_hp}",

            # --- Estadísticas Formateadas ---
            "str": fmt_stat(adv.base_str, 'str'),
            "dex": fmt_stat(adv.base_dex, 'dex'),
            "con": fmt_stat(adv.base_con, 'con'),
            "int": fmt_stat(adv.base_int, 'int'),
            "wis": fmt_stat(adv.base_wis, 'wis'),
            "cha": fmt_stat(adv.base_cha, 'cha'),
            "luk": fmt_stat(adv.base_luk, 'luk'),

            # --- Combate Real ---
            "combat_armor": mods['armor'],
            "combat_damage": f"{mods['weapon_dice_count']}d{mods['weapon_dice_sides']} + {mods['damage']}",

            "wealth": {
                "iron_half_penny": adv.iron_half_penny, "iron_penny": adv.iron_penny,
                "ardite": adv.ardite, "drabin": adv.drabin, "copper_penny": adv.copper_penny,
                "iota": adv.iota, "silver_penny": adv.silver_penny, "sueldo": adv.sueldo,
                "talento": adv.talento, "real": adv.real, "marco": adv.marco
            },
            "wealth_summary": f"{adv.talento}T, {adv.iota}i, {adv.ardite}a",

            # --- Habilidades, Grimorio y Diccionario de Equipamiento ---
            "rpg_skills": get_derived_skills(adv),
            "grimoire": grimoire,
            "equipment": {
                "equip_main_hand": get_item_info(adv.equip_main_hand, "Desarmado"),
                "equip_off_hand": get_item_info(adv.equip_off_hand),
                "equip_head": get_item_info(adv.equip_head),
                "equip_torso": get_item_info(adv.equip_torso, "Ropa común"),
                "equip_hands": get_item_info(adv.equip_hands),
                "equip_legs": get_item_info(adv.equip_legs),
                "equip_feet": get_item_info(adv.equip_feet),
                "equip_necklace": get_item_info(adv.equip_necklace, "Ninguno"),
                "equip_ring_1": get_item_info(adv.equip_ring_1),
                "equip_ring_2": get_item_info(adv.equip_ring_2),
                "equip_bracelet": get_item_info(adv.equip_bracelet, "Ninguno"),
                "equip_earring": get_item_info(adv.equip_earring, "Ninguno"),
            }
        })

    guild_data = {
        "prestige_level": guild.prestige_level,
        "prestige": guild.prestige,
        "prestige_meta": guild.prestige_meta,
        "net_worth_talents": guild.net_worth_in_talents,
        "inventory": {
            "iron_half_penny": guild.iron_half_penny, "iron_penny": guild.iron_penny,
            "ardite": guild.ardite, "drabin": guild.drabin, "copper_penny": guild.copper_penny,
            "iota": guild.iota, "silver_penny": guild.silver_penny, "sueldo": guild.sueldo,
            "talento": guild.talento, "real": guild.real, "marco": guild.marco
        }
    }

    return Response({"guild": guild_data, "adventurers": adv_data})


@api_view(['POST'])
def consolidate_guild_wealth(request):
    """Llama al motor para consolidar la riqueza del gremio (Mesa del Cambista)."""
    # El ID 1 siempre representa a tu Gremio principal
    result = consolidate_wealth(1)
    if result.get("status") == "error":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
def start_session(request):
    """Crea la sesión al inicio y devuelve el guion de eventos pre-calculado."""
    data = request.data
    duration = data.get('duration_minutes', 25)
    category = data.get('category', 'General')
    adventurer_ids = data.get('adventurer_ids', [])

    # Crea la sesión en el momento para obtener un ID único que sirva de semilla
    session = DeepWorkSession.objects.create(
        duration_minutes=duration,
        category=category,
        completed=False
    )

    if adventurer_ids:
        adventurers = Adventurer.objects.filter(id__in=adventurer_ids)
        session.adventurers_involved.set(adventurers)
        session.save()
    else:
        adventurers = []

    # el Oráculo genera el destino
    script = generate_session_script(session.id, duration, adventurers)

    return Response({
        "status": "success",
        "session_id": session.id,
        "script": script
    })


@api_view(['POST'])
def complete_session(request):
    """Cierra la sesión aplicando el botín ganado según el tiempo sobrevivido."""
    data = request.data
    session_id = data.get('session_id')
    survived_seconds = data.get('survived_seconds')

    if not session_id:
        return Response({"status": "error", "message": "Falta el ID de la sesión."}, status=status.HTTP_400_BAD_REQUEST)

    # El motor procesa la realidad basándose en cuánto tiempo se aguantate sin distracciones, y devuelve el resultado de la expedición
    result = process_session_completion(session_id, survived_seconds)

    if result.get("status") == "error":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "status": "success",
        "message": "Expedición finalizada.",
        "log": result.get("log", []),
        "engine_details": result
    })


@api_view(['POST'])
def create_adventurer(request):
    """Crea un aventurero. Verifica el límite de cupos del Gremio."""
    guild, _ = GuildProfile.objects.get_or_create(id=1)

    # 1 cupo por cada Nivel del Gremio
    if Adventurer.objects.count() >= guild.prestige_level:
        return Response({
            "status": "error",
            "message": f"Gremio Nv. {guild.prestige_level} lleno. Estudia y sube de nivel para tener más cupos."
        }, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    cost_sueldos = data.get('cost_in_sueldos', 0)
    if cost_sueldos > 0:
        from posada.engine import pay_with_change
        class DummyItem:
            pass
        dummy = DummyItem()
        dummy.cost_marco = dummy.cost_real = dummy.cost_talento = dummy.cost_silver_penny = 0
        dummy.cost_iota = dummy.cost_drabin = dummy.cost_ardite = 0
        dummy.cost_sueldo = cost_sueldos
        dummy.cost_iron_penny = dummy.cost_iron_half_penny = dummy.cost_copper_penny = 0
        
        if not pay_with_change(guild, dummy):
            return Response({
                "status": "error",
                "message": f"Fondos insuficientes. El contrato cuesta {cost_sueldos} Sueldos (o equivalente)."
            }, status=status.HTTP_400_BAD_REQUEST)

    stats = data.get('stats', None)
    recruit_lvl = data.get('level', 1)

    adv = Adventurer.objects.create(
        name=data.get('name', 'Aventurero Desconocido'),
        adv_class=data.get('adv_class', 'FTR'),
        race=data.get('race', 'HUM'),
        gender=data.get('gender', 'O'),
        level=recruit_lvl,
        max_hp=25 + (recruit_lvl * 5),
        current_hp=25 + (recruit_lvl * 5),
        # Si vienen stats de la taberna, los asignamos. Si no, 0.
        base_str=stats['str'] if stats else 0, base_dex=stats['dex'] if stats else 0,
        base_con=stats['con'] if stats else 0, base_int=stats['int'] if stats else 0,
        base_wis=stats['wis'] if stats else 0, base_cha=stats['cha'] if stats else 0,
        base_luk=stats['luk'] if stats else 0
    )

    # Si es el primer avatar manual, reparte al azar los 13 pts.
    if not stats:
        distribute_random_stats(adv, 13)

    return Response({"status": "success", "message": f"{adv.name} ha firmado el contrato."})


@api_view(['GET'])
def tavern_recruits(request):
    """Genera reclutas procedurales escalados al Gremio."""
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    # 3 reclutas base + 2 por cada nivel después del 1
    num_recruits = 3 + (guild.prestige_level - 1) * 2
    
    # Calcular nivel máximo posible basado en los aventureros actuales
    max_lvl = 1
    advs = Adventurer.objects.all()
    if advs.exists():
        max_lvl = max([a.level for a in advs])
    max_recruit_lvl = max(1, max_lvl - 1)

    prefixes = ["Thor", "Grim", "Ar", "Leg", "Kvoth", "El",
                "Fae", "Gael", "Bae", "Mor", "Dae", "Val", "Gim"]
    suffixes = ["din", "gar", "agorn", "olas", "e", "rond",
                "lin", "dor", "th", "gan", "mon", "ria", "li"]

    recruits = []
    for _ in range(num_recruits):
        # Generación de Identidad
        name = random.choice(prefixes) + random.choice(suffixes)
        adv_class_obj = random.choice(AdventurerClass.choices)
        race_obj = random.choice(AdventurerRace.choices)
        gender_obj = random.choice(AdventurerGender.choices)

        recruit_lvl = random.randint(1, max_recruit_lvl)
        cost_sueldo = recruit_lvl * 6
        equipment_desc = f"Set Básico Nv. {recruit_lvl}" if recruit_lvl < 5 else f"Set Curtido Nv. {recruit_lvl}"

        # Reparto Procedural de los Puntos Base
        stats = {'str': 0, 'dex': 0, 'con': 0,
                 'int': 0, 'wis': 0, 'cha': 0, 'luk': 0}
        keys = list(stats.keys())
        for _ in range(13 + (recruit_lvl - 1)):
            stats[random.choice(keys)] += 1

        recruits.append({
            "name": name,
            "adv_class": adv_class_obj[0],
            "adv_class_display": adv_class_obj[1],
            "race": race_obj[0],
            "race_display": race_obj[1],
            "gender": gender_obj[0],
            "stats": stats,
            "level": recruit_lvl,
            "cost_in_sueldos": cost_sueldo,
            "equipment_desc": equipment_desc
        })
    return Response({"recruits": recruits})


@api_view(['DELETE'])
def delete_adventurer(request, adv_id):
    """Elimina un aventurero de la base de datos."""
    try:
        adv = Adventurer.objects.get(id=adv_id)
        name = adv.name
        adv.delete()
        return Response({"status": "success", "message": f"{name} ha sido eliminado del Gremio."})
    except Adventurer.DoesNotExist:
        return Response({"status": "error", "message": "Aventurero no encontrado."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
def rename_adventurer(request, adv_id):
    """Renombra un aventurero."""
    new_name = request.data.get('name', '').strip()
    if not new_name:
        return Response({"status": "error", "message": "El nombre no puede estar vacío."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        adv = Adventurer.objects.get(id=adv_id)
        old_name = adv.name
        adv.name = new_name
        adv.save()
        return Response({"status": "success", "message": f"{old_name} ahora se llama {new_name}."})
    except Adventurer.DoesNotExist:
        return Response({"status": "error", "message": "Aventurero no encontrado."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def list_habits(request):
    """Lista todos los hábitos y evalúa penalizaciones de días anteriores."""
    # Al consultar el tablón, el motor revisa si hay deudas de días pasados
    penalties = evaluate_daily_penalties()

    today = timezone.localdate()
    habits = DailyHabit.objects.all()

    habit_list = []
    for h in habits:
        habit_list.append({
            "id": h.id, "name": h.name, "difficulty": h.get_difficulty_display(),
            "difficulty_code": h.difficulty,
            "completed_today": h.last_completed_date == today,
            "current_streak": h.current_streak,
            "is_bad_habit": h.is_bad_habit,
            "valid_days": h.valid_days,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "last_completed_date": h.last_completed_date.isoformat() if h.last_completed_date else None,
            "previous_streak": h.previous_streak,
        })

    return Response({
        "habits": habit_list,
        "penalties_applied": penalties
    })


@api_view(['POST'])
def create_habit(request):
    data = request.data
    habit = DailyHabit.objects.create(
        name=data.get('name'), difficulty=data.get('difficulty', 'C'),
        valid_days=data.get('valid_days', '0,1,2,3,4,5,6'),
        is_bad_habit=data.get('is_bad_habit', False)
    )
    return Response({"status": "success", "message": f"Hábito '{habit.name}' añadido."})


@api_view(['POST'])
def complete_habit(request):
    today = timezone.localdate()
    habit_id = request.data.get('habit_id')

    try:
        habit = DailyHabit.objects.get(id=habit_id)
        if habit.last_completed_date == today:
            return Response({"status": "warning", "message": "Ya interactuaste con este hábito hoy."})

        guild, _ = GuildProfile.objects.get_or_create(id=1)
        rewards = {
            'S': {'prestige': 25, 'coin': 'iota', 'amt': 2, 'coin2': 'drabin', 'amt2': 5},
            'A': {'prestige': 10, 'coin': 'ardite', 'amt': 10, 'coin2': 'copper_penny', 'amt2': 1},
            'B': {'prestige': 5,  'coin': 'iron_penny', 'amt': 5, 'coin2': 'ardite', 'amt2': 2},
            'C': {'prestige': 2,  'coin': 'iron_half_penny', 'amt': 5, 'coin2': None, 'amt2': 0},
        }
        r = rewards.get(habit.difficulty)

        if habit.is_bad_habit:
            # LÓGICA DE RECAÍDA
            prestige_penalty = r['prestige'] * \
                2  # Penalización doble por recaer
            habit.last_prestige_reward = prestige_penalty
            habit.previous_streak = habit.current_streak

            guild.prestige -= prestige_penalty
            habit.current_streak = 0
            habit.last_completed_date = today
            guild.save()
            habit.save()
            return Response({"status": "error", "message": f"¡Recaída en '{habit.name}'! Perdiste {prestige_penalty} Prestigio."})

        else:
            # LÓGICA DE BUEN HÁBITO
            habit.last_prestige_reward = r['prestige']
            habit.last_coin_type = r['coin']
            habit.last_coin_amount = r['amt']
            habit.previous_streak = habit.current_streak
            habit.current_streak += 1

            setattr(guild, r['coin'], getattr(guild, r['coin']) + r['amt'])
            if r['coin2']:
                setattr(guild, r['coin2'], getattr(guild, r['coin2']) + r['amt2'])

            leveled_up = guild.add_prestige(r['prestige'])

            habit.last_completed_date = today
            habit.save()

            lvl_msg = f" ¡El Gremio ascendió al Nivel {guild.prestige_level}!" if leveled_up else ""

            # --- LÓGICA DE HITOS DE RACHAS (COFRES) ---
            drop_msg = ""
            if habit.current_streak in [7, 14, 30, 60, 90, 180, 365]:
                diff_weight = {'C': 0, 'B': 1, 'A': 2, 'S': 3}[habit.difficulty]
                streak_weight = {7: 0, 14: 1, 30: 2, 60: 3, 90: 3, 180: 4, 365: 5}[habit.current_streak]
                
                total_weight = diff_weight + streak_weight
                
                rarity = 'COM'
                if total_weight >= 6:
                    rarity = 'LEG' if random.random() < 0.3 else 'EPC'
                elif total_weight >= 4:
                    rarity = 'EPC' if random.random() < 0.4 else 'RAR'
                elif total_weight >= 2:
                    rarity = 'RAR' if random.random() < 0.5 else 'UNC'
                elif total_weight >= 1:
                    rarity = 'UNC'
                    
                pool = Item.objects.filter(rarity=rarity)
                if not pool.exists() and rarity in ['EPC', 'LEG']:
                    pool = Item.objects.filter(rarity='RAR')
                    
                if pool.exists():
                    drop = random.choice(pool)
                    g_slot, _ = InventorySlot.objects.get_or_create(guild=guild, item=drop, adventurer=None, defaults={'quantity': 0})
                    g_slot.quantity += 1
                    g_slot.save()
                    color = ItemRarity.get_color(drop.rarity)
                    drop_msg += f"\n🎁 ¡Racha de {habit.current_streak} días! Cofre: \\[[{color}]{drop.name}[/]\\]"

            # --- LÓGICA DEL TABLÓN PATROCINADO ---
            if habit.difficulty == 'S':
                has_patroc = GuildUnlockedUpgrade.objects.filter(
                    guild=guild, upgrade__key='tablon_patroc').exists()
                if has_patroc and random.random() < 0.05:  # 5% de probabilidad
                    pool = Item.objects.filter(rarity__in=['EPC', 'LEG'])
                    if pool.exists():
                        drop = random.choice(pool)
                        g_slot, _ = InventorySlot.objects.get_or_create(
                            guild=guild, item=drop, adventurer=None, defaults={'quantity': 0})
                        g_slot.quantity += 1
                        g_slot.save()
                        color = ItemRarity.get_color(drop.rarity)
                        drop_msg = f"\n¡El Tablón Patrocinado te envió \\[[{color}]{drop.name}[/]\\] al cofre!"

            return Response({"status": "success", "message": f"¡'{habit.name}' completado! +{r['prestige']} Prestigio.{lvl_msg}{drop_msg}"})

    except DailyHabit.DoesNotExist:
        return Response({"status": "error", "message": "Hábito no encontrado."})


@api_view(['GET'])
def get_stats_data(request):
    """Extrae los últimos 30 días de actividad para el gráfico."""
    thirty_days_ago = timezone.localdate() - timedelta(days=30)
    stats = DailyStatistic.objects.filter(
        date__gte=thirty_days_ago).order_order_by('date')

    data = {
        "dates": [s.date.strftime("%d/%m") for s in stats],
        "deep_work": [s.deep_work_minutes for s in stats],
        "screen_time": [s.screen_time_minutes for s in stats]
    }
    return Response(data)


@api_view(['GET'])
def get_inventory(request, target_type, target_id):
    """Obtiene el contenido de una mochila (aventurero) o del cofre (gremio)."""
    if target_type == 'guild':
        slots = InventorySlot.objects.filter(
            guild_id=target_id, quantity__gt=0)
    else:
        slots = InventorySlot.objects.filter(
            adventurer_id=target_id, quantity__gt=0)

    data = []
    for s in slots:
        data.append({
            "slot_id": s.id,
            "item_name": s.item.name,
            "color": ItemRarity.get_color(s.item.rarity),
            "type": s.item.get_item_type_display(),
            "qty": s.quantity,
            "stats": f"DMG:{s.item.bonus_damage} | ARM:{s.item.bonus_armor}",
            "desc": f"[{ItemRarity.get_color(s.item.rarity)}]{s.item.name}[/]\n\n{s.item.description}\n[b]Material:[/b] {s.item.get_material_display()} | [b]Bonus:[/b] DMG +{s.item.bonus_damage} / ARM +{s.item.bonus_armor}"
        })
    return Response({"slots": data})


@api_view(['POST'])
def inventory_action(request):
    """Mueve objetos entre el Cofre y los Aventureros, Vende o Equipa."""
    action = request.data.get('action')
    slot_id = request.data.get('slot_id')
    adv_id = request.data.get('adv_id')

    try:
        slot = InventorySlot.objects.get(id=slot_id)
        guild = GuildProfile.objects.get(id=1)
        is_stackable = slot.item.item_type in ['CNS', 'MSC']

        if action == "to_guild":
            if not slot.adventurer:
                return Response({"error": "Ya está en el cofre"}, status=400)
            if is_stackable:
                g_slot, _ = InventorySlot.objects.get_or_create(
                    guild=guild, item=slot.item, adventurer=None, defaults={'quantity': 0})
                g_slot.quantity += 1
                g_slot.save()
            else:
                InventorySlot.objects.create(
                    guild=guild, item=slot.item, adventurer=None, quantity=1)

        elif action == "to_adv":
            if not slot.guild:
                return Response({"error": "No está en el cofre"}, status=400)
            target_adv = Adventurer.objects.get(id=adv_id)

            if is_stackable:
                a_slots = InventorySlot.objects.filter(
                    adventurer=target_adv, item=slot.item, quantity__lt=16)
                if a_slots.exists():
                    a_slot = a_slots.first()
                    a_slot.quantity += 1
                    a_slot.save()
                elif target_adv.inventory.count() < target_adv.inventory_capacity:
                    InventorySlot.objects.create(
                        adventurer=target_adv, item=slot.item, guild=None, quantity=1)
                else:
                    return Response({"error": "La mochila del aventurero está llena (Max 10 slots)."}, status=400)
            else:
                if target_adv.inventory.count() >= target_adv.inventory_capacity:
                    return Response({"error": "La mochila del aventurero está llena (Max 10 slots)."}, status=400)
                InventorySlot.objects.create(
                    adventurer=target_adv, item=slot.item, guild=None, quantity=1)

        elif action == "equip":
            if not slot.adventurer:
                return Response({"error": "Mueve el objeto a la mochila del aventurero primero."}, status=400)
            adv = slot.adventurer
            item = slot.item
            if not is_class_allowed(adv, item):
                return Response({"error": "Incompatible con su clase."}, status=400)
            if item.item_type in ['CNS', 'MSC']:
                return Response({"error": "No puedes equipar esto."}, status=400)

            slot_map = {
                'W1H': 'equip_main_hand', 'W2H': 'equip_main_hand', 'OFF': 'equip_off_hand',
                'HED': 'equip_head', 'TRS': 'equip_torso', 'LEG': 'equip_legs', 'LGS': 'equip_legs',
                'HND': 'equip_hands', 'FET': 'equip_feet', 'NCK': 'equip_necklace',
                'BRC': 'equip_bracelet', 'EAR': 'equip_earring'
            }
            attr_name = slot_map.get(item.item_type)
            if item.item_type == 'RNG':
                attr_name = 'equip_ring_1' if not adv.equip_ring_1 else 'equip_ring_2'

            old_item = getattr(adv, attr_name)
            setattr(adv, attr_name, item)
            adv.save()

            if old_item:
                from .engine import add_item_to_inventory
                add_item_to_inventory(adv, old_item)

            slot.quantity -= 1
            if slot.quantity <= 0:
                slot.delete()
            else:
                slot.save()
            return Response({"status": "success", "message": f"{item.name} equipado."})

        elif action == "sell":
            # Extrae el valor del objeto y lo inyecta al Gremio
            item = slot.item
            guild.iron_half_penny += item.cost_iron_half_penny
            guild.iron_penny += item.cost_iron_penny
            guild.ardite += item.cost_ardite
            guild.drabin += item.cost_drabin
            guild.copper_penny += item.cost_copper_penny
            guild.iota += item.cost_iota
            guild.silver_penny += item.cost_silver_penny
            guild.sueldo += item.cost_sueldo
            guild.talento += item.cost_talento
            guild.real += item.cost_real
            guild.marco += item.cost_marco
            guild.save()
            universal_consolidate(guild)  # Ordena el dinero automáticamente

        if action in ["to_guild", "to_adv", "sell"]:
            slot.quantity -= 1
            if slot.quantity <= 0:
                slot.delete()
            else:
                slot.save()

        return Response({"status": "success", "message": "Acción completada."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
def list_charts(request):
    """Devuelve todos los gráficos activos y sus coordenadas ordenadas."""
    charts = CustomChart.objects.filter(is_active=True).order_by('created_at')

    if not charts.exists():
        default_chart = CustomChart.objects.create(
            title="Horas de Deep Work",
            y_axis_label="Horas", x_axis_label="Día del Mes",
            x_min=1.0, goal_x_value=30, y_min=0.0, y_max=6.0
        )
        charts = [default_chart]

    data = []
    for c in charts:
        points = c.data_points.all().order_by('x_value')
        completion = get_chart_completion_status(c)
        data.append({
            "id": c.id, "title": c.title,
            "x_label": c.x_axis_label, "y_label": c.y_axis_label,
            "x_min": c.x_min, "goal_x": c.goal_x_value,
            "y_min": c.y_min, "y_max": c.y_max,
            "polarity": c.get_polarity_display(),
            "x_data": [p.x_value for p in points],
            "y_data": [p.y_value for p in points],
            "covered_count": completion["covered_count"],
            "total_expected": completion["total_expected"],
            "missing_points": completion["missing"],
            "is_complete": completion["is_complete"],
        })
    return Response({"charts": data})


@api_view(['POST'])
def add_chart_point(request):
    """Añade o actualiza una coordenada (X, Y) en un gráfico específico."""
    chart_id = request.data.get('chart_id')
    try:
        x_raw = request.data.get('x_value')
        y_val = float(request.data.get('y_value'))

        # Validar que X sea un número entero
        x_val = float(x_raw)
        if x_val != int(x_val):
            return Response({"error": f"El valor del eje X debe ser un número entero (recibido: {x_raw})."}, status=400)
        x_val = int(x_val)

        chart = CustomChart.objects.get(id=chart_id)

        # Validar que X esté dentro del rango del gráfico
        if x_val < int(chart.x_min) or x_val > chart.goal_x_value:
            return Response(
                {"error": f"El valor X={x_val} está fuera del rango [{int(chart.x_min)}, {chart.goal_x_value}]."},
                status=400
            )

        # update_or_create permite sobreescribir si te equivocaste de valor en un día
        point, created = ChartDataPoint.objects.update_or_create(
            chart=chart, x_value=float(x_val),
            defaults={'y_value': y_val}
        )
        msg = "Punto añadido." if created else "Punto actualizado."

        # Verificar si el gráfico quedó completo tras este punto
        completion = get_chart_completion_status(chart)
        return Response({
            "status": "success",
            "message": msg,
            "chart_complete": completion["is_complete"],
            "covered_count": completion["covered_count"],
            "total_expected": completion["total_expected"]
        })
    except CustomChart.DoesNotExist:
        return Response({"error": "Gráfico no encontrado."}, status=404)
    except (ValueError, TypeError) as e:
        return Response({"error": f"Valores numéricos inválidos: {e}"}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['POST'])
def create_chart(request):
    """Permite crear un nuevo lienzo de tracking con límites absolutos."""
    try:
        chart = CustomChart.objects.create(
            title=request.data.get('title', 'Nuevo Tracker'),
            y_axis_label=request.data.get('y_label', 'Valor'),
            x_axis_label=request.data.get('x_label', 'Día'),
            x_min=float(request.data.get('x_min', 1.0)),
            goal_x_value=int(request.data.get('goal_x', 30)),
            y_min=float(request.data.get('y_min', 0.0)),
            y_max=float(request.data.get('y_max', 10.0)),
            polarity=request.data.get('polarity', 'POS')
        )
        return Response({"status": "success", "message": f"Gráfico '{chart.title}' creado."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['DELETE'])
def delete_chart(request, chart_id):
    """Elimina un gráfico por completo (y todos sus puntos)."""
    try:
        chart = CustomChart.objects.get(id=chart_id)
        # Protege el gráfico base para que el sistema no se quede sin lienzos
        if chart.id == 1 and CustomChart.objects.count() == 1:
            return Response({"error": "No puedes borrar tu único gráfico."}, status=400)

        title = chart.title
        chart.delete()  # borra en cascada los ChartDataPoint asociados
        return Response({"status": "success", "message": f"Gráfico '{title}' eliminado."})
    except CustomChart.DoesNotExist:
        return Response({"error": "Gráfico no encontrado."}, status=404)


@api_view(['DELETE'])
def delete_habit(request, habit_id):
    try:
        DailyHabit.objects.get(id=habit_id).delete()
        return Response({"status": "success", "message": "Hábito eliminado del tablón."})
    except DailyHabit.DoesNotExist:
        return Response({"status": "error", "message": "Hábito no encontrado."}, status=404)


@api_view(['POST'])
def undo_habit(request):
    habit_id = request.data.get('habit_id')
    today = timezone.localdate()
    try:
        habit = DailyHabit.objects.get(id=habit_id)
        if habit.last_completed_date != today:
            return Response({"status": "error", "message": "Solo puedes deshacer acciones de hoy."}, status=400)

        guild, _ = GuildProfile.objects.get_or_create(id=1)

        if habit.is_bad_habit:
            # Devuelve el prestigio restado por error
            guild.add_prestige(habit.last_prestige_reward)
        else:
            # Quita el prestigio y monedas ganadas por error
            guild.add_prestige(-habit.last_prestige_reward)
            if habit.last_coin_type:
                curr_coin = getattr(guild, habit.last_coin_type)
                setattr(guild, habit.last_coin_type, max(
                    0, curr_coin - habit.last_coin_amount))

        guild.save()
        habit.current_streak = habit.previous_streak
        habit.last_completed_date = today - timedelta(days=1)
        habit.save()

        return Response({"status": "success", "message": f"Acción en '{habit.name}' revertida."})
    except DailyHabit.DoesNotExist:
        return Response({"status": "error", "message": "Hábito no encontrado."}, status=404)


@api_view(['POST'])
def claim_chart_reward(request):
    chart_id = request.data.get('chart_id')
    try:
        chart = CustomChart.objects.get(id=chart_id)
        result = calculate_chart_reward(chart)
        return Response(result)
    except CustomChart.DoesNotExist:
        return Response({"status": "error", "message": "Gráfico no encontrado."}, status=404)


@api_view(['POST'])
def unequip_item(request, adv_id):
    """Quita un objeto del cuerpo y lo guarda en la mochila (si hay espacio)."""
    slot_type = request.data.get('slot_type')
    try:
        adv = Adventurer.objects.get(id=adv_id)
        item = getattr(adv, slot_type)
        if not item:
            return Response({"error": "Ranura vacía."}, status=400)

        if adv.inventory.count() >= adv.inventory_capacity:
            return Response({"error": "Mochila llena. Vende o guarda algo en el Cofre."}, status=400)

        setattr(adv, slot_type, None)
        adv.save()

        from .engine import add_item_to_inventory
        add_item_to_inventory(adv, item)
        return Response({"status": "success", "message": f"{item.name} desequipado."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
def list_journal(request):
    """Obtiene todas las entradas del diario ordenadas cronológicamente."""
    entries = JournalEntry.objects.all().order_by('created_at')
    data = []

    for e in entries:
        # Convierte a la zona horaria local
        local_dt = timezone.localtime(e.created_at)
        timestamp = local_dt.strftime('%d/%m/%Y - %H:%M hrs')
        data.append({
            "id": e.id,
            "content": e.content,
            "timestamp": timestamp
        })
    return Response({"entries": data})


@api_view(['POST'])
def create_journal_entry(request):
    """Guarda una nueva página y otorga un buff al Gremio."""
    content = request.data.get('content')
    if not content:
        return Response({"error": "La página no puede estar vacía."}, status=400)

    # --- Buff de Claridad Mental ---
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    leveled_up = guild.add_prestige(2)
    lvl_msg = f" ¡El Gremio ascendió al Nivel {guild.prestige_level}!" if leveled_up else ""

    JournalEntry.objects.create(content=content)
    return Response({
        "status": "success",
        "message": f"Pensamiento sellado en el Diario (+2 Prestigio).{lvl_msg}"
    })


@api_view(['GET'])
def list_upgrades(request):
    """Devuelve el catálogo de mejoras cruzado con lo que el gremio ya compró."""
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    upgrades = GuildUpgrade.objects.all().order_by('req_prestige_level')
    unlocked_keys = set(GuildUnlockedUpgrade.objects.filter(
        guild=guild).values_list('upgrade__key', flat=True))

    data = []
    for u in upgrades:
        if u.key in unlocked_keys:
            status_str = "Adquirido"
        elif guild.prestige_level < u.req_prestige_level:
            status_str = "Bloqueado"
        else:
            status_str = "Disponible"

        data.append({
            "key": u.key,
            "name": u.name,
            "description": u.description,
            "cost_coin": u.cost_coin.title(),
            "cost_amount": u.cost_amount,
            "req_level": u.req_prestige_level,
            "status": status_str
        })
    return Response({"upgrades": data})


@api_view(['POST'])
def buy_upgrade(request):
    """Procesa la compra de una mejora de infraestructura."""
    key = request.data.get('key')
    guild, _ = GuildProfile.objects.get_or_create(id=1)

    try:
        upgrade = GuildUpgrade.objects.get(key=key)
    except GuildUpgrade.DoesNotExist:
        return Response({"error": "Mejora no encontrada."}, status=404)

    if GuildUnlockedUpgrade.objects.filter(guild=guild, upgrade=upgrade).exists():
        return Response({"error": "Ya posees esta mejora."}, status=400)

    if guild.prestige_level < upgrade.req_prestige_level:
        return Response({"error": f"Requiere Gremio Nivel {upgrade.req_prestige_level}."}, status=400)

    curr_coins = getattr(guild, upgrade.cost_coin)
    if curr_coins < upgrade.cost_amount:
        return Response({"error": f"Fondos insuficientes. Cuesta {upgrade.cost_amount} {upgrade.cost_coin.title()}."}, status=400)

    # Descuenta los fondos y registra la compra
    setattr(guild, upgrade.cost_coin, curr_coins - upgrade.cost_amount)
    guild.save()
    universal_consolidate(guild)
    GuildUnlockedUpgrade.objects.create(guild=guild, upgrade=upgrade)

    return Response({"status": "success", "message": f"¡Mejora '{upgrade.name}' adquirida!"})


# --- KANBAN ---

@api_view(['GET'])
def list_kanban(request):
    """Lista el tablero Kanban con sus columnas y tareas. Crea uno por defecto si no existe."""
    from .models import KanbanBoard, KanbanColumn, KanbanTask
    board = KanbanBoard.objects.first()
    if not board:
        board = KanbanBoard.objects.create(name="Tablero Principal")
        KanbanColumn.objects.create(board=board, title="Por Hacer", position=0, color="yellow")
        KanbanColumn.objects.create(board=board, title="En Progreso", position=1, color="cyan")
        KanbanColumn.objects.create(board=board, title="Completado", position=2, color="green")

    columns = board.columns.all().order_by('position')
    data = {
        "board_id": board.id,
        "board_name": board.name,
        "columns": []
    }
    for col in columns:
        tasks = col.tasks.all()
        col_data = {
            "id": col.id,
            "title": col.title,
            "position": col.position,
            "color": col.color,
            "tasks": [{
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.get_priority_display(),
                "priority_code": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "prestige_reward": t.prestige_reward,
            } for t in tasks]
        }
        data["columns"].append(col_data)

    return Response(data)


@api_view(['POST'])
def create_kanban_column(request):
    """Crea una nueva columna en el tablero."""
    from .models import KanbanBoard, KanbanColumn
    board = KanbanBoard.objects.first()
    if not board:
        return Response({"error": "No hay tablero."}, status=400)

    title = request.data.get('title', 'Nueva Columna')
    color = request.data.get('color', 'white')
    max_pos = board.columns.count()
    KanbanColumn.objects.create(board=board, title=title, position=max_pos, color=color)
    return Response({"status": "success", "message": f"Columna '{title}' creada."})


@api_view(['POST'])
def create_kanban_task(request):
    """Crea una tarea nueva en la primera columna (Por Hacer)."""
    from .models import KanbanColumn, KanbanTask, TaskPriority
    column_id = request.data.get('column_id')

    try:
        if column_id:
            column = KanbanColumn.objects.get(id=column_id)
        else:
            column = KanbanColumn.objects.order_by('position').first()
            if not column:
                return Response({"error": "Crea al menos una columna primero."}, status=400)

        priority = request.data.get('priority', 'MED')
        prestige_map = {'CRT': 75, 'HGH': 35, 'MED': 15, 'LOW': 5}

        due_date = request.data.get('due_date')
        task = KanbanTask.objects.create(
            column=column,
            title=request.data.get('title', 'Nueva Tarea'),
            description=request.data.get('description', ''),
            priority=priority,
            due_date=due_date if due_date else None,
            prestige_reward=prestige_map.get(priority, 5)
        )
        return Response({"status": "success", "message": f"Tarea '{task.title}' creada."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['POST'])
def move_kanban_task(request):
    """Mueve una tarea a otra columna. Si llega a la última, otorga prestigio."""
    from .models import KanbanTask, KanbanColumn
    task_id = request.data.get('task_id')
    direction = request.data.get('direction', 'right')  # 'right' o 'left'

    try:
        task = KanbanTask.objects.get(id=task_id)
        current_col = task.column
        board = current_col.board
        columns = list(board.columns.all().order_by('position'))
        current_idx = next(i for i, c in enumerate(columns) if c.id == current_col.id)

        if direction == 'right':
            if current_idx >= len(columns) - 1:
                return Response({"status": "warning", "message": "Ya está en la última columna."})
            new_col = columns[current_idx + 1]
        else:
            if current_idx <= 0:
                return Response({"status": "warning", "message": "Ya está en la primera columna."})
            new_col = columns[current_idx - 1]

        task.column = new_col
        msg = f"'{task.title}' movida a '{new_col.title}'."

        # Si llega a la última columna, completar y dar prestigio
        if new_col.id == columns[-1].id and not task.completed_at:
            task.completed_at = timezone.now()
            guild, _ = GuildProfile.objects.get_or_create(id=1)
            
            reward_msg = f"+{task.prestige_reward} Prestigio"
            if task.priority == 'LOW':
                guild.silver_penny += 1
                reward_msg += ", +1 Penique de Plata"
            elif task.priority == 'MED':
                guild.sueldo += 2
                guild.silver_penny += 1
                reward_msg += ", +2 Sueldos, +1 Penique de Plata"
            elif task.priority == 'HGH':
                guild.real += 1
                guild.sueldo += 5
                reward_msg += ", +1 Real, +5 Sueldos"
            elif task.priority == 'CRT':
                guild.talento += 1
                guild.real += 2
                reward_msg += ", +1 Talento, +2 Reales"

            leveled_up = guild.add_prestige(task.prestige_reward)
            lvl_msg = f" ¡El Gremio ascendió al Nivel {guild.prestige_level}!" if leveled_up else ""
            msg = f"¡Tarea '{task.title}' completada! {reward_msg}.{lvl_msg}"

        # Si se mueve de vuelta desde la última columna, quitar completado
        elif new_col.id != columns[-1].id and task.completed_at:
            task.completed_at = None

        task.save()
        return Response({"status": "success", "message": msg})
    except KanbanTask.DoesNotExist:
        return Response({"error": "Tarea no encontrada."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
@api_view(['PUT'])
def edit_kanban_task(request, task_id):
    """Edita una tarea existente del tablero."""
    from .models import KanbanTask
    try:
        task = KanbanTask.objects.get(id=task_id)
        task.title = request.data.get('title', task.title)
        task.description = request.data.get('description', task.description)
        task.priority = request.data.get('priority', task.priority)
        due_date = request.data.get('due_date')
        if due_date is not None:
            task.due_date = due_date if due_date else None
        task.save()
        return Response({"status": "success", "message": f"Tarea '{task.title}' editada."})
    except KanbanTask.DoesNotExist:
        return Response({"error": "Tarea no encontrada."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)



@api_view(['DELETE'])
def delete_kanban_task(request, task_id):
    """Elimina una tarea del tablero."""
    from .models import KanbanTask
    try:
        task = KanbanTask.objects.get(id=task_id)
        title = task.title
        task.delete()
        return Response({"status": "success", "message": f"Tarea '{title}' eliminada."})
    except KanbanTask.DoesNotExist:
        return Response({"error": "Tarea no encontrada."}, status=404)


@api_view(['DELETE'])
def delete_kanban_column(request, col_id):
    """Elimina una columna y todas sus tareas."""
    from .models import KanbanColumn
    try:
        col = KanbanColumn.objects.get(id=col_id)
        if col.board.columns.count() <= 1:
            return Response({"error": "No puedes borrar tu última columna."}, status=400)
        title = col.title
        col.delete()
        return Response({"status": "success", "message": f"Columna '{title}' eliminada."})
    except KanbanColumn.DoesNotExist:
        return Response({"error": "Columna no encontrada."}, status=404)


# --- CALENDARIO ---

@api_view(['GET'])
def list_calendar_events(request, year, month):
    """Lista todos los eventos de un mes específico."""
    from .models import CalendarEvent
    events = CalendarEvent.objects.filter(date__year=year, date__month=month)
    data = [{
        "id": e.id,
        "date": e.date.isoformat(),
        "title": e.title,
        "description": e.description,
        "is_important": e.is_important,
        "color": e.color,
    } for e in events]
    return Response({"events": data, "year": year, "month": month})


@api_view(['POST'])
def create_calendar_event(request):
    """Crea un evento en el calendario. +1 Prestigio por organizar."""
    from .models import CalendarEvent
    try:
        from datetime import date as dt_date
        date_str = request.data.get('date')
        event = CalendarEvent.objects.create(
            date=dt_date.fromisoformat(date_str),
            title=request.data.get('title', 'Evento'),
            description=request.data.get('description', ''),
            is_important=request.data.get('is_important', False),
            color=request.data.get('color', 'white')
        )

        # Buff de prestigio por planificar
        guild, _ = GuildProfile.objects.get_or_create(id=1)
        prestige_gain = 3 if event.is_important else 1
        guild.add_prestige(prestige_gain)

        return Response({"status": "success", "message": f"Evento '{event.title}' creado (+{prestige_gain} Prestigio)."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)
@api_view(['PUT'])
def edit_calendar_event(request, event_id):
    """Edita un evento existente del calendario."""
    from .models import CalendarEvent
    from datetime import date as dt_date
    try:
        event = CalendarEvent.objects.get(id=event_id)
        date_str = request.data.get('date')
        if date_str:
            event.date = dt_date.fromisoformat(date_str)
        event.title = request.data.get('title', event.title)
        event.description = request.data.get('description', event.description)
        if 'is_important' in request.data:
            event.is_important = request.data.get('is_important')
        event.color = request.data.get('color', event.color)
        event.save()
        return Response({"status": "success", "message": f"Evento '{event.title}' editado."})
    except CalendarEvent.DoesNotExist:
        return Response({"error": "Evento no encontrado."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)



@api_view(['DELETE'])
def delete_calendar_event(request, event_id):
    """Elimina un evento del calendario."""
    from .models import CalendarEvent
    try:
        event = CalendarEvent.objects.get(id=event_id)
        title = event.title
        event.delete()
        return Response({"status": "success", "message": f"Evento '{title}' eliminado."})
    except CalendarEvent.DoesNotExist:
        return Response({"error": "Evento no encontrado."}, status=404)

