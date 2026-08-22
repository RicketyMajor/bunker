"""Custom charts: how much of the canvas the user filled, and what it pays.

Moved out of `legacy.py` unchanged (Phase 3, Task 8). Touches no other seam.
"""
import itertools
import random

from posada.models import GuildProfile

def get_chart_completion_status(chart):
    """Analiza el progreso de un gráfico: qué puntos enteros del eje X están cubiertos y cuáles faltan."""
    x_start = int(chart.x_min)
    x_end = int(chart.goal_x_value)
    expected = set(range(x_start, x_end + 1))

    # Sin order_by: esto alimenta un set, que ya descarta el orden.
    covered = {int(p.x_value) for p in chart.data_points.all()} & expected

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
    for anterior, actual in itertools.pairwise(points):
        dx = actual.x_value - anterior.x_value
        # La altura se mide desde el "suelo" del gráfico (y_min)
        h1 = max(0.0, anterior.y_value - chart.y_min)
        h2 = max(0.0, actual.y_value - chart.y_min)
        area += dx * (h1 + h2) / 2.0

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

    leveled_up = guild.add_prestige(prestige_reward, 'meta_completada',
                                    detail=chart.title, ref_id=chart.id)
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
        g_slot, creado = InventorySlot.objects.get_or_create(guild=guild, item=drop, adventurer=None, defaults={'quantity': 1})
        if not creado:
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
