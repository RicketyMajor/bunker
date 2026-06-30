import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .models import GuildProfile, Adventurer, DeepWorkSession, Item, DailyHabit, DailyStatistic, InventorySlot, Monster, ItemRarity, CustomChart, ChartDataPoint, GuildUpgrade, JournalEntry, CalendarEvent
from .skills import SkillRegistry

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


def generate_session_script(session_id, duration_minutes, adventurers_qs):
    random.seed(session_id)
    class ScriptList(list):
        def append(self, item):
            try:
                item["state"] = state
            except NameError:
                item["state"] = "EXPLORING"
            super().append(item)
    script = ScriptList()
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
    temp_hp = {adv.id: adv.current_hp for adv in adventurers}

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
            current_second += 30
            if current_second >= total_seconds:
                break

            # Elige un aventurero al azar solo para eventos narrativos de consumibles
            flavor_adv = random.choice(adventurers)

            # --- MICRO-EVENTOS NARRATIVOS DE EXPLORACIÓN ---
            if random.random() < 0.25:  # 25% de probabilidad de suceso narrativo
                event_adv = random.choice(adventurers)
                skills = get_derived_skills(event_adv)

                event_texts = {
                    "Atletismo": [
                        ("escalar un muro de roca suelta", "llega a la cima demostrando una fuerza bruta envidiable", "resbala y cae torpemente de espaldas"),
                        ("mover una pesada columna caída", "la levanta con un rugido monumental de esfuerzo", "termina con un tirón muscular y la columna ni se mueve"),
                        ("saltar sobre una profunda grieta", "cae firmemente al otro lado y sigue corriendo", "se queda corto y debe trepar agónicamente"),
                    ],
                    "Sigilo": [
                        ("moverse sin hacer ruido entre la maleza", "pasa como una sombra indetectable", "pisa una rama seca que hace eco en toda la cueva"),
                        ("pasar junto a unos guardias distraídos", "se desliza sin que ni siquiera sientan su presencia", "tira una jarra de metal por error"),
                        ("esconderse detrás de unas cajas", "se funde perfectamente con las sombras del lugar", "deja medio cuerpo a la vista como un novato"),
                    ],
                    "Percepción": [
                        ("agudizar sus sentidos buscando peligros", "nota unas tenues marcas de garras en la pared", "solo logra ver formas confusas en la oscuridad"),
                        ("escuchar a través de una puerta de madera", "distingue los pasos pesados de una bestia del otro lado", "solo escucha su propio zumbido en los oídos"),
                        ("revisar el techo en busca de amenazas", "avista a una criatura acechando entre estalactitas", "el polvo le entra a los ojos y no ve nada"),
                    ],
                    "Acrobacias": [
                        ("cruzar un abismo sobre un tronco húmedo", "mantiene un equilibrio perfecto como un felino", "casi cae al vacío, recuperándose a duras penas"),
                        ("deslizarse por debajo de una rampa", "pasa con elegancia rozando el suelo", "se atasca de hombros a la mitad del camino"),
                        ("esquivar una trampa de cuchillas", "hace una voltereta grácil y sale ileso", "tropieza de boca y por suerte la cuchilla falla"),
                    ],
                    "Supervivencia": [
                        ("buscar rastros frescos en la tierra", "identifica claramente hacia dónde fueron los monstruos", "pierde el rastro en el fango denso"),
                        ("buscar bayas para recuperar energías", "encuentra frutos nutritivos en un arbusto", "se pincha con espinas tóxicas y no saca nada"),
                        ("orientarse en la laberíntica cueva", "deduce correctamente el camino hacia el norte", "acaba dando un giro en círculos de 360 grados"),
                    ],
                    "Arcano": [
                        ("intentar descifrar unas runas brillantes", "comprende el flujo de magia antigua", "le da dolor de cabeza al intentar leerlas"),
                        ("identificar el origen de un aura mágica", "descubre la esencia evocadora del hechizo", "confunde la magia y siente pánico inútil"),
                        ("detectar una ilusión en el pasillo", "parpadea y ve a través del engaño", "cree ciegamente en la falsa pared de ladrillos"),
                    ],
                    "Juego de Manos": [
                        ("intentar forzar el cerrojo de un cofre viejo", "lo abre con un click maestro", "rompe su ganzúa dentro de la cerradura"),
                        ("robar la llave del cinturón de un guardia dormido", "la obtiene suavemente con dos dedos", "hace tintinear las llaves despertando al guardia (casi)"),
                        ("esconder un objeto valioso en su bota", "lo hace en un parpadeo mágico", "se le cae al suelo ruidosamente"),
                    ],
                    "Historia": [
                        ("recordar a qué dinastía pertenece una estatua", "recuerda exactamente el nombre del rey antiguo", "la estatua está demasiado desgastada para saberlo"),
                        ("hacer memoria sobre la guerra en este lugar", "deduce las tácticas que usaron los caídos", "mezcla leyendas con hechos y se confunde"),
                        ("identificar un blasón en un escudo roto", "reconoce la noble familia extinta", "lo confunde con un garabato sin sentido"),
                    ],
                    "Religión": [
                        ("identificar un altar profano", "reconoce los símbolos impíos de inmediato", "siente un escalofrío pero no logra descifrar nada"),
                        ("rezar para apartar espíritus oscuros", "su deidad lo protege y el aire se purifica", "las deidades oscuras se ríen de su torpeza"),
                        ("recordar el mito de creación del dios local", "recita un pasaje que revela un secreto de la cueva", "no puede recordar más allá de cantos de taberna"),
                    ],
                    "Medicina": [
                        ("evaluar unas extrañas plantas pálidas", "descubre que sus hojas son cicatrizantes", "cree que son venenosas y prefiere no tocarlas"),
                        ("examinar el cadáver de un aventurero", "determina con precisión cómo murió", "siente náuseas y tiene que apartar la vista"),
                        ("vendar rápidamente un corte menor", "aplica presión y detiene el sangrado maravillosamente", "hace un nudo mal hecho que se deshace"),
                    ],
                    "Naturaleza": [
                        ("identificar a una criatura subterránea", "reconoce sus debilidades y su hábitat", "no logra distinguirla de un animal común"),
                        ("examinar el tipo de piedra de la cueva", "determina que la cueva es volcánica", "no tiene idea de geología"),
                        ("predecir si habrá un sismo por los ruidos", "se siente seguro de que el túnel aguantará", "entra en pánico creyendo que colapsará"),
                    ],
                    "Intimidación": [
                        ("amenazar a las sombras para que huyan", "gruñe y unas pequeñas ratas huyen despavoridas", "pega un grito que se quiebra en un gallo vergonzoso"),
                        ("golpear su arma contra la pared", "las chispas asustan a los murciélagos", "rompe una parte de su empuñadura por bruto"),
                    ],
                    "Investigación": [
                        ("buscar mecanismos ocultos en el suelo", "halla una baldosa que activa una trampa", "solo ve tierra y piedras inútiles"),
                        ("deducir la combinación de un panel", "entiende el patrón lógico enseguida", "presiona botones al azar sin éxito"),
                    ],
                }

                # Elegimos una habilidad que tenga narrativa
                skill_name = random.choice(list(event_texts.keys()))
                action, succ_msg, fail_msg = random.choice(event_texts[skill_name])

                skill_bonus = skills[skill_name]
                dc = random.randint(10, 18)  # Dificultad Dinámica
                roll = roll_d20()["value"]
                total = roll + skill_bonus

                script.append({"second": current_second - 45, "type": "flavor",
                              "message": f"🎲 {event_adv.name} intenta {action} (Chequeo de {skill_name}, CD {dc})."})
                if total >= dc:
                    script.append({"second": current_second - 42, "type": "flavor",
                                  "message": f"   -> ¡ÉXITO! ({roll} + {skill_bonus} = {total}). {event_adv.name} {succ_msg}."})
                else:
                    script.append({"second": current_second - 42, "type": "flavor",
                                  "message": f"   -> FALLO ({roll} + {skill_bonus} = {total}). {event_adv.name} {fail_msg}."})

            # --- EVENTOS DE CONSUMIBLES (INMERSIÓN FLAVOR EXTENDIDA) ---
            if random.random() < 0.15:
                flavor_slots = list(InventorySlot.objects.filter(
                    adventurer=flavor_adv, item__consumable_type__in=['FLV', 'HEL', 'MAN'], quantity__gt=0))
                if flavor_slots:
                    slot = random.choice(flavor_slots)
                    slot.quantity -= 1
                    if slot.quantity <= 0:
                        slot.delete()
                    else:
                        slot.save()
                    
                    item_type = slot.item.consumable_type
                    amt_healed = slot.item.consumable_amount
                    if item_type == 'HEL':
                        temp_hp[flavor_adv.id] = min(flavor_adv.max_hp, temp_hp[flavor_adv.id] + amt_healed)
                    elif item_type == 'MAN' and hasattr(flavor_adv, 'class_resources'):
                        for k in flavor_adv.class_resources:
                            flavor_adv.class_resources[k] += amt_healed


                    item_name = slot.item.name.lower()

                    # --- DICCIONARIO DE INFINITAS ACCIONES MAPPED ---
                    # El motor buscará si el nombre del objeto contiene alguna de estas llaves
                    flavor_database = {
                        "cuerda de escalada mágica": [
                            f"{flavor_adv.name} pronuncia una palabra de mando y la [bold cyan]{slot.item.name}[/bold cyan] se anuda sola en las alturas.",
                            f"{flavor_adv.name} observa cómo la [bold cyan]{slot.item.name}[/bold cyan] trepa por la pared como si fuera una serpiente."
                        ],
                        "cuerda": [
                            f"{flavor_adv.name} desenrolla su [bold cyan]{slot.item.name}[/bold cyan] para asegurar el descenso del grupo por una pendiente.",
                            f"{flavor_adv.name} lanza su [bold cyan]{slot.item.name}[/bold cyan] hacia una saliente alta, trepando para explorar un nivel superior.",
                            f"{flavor_adv.name} usa una [bold cyan]{slot.item.name}[/bold cyan] para amarrar firmemente una puerta sospechosa y evitar emboscadas."
                        ],
                        "ración": [
                            f"{flavor_adv.name} hace una pausa para consumir su [bold cyan]{slot.item.name}[/bold cyan], recuperando aliento.",
                            f"{flavor_adv.name} comparte un pedazo de su [bold cyan]{slot.item.name}[/bold cyan] mientras revisa el mapa de la mazmorra."
                        ],
                        "antorcha": [
                            f"{flavor_adv.name} enciende una [bold cyan]{slot.item.name}[/bold cyan], iluminando rincones oscuros y revelando un pasadizo.",
                            f"{flavor_adv.name} blande su [bold cyan]{slot.item.name}[/bold cyan] encendida para ahuyentar a una bandada de murciélagos molestos."
                        ],
                        "mapa": [
                            f"{flavor_adv.name} extiende un [bold cyan]{slot.item.name}[/bold cyan] antiguo sobre una roca, tratando de orientar la marcha de la party."
                        ],
                        "pala": [
                            f"{flavor_adv.name} usa su [bold cyan]{slot.item.name}[/bold cyan] para remover unos escombros del camino, buscando pasajes secretos."
                        ],
                        "odre": [
                            f"{flavor_adv.name} toma un largo trago de su [bold cyan]{slot.item.name}[/bold cyan], refrescando su reseca garganta.",
                            f"{flavor_adv.name} vierte un poco de agua de su [bold cyan]{slot.item.name}[/bold cyan] para limpiar una vieja inscripción en la pared."
                        ],
                        "yesquero": [
                            f"{flavor_adv.name} hace saltar chispas de su [bold cyan]{slot.item.name}[/bold cyan] tratando de encender una fogata improvisada."
                        ],
                        "saco de dormir": [
                            f"{flavor_adv.name} desenrolla su [bold cyan]{slot.item.name}[/bold cyan], preparando un sitio cómodo para el próximo descanso largo."
                        ],
                        "mochila": [
                            f"{flavor_adv.name} ajusta las correas de su [bold cyan]{slot.item.name}[/bold cyan] para distribuir mejor el peso del botín."
                        ],
                        "alforjas": [
                            f"{flavor_adv.name} revisa el contenido de sus [bold cyan]{slot.item.name}[/bold cyan], organizando sus provisiones con cuidado."
                        ],
                        "saco": [
                            f"{flavor_adv.name} abre su [bold cyan]{slot.item.name}[/bold cyan] preparándolo para guardar las riquezas que encuentren."
                        ],
                        "tiza": [
                            f"{flavor_adv.name} marca una 'X' en la pared con su [bold cyan]{slot.item.name}[/bold cyan] para no perderse en el laberinto."
                        ],
                        "espejo": [
                            f"{flavor_adv.name} usa su [bold cyan]{slot.item.name}[/bold cyan] para espiar por la esquina del pasillo sin exponerse."
                        ],
                        "jabón": [
                            f"{flavor_adv.name} se frota un poco de [bold cyan]{slot.item.name}[/bold cyan] en las manos para quitarse la mugre de la mazmorra."
                        ],
                        "garfio": [
                            f"{flavor_adv.name} lanza hábilmente el [bold cyan]{slot.item.name}[/bold cyan], enganchándolo en un balcón superior."
                        ],
                        "linterna": [
                            f"{flavor_adv.name} enciende su [bold cyan]{slot.item.name}[/bold cyan], proyectando un cono de luz que perfora las tinieblas."
                        ],
                        "aceite": [
                            f"{flavor_adv.name} vierte su [bold cyan]{slot.item.name}[/bold cyan] sobre unas bisagras oxidadas para abrir la puerta sin ruido."
                        ],
                        "palanca": [
                            f"{flavor_adv.name} hace fuerza con su [bold cyan]{slot.item.name}[/bold cyan] para forzar la apertura de un cofre bloqueado."
                        ],
                        "pitones": [
                            f"{flavor_adv.name} clava unos [bold cyan]{slot.item.name}[/bold cyan] en la pared, creando asideros seguros para escalar."
                        ],
                        "martillo": [
                            f"{flavor_adv.name} da golpes precisos con su [bold cyan]{slot.item.name}[/bold cyan] comprobando la solidez del muro."
                        ],
                        "pluma": [
                            f"{flavor_adv.name} saca su [bold cyan]{slot.item.name}[/bold cyan], preparándose para cartografiar el pasadizo."
                        ],
                        "tinta": [
                            f"{flavor_adv.name} destapa un [bold cyan]{slot.item.name}[/bold cyan] con cuidado de no manchar sus ropas."
                        ],
                        "pergamino": [
                            f"{flavor_adv.name} extiende un [bold cyan]{slot.item.name}[/bold cyan] liso y comienza a trazar un esquema del lugar."
                        ],
                        "campana": [
                            f"{flavor_adv.name} coloca una [bold cyan]{slot.item.name}[/bold cyan] atada a un hilo para alertar de cualquier movimiento nocturno."
                        ],
                        "catalejo": [
                            f"{flavor_adv.name} despliega su [bold cyan]{slot.item.name}[/bold cyan] y observa con detalle una estructura a la distancia."
                        ],
                        "herramientas de ladrón": [
                            f"{flavor_adv.name} saca sus [bold cyan]{slot.item.name}[/bold cyan] y se concentra en la compleja cerradura del portón."
                        ],
                        "disfraz": [
                            f"{flavor_adv.name} usa su [bold cyan]{slot.item.name}[/bold cyan] para ponerse una barba falsa y pasar desapercibido."
                        ],
                        "falsificación": [
                            f"{flavor_adv.name} revisa los sellos de cera en su [bold cyan]{slot.item.name}[/bold cyan] preparando un documento engañoso."
                        ],
                        "envenenador": [
                            f"{flavor_adv.name} extrae una aguja de su [bold cyan]{slot.item.name}[/bold cyan], recubriéndola con una toxina mortal."
                        ],
                        "tienda": [
                            f"{flavor_adv.name} arma rápidamente su [bold cyan]{slot.item.name}[/bold cyan], creando un refugio seguro para descansar."
                        ],
                        "poción de trepar": [
                            f"{flavor_adv.name} bebe la [bold cyan]{slot.item.name}[/bold cyan] y sus manos se vuelven pegajosas, permitiéndole subir por la pared."
                        ],
                        "fuego de alquimista": [
                            f"{flavor_adv.name} agita el [bold cyan]{slot.item.name}[/bold cyan], amenazando con desatar un infierno de llamas verdes."
                        ],
                        "agua bendita": [
                            f"{flavor_adv.name} rocía un poco de [bold cyan]{slot.item.name}[/bold cyan] sobre un altar profano, purificando la zona."
                        ],
                        "piedra brillante": [
                            f"{flavor_adv.name} saca su [bold cyan]{slot.item.name}[/bold cyan] que emite una luz perpetua, guiando al grupo."
                        ],
                        "bolso de trucos": [
                            f"{flavor_adv.name} mete la mano en su [bold cyan]{slot.item.name}[/bold cyan] y extrae una pequeña bola peluda que pronto será un animal."
                        ],
                        "bolsa de contención": [
                            f"{flavor_adv.name} guarda un pesado escudo dentro de su [bold cyan]{slot.item.name}[/bold cyan] sin esfuerzo alguno."
                        ],
                        "escoba voladora": [
                            f"{flavor_adv.name} monta su [bold cyan]{slot.item.name}[/bold cyan], flotando a un par de metros del suelo con elegancia."
                        ],
                        "gema de visión": [
                            f"{flavor_adv.name} mira a través de la [bold cyan]{slot.item.name}[/bold cyan], revelando auras invisibles y trucos mágicos."
                        ],
                        "zurrón": [
                            f"{flavor_adv.name} piensa en un objeto y lo saca de inmediato de su [bold cyan]{slot.item.name}[/bold cyan] sin tener que buscar."
                        ],
                        "piedra de enviar": [
                            f"{flavor_adv.name} susurra un mensaje secreto a la [bold cyan]{slot.item.name}[/bold cyan], esperando respuesta telepática."
                        ],
                        "manual de ganancia": [
                            f"{flavor_adv.name} lee unas páginas del [bold cyan]{slot.item.name}[/bold cyan], sintiendo cómo sus músculos se tensan con nuevo vigor."
                        ],
                        "tomo de entendimiento": [
                            f"{flavor_adv.name} hojea el [bold cyan]{slot.item.name}[/bold cyan], sus ojos brillando con una sabiduría celestial."
                        ],
                        "agujero portátil": [
                            f"{flavor_adv.name} extiende el [bold cyan]{slot.item.name}[/bold cyan] en el suelo, creando un pozo oscuro instantáneo."
                        ],
                        "alfombra voladora": [
                            f"{flavor_adv.name} se sienta cómodamente sobre su [bold cyan]{slot.item.name}[/bold cyan], planeando suavemente por el corredor."
                        ],
                        "gema de control": [
                            f"{flavor_adv.name} sostiene en alto la [bold cyan]{slot.item.name}[/bold cyan], que palpita con la furia reprimida de un elemental."
                        ],
                        "grilletes": [
                            f"{flavor_adv.name} hace sonar sus pesados [bold cyan]{slot.item.name}[/bold cyan], listos para apresar a un enemigo resbaladizo."
                        ],
                        "mazo de muchas cosas": [
                            f"{flavor_adv.name} baraja el peligroso [bold cyan]{slot.item.name}[/bold cyan], tentando al destino con una leve sonrisa."
                        ],
                        "esfera de aniquilación": [
                            f"{flavor_adv.name} manipula la [bold cyan]{slot.item.name}[/bold cyan] con sumo cuidado, temiendo que trague hasta la luz."
                        ],
                        "piedra filosofal": [
                            f"{flavor_adv.name} contempla la [bold cyan]{slot.item.name}[/bold cyan], la joya definitiva que puede transmutar la realidad."
                        ],
                        "amuleto de los planos": [
                            f"{flavor_adv.name} ajusta el [bold cyan]{slot.item.name}[/bold cyan], cuyo cristal parpadea con colores de otros mundos."
                        ],
                        "libro de la oscuridad vil": [
                            f"{flavor_adv.name} pasa una página del [bold cyan]{slot.item.name}[/bold cyan], y las sombras de la habitación parecen susurrar."
                        ],
                        "elixir de inmortalidad": [
                            f"{flavor_adv.name} observa el dorado [bold cyan]{slot.item.name}[/bold cyan], la promesa de una vida sin fin burbujeando dentro."
                        ]
                    }

                    # Lógica de búsqueda por palabra clave
                    message_chosen = None
                    for key, lines in flavor_database.items():
                        if key in item_name:
                            message_chosen = random.choice(lines)
                            break

                    # Fallback genérico para otros consumibles
                    if not message_chosen:
                        if item_type == 'HEL':
                            message_chosen = f"¡{flavor_adv.name} bebe su [bold cyan]{slot.item.name}[/bold cyan] y recupera {amt_healed} HP!"
                        elif item_type == 'MAN':
                            message_chosen = f"¡{flavor_adv.name} consume [bold cyan]{slot.item.name}[/bold cyan] y siente cómo su poder interno se restaura!"
                        else:
                            message_chosen = f"Durante la marcha, {flavor_adv.name} decide utilizar su [bold cyan]{slot.item.name}[/bold cyan] de forma ingeniosa."

                    script.append({"second": current_second - 15,
                                  "type": "flavor", "message": message_chosen})
            # --------------------------------------------------------
            # Tirada de Encuentro
            if monsters_db and random.random() < 0.08:
                # --- TABLAS DE ENCUENTRO PONDERADAS ---
                # SML: 60%, MED: 30%, LRG: 8%, EPC: 2%
                category_weights = {'SML': 60, 'MED': 30, 'LRG': 8, 'EPC': 2}

                weights = [category_weights.get(
                    m.category, 10) for m in monsters_db]
                base_monster = random.choices(
                    monsters_db, weights=weights, k=1)[0]
                # ---------------------------------------------------------------

                spawn_count = random.randint(
                    base_monster.min_spawn, base_monster.max_spawn)

                # Genera cada individuo del grupo con su propio registro de estados y stats precisos
                for i in range(spawn_count):
                    # Generación dentro de los rangos definidos
                    m_stats = {
                        'str': safe_randint(base_monster.min_str, base_monster.max_str),
                        'dex': safe_randint(base_monster.min_dex, base_monster.max_dex),
                        'con': safe_randint(base_monster.min_con, base_monster.max_con),
                        'int': safe_randint(base_monster.min_int, base_monster.max_int),
                        'wis': safe_randint(base_monster.min_wis, base_monster.max_wis),
                        'cha': safe_randint(base_monster.min_cha, base_monster.max_cha),
                        'armor': safe_randint(base_monster.min_armor, base_monster.max_armor),
                        'luk': 0
                    }

                    # La salud se calcula desde el rango base + bonificador de constitución
                    base_hp_roll = safe_randint(
                        base_monster.min_hp, base_monster.max_hp)
                    hp = base_hp_roll + (m_stats['con'] * 2)

                    # Nombra al monstruo para distinguirlo (Ej: Goblin Saqueador A, Goblin Saqueador B)
                    name = f"{base_monster.name} {'ABCDEF'[i]}" if spawn_count > 1 else base_monster.name

                    active_monsters_group.append({
                        'name': name, 'hp': hp, 'max_hp': hp, 'stats': m_stats, 'base': base_monster,
                        'status': set()
                    })

                m_color = MONSTER_COLORS.get(base_monster.category, 'red')
                msg = f"¡EMBOSCADA! Un grupo de {spawn_count} [[{m_color}]{base_monster.name}s[/]] corta el paso." if spawn_count > 1 else f"¡PELIGRO! Un [[{m_color}]{base_monster.name}[/]] bloquea el camino."
                script.append({"second": current_second,
                              "type": "flavor", "message": msg})
                state = "COMBAT"
                continue

            # Exploración (Botín) — Cada aventurero vivo busca por su cuenta
            for explore_adv in adventurers:
                if temp_hp[explore_adv.id] <= 0:
                    continue
                adv_luk = explore_adv.base_luk + sum(item.bonus_luk for item in explore_adv.get_equipped_items())
                
                # Roll for coins
                coin_pool = [
                    ('marco', 0.0001), 
                    ('real', 0.0005), 
                    ('talento', 0.001),
                    ('sueldo', 0.005),
                    ('iota', 0.01), 
                    ('silver_penny', 0.01), 
                    ('drabin', 0.05), 
                    ('copper_penny', 0.05),
                    ('iron_penny', 0.10),
                    ('iron_half_penny', 0.20),
                    ('ardite', 0.25)
                ]
                
                found_coin = None
                roll = random.random()
                for coin_name, prob in coin_pool:
                    if roll < (prob + (adv_luk * 0.002)):
                        found_coin = coin_name
                        break
                        
                if found_coin:
                    if found_coin in ['iron_half_penny', 'iron_penny', 'copper_penny']:
                        amt = random.randint(2, 5) + adv_luk
                    elif found_coin in ['ardite', 'silver_penny', 'drabin']:
                        amt = random.randint(1, 3) + (adv_luk // 2)
                    else:
                        amt = 1
                        
                    color = COIN_COLORS.get(found_coin, 'white')
                    display_name = found_coin.replace('_', ' ').title()
                    if found_coin == 'iron_half_penny': display_name = "Medio Penique de Hierro"
                    
                    script.append({"second": current_second - 10, "type": "loot", "coin": found_coin,
                                  "amount": amt, "message": f"{explore_adv.name} encontró {amt} [[{color}]{display_name}[/]]."})

                # Drops aleatorios
                if all_items_db and random.random() < (0.025 + (adv_luk * 0.01)):
                    roll = random.random()
                    rarity = 'COM'
                    if roll < 0.05: rarity = 'RAR'
                    elif roll < 0.25: rarity = 'UNC'
                    
                    pool = [i for i in all_items_db if i.rarity == rarity]
                    if not pool:
                        pool = all_items_db
                    drop_item = random.choice(pool)
                    script.append({"second": current_second - 5, "type": "item_loot", "item_id": drop_item.id, "adventurer_id": explore_adv.id,
                                  "message": f"🎁 {explore_adv.name} encontró algo brillando: [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]"})


            # --- EVALUACIÓN DE HABILIDADES DE SESIÓN (EXPLORACIÓN) ---
            for skill_adv in adventurers:
                if temp_hp[skill_adv.id] <= 0: continue
                available_session_skills = []
                for skill_id, skill_data in SkillRegistry.get_all_skills().items():
                    if skill_data["type"] == "SESSION" and skill_adv.adv_class in skill_data["allowed_classes"] and skill_adv.level >= skill_data["req_level"]:
                        if skill_id not in session_skills_tracker[skill_adv.id]:
                            available_session_skills.append(skill_data)
                
                if available_session_skills:
                    context = {
                        'caster': skill_adv,
                        'allies': adventurers,
                        'enemies': [], # No hay enemigos en exploración
                        'adv_status': adv_status_tracker,
                        'current_second': current_second - 2,
                        'log': script,
                        'eval_mode': True,
                        'session_duration': total_seconds
                    }
                    best_action = None
                    best_score = 50
                    for skill in available_session_skills:
                        try:
                            score = skill["execute"](context)
                            if isinstance(score, bool): score = 0
                            if score > best_score:
                                best_score = score
                                best_action = skill
                        except: pass
                        
                    if best_action:
                        context['eval_mode'] = False
                        try:
                            success = best_action["execute"](context)
                            if success:
                                session_skills_tracker[skill_adv.id].add(best_action["id"])
                        except: pass
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

            # --- PREPARACIÓN DE INICIATIVA ---
            combatants = []
            for m in active_monsters_group:
                init = random.randint(1, 20) + m['stats']['dex']
                combatants.append({'type': 'monster', 'entity': m, 'init': init})
            for adv in adventurers:
                if temp_hp[adv.id] > 0:
                    init = random.randint(1, 20) + adv.get_stat_modifiers()['dex']
                    combatants.append({'type': 'adventurer', 'entity': adv, 'init': init})
            
            combatants.sort(key=lambda x: x['init'], reverse=True)
            
            for combatant in combatants:
                if combatant['type'] == 'monster':
                    m = combatant['entity']
                    if m['hp'] <= 0: continue
                    
                    # --- APLICAR DAÑO EN EL TIEMPO (DoT) AL MONSTRUO ---
                    dot_damage = 0
                    if 'PSN' in m['status']: dot_damage += random.randint(1, 4)
                    if 'BRN' in m['status']: dot_damage += random.randint(1, 6)
                    if 'BLD' in m['status']: dot_damage += random.randint(1, 4)
                    if dot_damage > 0:
                        m['hp'] -= dot_damage
                        script.append({"second": current_second - 10, "type": "flavor",
                                      "message": f"🩸 [bold red]{m['name']}[/bold red] sufre {dot_damage} de daño por estados alterados."})
                        if m['hp'] <= 0: continue

                    if 'STUNNED' in m['status']:
                        m['status'].remove('STUNNED')
                        script.append({"second": current_second - 8, "type": "flavor",
                                      "message": f"💫 [bold red]{m['name']}[/bold red] está aturdido y no puede moverse."})
                        continue

                    valid_targets = [a for a in adventurers if temp_hp[a.id] > 0]
                    if not valid_targets: break
                    target = random.choice(valid_targets)
                    adv_mods = target.get_stat_modifiers()
                    adv_evasion = 8 + max(adv_mods['dex'], adv_mods['armor'])
                    adv_on_attack = 'BLINDED' in adv_status_tracker[target.id] or 'RECKLESS' in adv_status_tracker[target.id]
                    disadv_on_attack = 'BLINDED' in m['status'] or 'DODGING' in adv_status_tracker[target.id]

                    m_raw_roll = roll_d20(advantage=adv_on_attack, disadvantage=disadv_on_attack)["value"]
                    m_roll_total = m_raw_roll + m['stats']['dex']

                    is_hit = False
                    if m_raw_roll == 20: is_hit = True
                    elif m_raw_roll == 1: is_hit = False
                    else: is_hit = (m_roll_total >= adv_evasion)

                    if is_hit:
                        base_m = m['base']
                        m_dmg_dice = sum(random.randint(1, base_m.damage_dice_sides) for _ in range(base_m.damage_dice_count))
                        m_extra_dice = sum(random.randint(1, getattr(base_m, 'bonus_damage_dice_sides', 4)) for _ in range(getattr(base_m, 'bonus_damage_dice_count', 0))) if getattr(base_m, 'bonus_damage_dice_count', 0) > 0 else 0
                        m_dmg = m_dmg_dice + m_extra_dice + base_m.bonus_damage + m['stats']['str']

                        if target.adv_class == 'ROG' and target.level >= 5 and 'REACTION_USED' not in adv_status_tracker[target.id]:
                            m_dmg = m_dmg // 2
                            adv_status_tracker[target.id].add('REACTION_USED')
                            script.append({"second": current_second - 8, "type": "flavor", "message": f"🛡️ {target.name} usa [bold yellow]Esquiva Asombrosa[/bold yellow] y mitiga el impacto."})

                        if 'RAGING' in adv_status_tracker[target.id]:
                            m_dmg = m_dmg // 2

                        eff_m = getattr(base_m, 'on_hit_effect', 'NON')
                        if eff_m != 'NON' and random.randint(1, 100) <= getattr(base_m, 'effect_chance', 0):
                            if eff_m == 'LFS':
                                heal = sum(random.randint(1, getattr(base_m, 'effect_dice_sides', 4)) for _ in range(getattr(base_m, 'effect_dice_count', 1)))
                                m['hp'] = min(m['max_hp'], m['hp'] + heal)
                                script.append({"second": current_second - 8, "type": "flavor", "message": f"¡[bold red]{m['name']}[/bold red] drena {heal} HP de {target.name}!"})
                            else:
                                adv_status_tracker[target.id].add(eff_m)
                                script.append({"second": current_second - 8, "type": "flavor", "message": f"¡[bold red]{m['name']}[/bold red] inyecta el estado {eff_m} a {target.name}!"})

                        eff_adv = adv_mods.get('on_hit_effect', 'NON')
                        if eff_adv == 'THN' and random.randint(1, 100) <= adv_mods.get('effect_chance', 0):
                            thorns_dmg = random.randint(1, 4)
                            m['hp'] -= thorns_dmg
                            script.append({"second": current_second - 7, "type": "flavor", "message": f"La armadura de {target.name} devuelve {thorns_dmg} daño a [bold red]{m['name']}[/bold red]."})

                        final_dmg = max(1, m_dmg - adv_mods['con'])
                        temp_hp[target.id] -= final_dmg

                        crit_msg = "[bold magenta]¡CRÍTICO![/bold magenta] " if m_raw_roll == 20 else ""
                        script.append({"second": current_second - 8, "type": "damage", "adventurer_id": target.id, "amount": final_dmg,
                                      "message": f"{crit_msg}[bold red]{m['name']}[/bold red] golpea a {target.name} ({final_dmg} daño)."})
                        if temp_hp[target.id] <= 0:
                            script.append({"second": current_second - 7, "type": "flavor", "message": f"⚠️ [bold yellow]{target.name}[/bold yellow] ha caído inconsciente en combate."})
                    else:
                        fail_msg = "falla estrepitosamente" if m_raw_roll == 1 else "falla su ataque"
                        script.append({"second": current_second - 8, "type": "flavor", "message": f"[bold red]{m['name']}[/bold red] {fail_msg} contra {target.name}."})
                
                else:
                    adv = combatant['entity']
                    if temp_hp[adv.id] <= 0: continue
                    if not active_monsters_group: break
                    
                    adv_mods = adv.get_stat_modifiers()

                    if temp_hp[adv.id] < (adv.max_hp * 0.3):
                        heal_slots = list(InventorySlot.objects.filter(adventurer=adv, item__consumable_type='HEL', quantity__gt=0))
                        if heal_slots:
                            slot = heal_slots[0]
                            slot.quantity -= 1
                            if slot.quantity <= 0: slot.delete()
                            else: slot.save()

                            heal_amount = slot.item.consumable_amount if slot.item.consumable_amount > 0 else random.randint(10, 20)
                            temp_hp[adv.id] = min(adv.max_hp, temp_hp[adv.id] + heal_amount)
                            script.append({"second": current_second - 5, "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                           "message": f"¡Salud Crítica! {adv.name} bebe desesperadamente una [bold cyan]{slot.item.name}[/bold cyan] (+{heal_amount} HP)."})
                            continue

                    dot_damage = 0
                    if 'PSN' in adv_status_tracker[adv.id]: dot_damage += random.randint(1, 4)
                    if 'BRN' in adv_status_tracker[adv.id]: dot_damage += random.randint(1, 6)
                    if 'BLD' in adv_status_tracker[adv.id]: dot_damage += random.randint(1, 4)
                    if dot_damage > 0:
                        temp_hp[adv.id] -= dot_damage
                        script.append({"second": current_second - 6, "type": "damage", "adventurer_id": adv.id,
                                      "amount": dot_damage, "message": f"{adv.name} sufre {dot_damage} de daño continuo."})
                        if temp_hp[adv.id] <= 0:
                            script.append({"second": current_second - 5, "type": "flavor", "message": f"⚠️ [bold yellow]{adv.name}[/bold yellow] ha caído inconsciente por sus heridas."})
                            continue

                    available_skills = []
                    for skill_id, skill_data in SkillRegistry.get_all_skills().items():
                        if adv.adv_class in skill_data["allowed_classes"] and adv.level >= skill_data["req_level"]:
                            if skill_data["type"] == "COMBAT" and skill_id not in combat_skills_tracker[adv.id]:
                                available_skills.append(skill_data)

                    best_action = "BASIC_ATTACK"
                    best_score = 50

                    context = {
                        'caster': adv,
                        'allies': adventurers,
                        'enemies': active_monsters_group,
                        'adv_status': adv_status_tracker,
                        'current_second': current_second - 4,
                        'log': script,
                        'eval_mode': True
                    }

                    for skill in available_skills:
                        try:
                            score = skill["execute"](context)
                            if score > best_score:
                                best_score = score
                                best_action = skill
                        except Exception as e:
                            import logging
                            logging.warning(f"Skill eval error: {e}")

                    context['eval_mode'] = False

                    if best_action == "BASIC_ATTACK":
                        adv_status_tracker[adv.id].discard('REACTION_USED')
                        attacks = 2 if adv.level >= 5 and adv.adv_class in ['FTR', 'BBN', 'RGR', 'PAL', 'MNK'] else 1

                        for _ in range(attacks):
                            if not active_monsters_group: break
                            target_m = random.choice(active_monsters_group)
                            attack_stat = max(adv_mods['str'], adv_mods['dex'])

                            adv_on_attack = 'BLINDED' in target_m['status'] or 'RECKLESS' in adv_status_tracker[adv.id]
                            disadv_on_attack = 'BLINDED' in adv_status_tracker[adv.id]

                            m_evasion = 8 + max(target_m['stats']['dex'], target_m['stats'].get('armor', 0))
                            a_raw_roll = roll_d20(advantage=adv_on_attack, disadvantage=disadv_on_attack)["value"]
                            a_roll_total = a_raw_roll + attack_stat

                            if 'INSPIRED' in adv_status_tracker[adv.id]:
                                bard_dice = random.randint(1, 6)
                                a_roll_total += bard_dice
                                adv_status_tracker[adv.id].remove('INSPIRED')
                                script.append({"second": current_second - 5, "type": "flavor", "message": f"🎵 ¡La música del Bardo guía el golpe! (+{bard_dice})"})

                            is_hit = False
                            if a_raw_roll == 20: is_hit = True
                            elif a_raw_roll == 1: is_hit = False
                            else: is_hit = (a_roll_total >= m_evasion)

                            if is_hit:
                                sides = adv_mods.get('weapon_dice_sides', 4) or 4
                                count = adv_mods.get('weapon_dice_count', 1) or 1
                                a_dmg = sum(random.randint(1, sides) for _ in range(count)) + adv_mods['damage'] + adv_mods['str']

                                extra_count = adv_mods.get('bonus_dmg_dice_count', 0)
                                if extra_count > 0:
                                    extra_sides = adv_mods.get('bonus_dmg_dice_sides', 4) or 4
                                    a_dmg += sum(random.randint(1, extra_sides) for _ in range(extra_count))

                                if adv.adv_class == 'ROG' and adv_on_attack:
                                    sneak_dice = (adv.level + 1) // 2
                                    sneak_dmg = sum(random.randint(1, 6) for _ in range(sneak_dice))
                                    a_dmg += sneak_dmg
                                    script.append({"second": current_second - 5, "type": "flavor", "message": f"🗡️ ¡Ataque Furtivo de {adv.name}! (+{sneak_dmg})"})

                                if 'RAGING' in adv_status_tracker[adv.id]: a_dmg += 2
                                if 'INFUSED_WEAPON' in adv_status_tracker[adv.id]: a_dmg += 1

                                eff = adv_mods.get('on_hit_effect', 'NON')
                                if eff != 'NON' and eff != 'THN':
                                    if random.randint(1, 100) <= adv_mods.get('effect_chance', 0):
                                        if eff == 'LFS':
                                            heal = sum(random.randint(1, adv_mods['effect_dice_sides']) for _ in range(adv_mods['effect_dice_count']))
                                            temp_hp[adv.id] = min(adv.max_hp, temp_hp[adv.id] + heal)
                                            script.append({"second": current_second - 4, "type": "heal", "adventurer_id": adv.id, "amount": heal, "message": f"🦇 {adv.name} drena {heal} HP."})
                                        else:
                                            target_m['status'].add(eff)
                                            eff_names = {'PSN': 'Veneno', 'BLD': 'Sangrado', 'BRN': 'Quemaduras', 'STN': 'Aturdimiento', 'BLN': 'Ceguera'}
                                            script.append({"second": current_second - 4, "type": "flavor", "message": f"¡{adv.name} inflige {eff_names.get(eff, eff)}!"})

                                final_dmg = max(1, a_dmg - target_m['stats']['con'])
                                target_m['hp'] -= final_dmg

                                crit_msg = "[bold magenta]¡CRÍTICO![/bold magenta] " if a_raw_roll == 20 else ""
                                script.append({"second": current_second - 4, "type": "flavor",
                                              "message": f"{crit_msg}{adv.name} asesta un golpe de {final_dmg} daño a [bold red]{target_m['name']}[/bold red]."})
                            else:
                                fail_msg = "falla catastróficamente" if a_raw_roll == 1 else "falla su ataque"
                                script.append({"second": current_second - 4, "type": "flavor", "message": f"{adv.name} {fail_msg} contra [bold red]{target_m['name']}[/bold red]."})
                    else:
                        success = best_action["execute"](context)
                        if success:
                            combat_skills_tracker[adv.id].add(best_action["id"])
                # --- Comprobación Universal de Muertes ---
                for m in list(active_monsters_group):
                    if m['hp'] <= 0:
                        # Rescata la XP que otorga el monstruo y la sumamos al pozo
                        xp_ganada = getattr(m['base'], 'xp_reward', 0)

                        m_color = MONSTER_COLORS.get(m['base'].category, 'red')
                        script.append({"second": current_second - 2, "type": "flavor",
                                      "message": f"💀 [[{m_color}]{m['name']}[/]] cae derrotado (+{xp_ganada} XP).", "xp_ganada": xp_ganada})
                        active_monsters_group.remove(m)

                        # Generar Monedas
                        for coin, max_amt, prob in coin_drops.get(m['base'].category, []):
                            if random.random() < prob:
                                amt = random.randint(1, max_amt)
                                c_color = COIN_COLORS.get(coin, 'white')
                                display_name = coin.replace('_', ' ').title()
                                if coin == 'iron_half_penny': display_name = "Medio Penique de Hierro"
                                script.append({"second": current_second - 1, "type": "loot", "coin": coin, "amount": amt,
                                              "message": f"El monstruo soltó {amt} [[{c_color}]{display_name}[/]]."})

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


            # --- RESOLUCIÓN DEL COMBATE ---
            all_dead = all(temp_hp[a.id] <= 0 for a in adventurers)
            if not active_monsters_group or all_dead:
                # Reseteo del enfriamiento de habilidades de combate
                for adv_id in combat_skills_tracker:
                    combat_skills_tracker[adv_id].clear()
                    # Limpia los estados negativos al terminar el combate
                    adv_status_tracker[adv_id].clear()

                if all_dead:
                    script.append({"second": current_second, "type": "flavor", "message": "💀 ¡DERROTA! Todo el grupo ha caído."})
                    active_monsters_group.clear()
                    state = "CAMPFIRE"
                else:
                    script.append({"second": current_second, "type": "flavor", "message": "¡VICTORIA! La zona está despejada."})
                    if any(temp_hp[a.id] <= 0 for a in adventurers):
                        script.append({"second": current_second + 1, "type": "flavor", "message": "🏕️ El grupo decide montar un campamento para atender a los heridos."})
                        state = "CAMPFIRE"
                    else:
                        state = "EXPLORING"

        elif state == "CAMPFIRE":
            current_second += 30
            if current_second >= total_seconds:
                break
                
            all_healed = True
            for adv in adventurers:
                if temp_hp[adv.id] < adv.max_hp:
                    all_healed = False
                    heal = random.randint(adv.level, (adv.level * 3) + adv.base_con)
                    temp_hp[adv.id] = min(adv.max_hp, temp_hp[adv.id] + heal)
                    script.append({"second": current_second, "type": "heal", "adventurer_id": adv.id, "amount": heal, "message": f"🔥 {adv.name} descansa y recupera [bold green]{heal} HP[/]."})
            
            if all_healed:
                script.append({"second": current_second, "type": "flavor", "message": "🔥 El grupo se ha recuperado por completo. ¡La aventura continúa!"})
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
    session_monster_xp = 0
    for event in script:
        if event["second"] <= survived_seconds:
            if event.get("xp_ganada"):
                session_monster_xp += event["xp_ganada"]
            
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
                event_log.append(
                    f"{adv.name} sobrevivió a las heridas con {adv.current_hp}/{adv.max_hp} HP.")
            adv.save()

    distribute_tithe(guild, adventurers, loot, event_log)
    market_phase(adventurers, event_log)

    # --- EXPERIENCIA DE AVENTUREROS ---
    survived_minutes = survived_seconds // 60
    base_xp = survived_minutes * XP_PER_MINUTE
    cat_lower = session.category.lower()

    # --- Mejoras del Gremio ---
    from .models import GuildUnlockedUpgrade
    has_cartography = GuildUnlockedUpgrade.objects.filter(
        guild=guild, upgrade__key='salon_cartografia').exists()

    for adv in adventurers:
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
    from .models import Item, InventorySlot, ItemRarity
    
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
