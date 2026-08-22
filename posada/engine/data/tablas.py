"""Static tables the engine reads and never writes.

Moved out of `legacy.py` unchanged (Phase 3, Task 3). This module imports nothing — not Django,
not `posada.models` — which is what lets `states/` import it at module level instead of the
function-local re-imports that used to dodge the `legacy` <-> `states` cycle.
"""

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

XP_PER_MINUTE = 10

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


# The equipment slot each item_type occupies. SINGLE definition: this was copy-pasted five times
# (four in the engine, one in posada/views.py) and the copies had already drifted apart.
#
# ⚠ The engine's four copies mapped 'LEG', which is NOT in `Item.item_type`'s choices, and did NOT
# map 'LGS', which IS — with 21 items behind it. `_auto_equip` returns early on an unmapped type
# WITHOUT storing the item, so every leg piece the engine pulled was destroyed in silence: not
# equipped, not stored, not even logged. Measured 2026-08-22, then fixed here.
#
# 'RNG' is deliberately absent: a ring has two slots and is resolved before this map is consulted.
SLOT_POR_TIPO = {
    'W1H': 'equip_main_hand', 'W2H': 'equip_main_hand', 'OFF': 'equip_off_hand',
    'HED': 'equip_head', 'TRS': 'equip_torso', 'LGS': 'equip_legs',
    'HND': 'equip_hands', 'FET': 'equip_feet', 'NCK': 'equip_necklace',
    'BRC': 'equip_bracelet', 'EAR': 'equip_earring',
}


# Value of each coin in base units, DESCENDING. The order is load-bearing: every greedy
# decomposition in `economia.py` walks these top-down, and a coin placed after one worth less
# than it can never be assembled.
#
# ⚠ Measured 2026-08-22: the inline list in `calculate_sell_value` had ('sueldo', 1100) BEFORE
# ('iota', 3520). Selling 4 iotas at 100% returned 12 sueldos + 2 drabines + 5 ardites =
# 14,064 base units instead of 14,080 — the wrong denominations AND 16 units destroyed, because
# the leftover fell below the smallest coin. `tests/test_engine_split.py` now refuses any table
# here that is not sorted descending.
MANCOMUNIDAD = {
    'marco': 352000, 'real': 88000, 'talento': 35200, 'iota': 3520,
    'sueldo': 1100, 'drabin': 352, 'ardite': 32,
}
IMPERIAL = {
    'silver_penny': 100, 'copper_penny': 10, 'iron_penny': 2, 'iron_half_penny': 1,
}
