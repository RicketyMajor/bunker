from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import GuildProfile, Adventurer, DeepWorkSession, AdventurerClass, AdventurerRace, AdventurerGender
import random
from .engine import process_session_completion, generate_session_script, consolidate_wealth, distribute_random_stats


@api_view(['GET'])
def guild_status(request):
    """Devuelve el estado general del Gremio y la lista de aventureros con sus stats de RPG."""
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    adventurers = Adventurer.objects.all()

    adv_data = []
    for adv in adventurers:
        adv_data.append({
            "id": adv.id,
            "name": adv.name,
            "class_name": adv.get_adv_class_display(),
            "race": adv.get_race_display(),
            "level": adv.level,
            "xp": adv.experience,
            "is_recovering": adv.is_recovering,
            "wealth": {
                "iron_half_penny": adv.iron_half_penny, "iron_penny": adv.iron_penny,
                "ardite": adv.ardite, "drabin": adv.drabin, "copper_penny": adv.copper_penny,
                "iota": adv.iota, "silver_penny": adv.silver_penny, "sueldo": adv.sueldo,
                "talento": adv.talento, "real": adv.real, "marco": adv.marco
            },
            "wealth_summary": f"{adv.talento}T, {adv.iota}i, {adv.ardite}a",
            # --- STATS Y VIDA ---
            "str": adv.base_str, "dex": adv.base_dex, "con": adv.base_con,
            "int": adv.base_int, "wis": adv.base_wis, "cha": adv.base_cha, "luk": adv.base_luk,
            "hp": adv.current_hp, "max_hp": adv.max_hp,

            # --- INVENTARIO (8 SLOTS) ---
            "equip_main_hand": adv.equip_main_hand.name if adv.equip_main_hand else "Desarmado",
            "equip_off_hand": adv.equip_off_hand.name if adv.equip_off_hand else "Vacío",
            "equip_head": adv.equip_head.name if adv.equip_head else "Vacío",
            "equip_torso": adv.equip_torso.name if adv.equip_torso else "Ropa común",
            "equip_hands": adv.equip_hands.name if adv.equip_hands else "Vacío",
            "equip_legs": adv.equip_legs.name if adv.equip_legs else "Vacío",
            "equip_feet": adv.equip_feet.name if adv.equip_feet else "Vacío",
            "equip_accessory": adv.equip_accessory.name if adv.equip_accessory else "Ninguno"
        })

    guild_data = {
        "level": guild.level,
        "xp": guild.experience,
        "net_worth_talents": guild.net_worth_in_talents,
        "inventory": {
            "iron_half_penny": guild.iron_half_penny,
            "iron_penny": guild.iron_penny,
            "ardite": guild.ardite,
            "drabin": guild.drabin,
            "copper_penny": guild.copper_penny,
            "iota": guild.iota,
            "silver_penny": guild.silver_penny,
            "sueldo": guild.sueldo,
            "talento": guild.talento,
            "real": guild.real,
            "marco": guild.marco
        }
    }

    return Response({
        "guild": guild_data,
        "adventurers": adv_data
    })


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

    # SISTEMA DE LÍMITE: 1 cupo por cada Nivel del Gremio
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

    # Si es tu primer avatar manual (sin stats), el destino reparte los 13 pts.
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
