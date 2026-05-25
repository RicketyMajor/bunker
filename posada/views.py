from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import GuildProfile, Adventurer, DeepWorkSession, AdventurerClass, AdventurerRace, AdventurerGender, DailyHabit, DailyStatistic, HabitDifficulty, InventorySlot, ItemRarity, CustomChart, ChartDataPoint, ChartPolarity, JournalEntry, Item, GuildUpgrade, GuildUnlockedUpgrade
import random
from .engine import process_session_completion, generate_session_script, consolidate_wealth, distribute_random_stats, evaluate_daily_penalties, universal_consolidate, calculate_chart_reward, is_class_allowed, get_derived_skills
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
        "prestige_meta": guild.prestige_level * 100,
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
    if Adventurer.objects.count() >= guild.level:
        return Response({
            "status": "error",
            "message": f"Gremio Nv. {guild.level} lleno. Estudia y sube de nivel para tener más cupos."
        }, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    stats = data.get('stats', None)

    adv = Adventurer.objects.create(
        name=data.get('name', 'Aventurero Desconocido'),
        adv_class=data.get('adv_class', 'FTR'),
        race=data.get('race', 'HUM'),
        gender=data.get('gender', 'O'),
        max_hp=25,
        current_hp=25,
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
    """Genera 3 reclutas procedurales con nombres y stats aleatorios."""
    prefixes = ["Thor", "Grim", "Ar", "Leg", "Kvoth", "El",
                "Fae", "Gael", "Bae", "Mor", "Dae", "Val", "Gim"]
    suffixes = ["din", "gar", "agorn", "olas", "e", "rond",
                "lin", "dor", "th", "gan", "mon", "ria", "li"]

    recruits = []
    for _ in range(3):
        # Generación de Identidad
        name = random.choice(prefixes) + random.choice(suffixes)
        adv_class_obj = random.choice(AdventurerClass.choices)
        race_obj = random.choice(AdventurerRace.choices)
        gender_obj = random.choice(AdventurerGender.choices)

        # Reparto Procedural de los 13 Puntos Base
        stats = {'str': 0, 'dex': 0, 'con': 0,
                 'int': 0, 'wis': 0, 'cha': 0, 'luk': 0}
        keys = list(stats.keys())
        for _ in range(13):
            stats[random.choice(keys)] += 1

        recruits.append({
            "name": name,
            "adv_class": adv_class_obj[0],
            "adv_class_display": adv_class_obj[1],
            "race": race_obj[0],
            "race_display": race_obj[1],
            "gender": gender_obj[0],
            "stats": stats
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


@api_view(['GET'])
def list_habits(request):
    """Lista todos los hábitos y evalúa penalizaciones de días anteriores."""
    # Al consultar el tablón, el motor revisa si hay deudas de días pasados
    penalties = evaluate_daily_penalties()

    today = timezone.now().date()
    habits = DailyHabit.objects.all()

    habit_list = []
    for h in habits:
        habit_list.append({
            "id": h.id, "name": h.name, "difficulty": h.get_difficulty_display(),
            "completed_today": h.last_completed_date == today,
            "current_streak": h.current_streak,
            "is_bad_habit": h.is_bad_habit
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
    today = timezone.now().date()
    habit_id = request.data.get('habit_id')

    try:
        habit = DailyHabit.objects.get(id=habit_id)
        if habit.last_completed_date == today:
            return Response({"status": "warning", "message": "Ya interactuaste con este hábito hoy."})

        guild, _ = GuildProfile.objects.get_or_create(id=1)
        rewards = {
            'S': {'prestige': 50, 'coin': 'iota', 'amt': 1},
            'A': {'prestige': 25, 'coin': 'copper_penny', 'amt': 5},
            'B': {'prestige': 10, 'coin': 'copper_penny', 'amt': 2},
            'C': {'prestige': 5,  'coin': 'ardite', 'amt': 5},
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

            old_level = guild.prestige_level
            guild.prestige += r['prestige']
            setattr(guild, r['coin'], getattr(guild, r['coin']) + r['amt'])

            while True:
                meta = guild.prestige_level * 100
                if guild.prestige >= meta:
                    guild.prestige -= meta
                    guild.prestige_level += 1
                else:
                    break

            guild.save()
            habit.last_completed_date = today
            habit.save()

            lvl_msg = f" ¡El Gremio ascendió al Nivel {guild.prestige_level}!" if guild.prestige_level > old_level else ""

            # --- LÓGICA DEL TABLÓN PATROCINADO ---
            drop_msg = ""
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
                        drop_msg = f"\n¡El Tablón Patrocinado te envió [[{color}]{drop.name}[/]] al cofre!"

            return Response({"status": "success", "message": f"¡'{habit.name}' completado! +{r['prestige']} Prestigio.{lvl_msg}{drop_msg}"})

    except DailyHabit.DoesNotExist:
        return Response({"status": "error", "message": "Hábito no encontrado."})


@api_view(['GET'])
def get_stats_data(request):
    """Extrae los últimos 30 días de actividad para el gráfico."""
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
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
            "stats": f"DMG:{s.item.bonus_damage} | ARM:{s.item.bonus_armor}"
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
                'HED': 'equip_head', 'TRS': 'equip_torso', 'LEG': 'equip_legs',
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
        data.append({
            "id": c.id, "title": c.title,
            "x_label": c.x_axis_label, "y_label": c.y_axis_label,
            "x_min": c.x_min, "goal_x": c.goal_x_value,
            "y_min": c.y_min, "y_max": c.y_max,
            "polarity": c.get_polarity_display(),
            "x_data": [p.x_value for p in points],
            "y_data": [p.y_value for p in points],
        })
    return Response({"charts": data})


@api_view(['POST'])
def add_chart_point(request):
    """Añade o actualiza una coordenada (X, Y) en un gráfico específico."""
    chart_id = request.data.get('chart_id')
    try:
        x_val = float(request.data.get('x_value'))
        y_val = float(request.data.get('y_value'))

        chart = CustomChart.objects.get(id=chart_id)

        # update_or_create permite sobreescribir si te equivocaste de valor en un día
        point, created = ChartDataPoint.objects.update_or_create(
            chart=chart, x_value=x_val,
            defaults={'y_value': y_val}
        )
        msg = "Punto añadido." if created else "Punto actualizado."
        return Response({"status": "success", "message": msg})
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
    today = timezone.now().date()
    try:
        habit = DailyHabit.objects.get(id=habit_id)
        if habit.last_completed_date != today:
            return Response({"status": "error", "message": "Solo puedes deshacer acciones de hoy."}, status=400)

        guild, _ = GuildProfile.objects.get_or_create(id=1)

        if habit.is_bad_habit:
            # Devuelve el prestigio restado por error
            guild.prestige += habit.last_prestige_reward
        else:
            # Quita el prestigio y monedas ganadas por error
            guild.prestige -= habit.last_prestige_reward
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
    guild.prestige += 2

    # Verifica si la claridad mental subió de nivel al gremio
    lvl_msg = ""
    old_level = guild.prestige_level
    while True:
        meta = guild.prestige_level * 100
        if guild.prestige >= meta:
            guild.prestige -= meta
            guild.prestige_level += 1
        else:
            break

    guild.save()
    if guild.prestige_level > old_level:
        lvl_msg = f" ¡El Gremio ascendió al Nivel {guild.prestige_level}!"

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
