"""Tablas de botín para exploración y combate."""

# --- Tablas de Botín de Combate por Categoría de Monstruo ---
# (moneda, cant_max, probabilidad)
COIN_DROPS = {
    'SML': [('iron_penny', 5, 0.8), ('ardite', 3, 0.5), ('copper_penny', 1, 0.1)],
    'MED': [('copper_penny', 5, 0.8), ('drabin', 3, 0.5), ('silver_penny', 1, 0.2)],
    'LRG': [('silver_penny', 6, 0.9), ('sueldo', 2, 0.6), ('talento', 1, 0.1)],
    'EPC': [('sueldo', 5, 1.0), ('talento', 3, 0.8), ('real', 1, 0.3), ('marco', 1, 0.05)]
}

# (rareza, prob_base) -> luk_bonus sube la prob
ITEM_DROPS = {
    'SML': [('COM', 0.05), ('UNC', 0.01)],
    'MED': [('UNC', 0.10), ('RAR', 0.02)],
    'LRG': [('RAR', 0.15), ('EPC', 0.05)],
    'EPC': [('EPC', 0.25), ('LEG', 0.10)]
}

# --- Pool de Monedas para Exploración ---
# (nombre_moneda, probabilidad_base) — exclusión mutua, orden descendente de valor
COIN_POOL = [
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
