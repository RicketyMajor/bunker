from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import GuildProfile, Adventurer, DeepWorkSession
from .engine import process_session_completion


@api_view(['GET'])
def guild_status(request):
    """Devuelve el estado general del Gremio y la lista de aventureros."""
    # Obtiene o crea al Maestro del Gremio (Usuario)
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
            # Un pequeño resumen numérico de su riqueza para la tabla
            "wealth_summary": f"{adv.iota} iotas, {adv.copper_penny} cp"
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
def complete_session(request):
    """Recibe los datos de la TUI, crea la sesión y dispara el motor RPG."""
    data = request.data
    duration = data.get('duration_minutes', 25)
    category = data.get('category', 'General')
    adventurer_ids = data.get('adventurer_ids', [])

    # Crea la sesión inicial (aún no completada)
    session = DeepWorkSession.objects.create(
        duration_minutes=duration,
        category=category,
        completed=False
    )

    # Asigna a la Party que se eligió en la TUI
    if adventurer_ids:
        adventurers = Adventurer.objects.filter(id__in=adventurer_ids)
        session.adventurers_involved.set(adventurers)
        session.save()

    # motor
    result = process_session_completion(session.id)

    if result.get("status") == "error":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    # Devuelve el botín, la XP y el log (MUD Log) a la terminal
    return Response({
        "status": "success",
        "message": "Expedición finalizada con éxito.",
        "log": session.event_log,
        "engine_details": result
    })
