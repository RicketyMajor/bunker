"""Engine split guard — proves a MOVE moved nothing else. Runs inside the container:

    docker compose exec -T web python -m tests.test_engine_split

Three instruments, because the script-reproducibility net that `specs/posada-robusta.md` names
covers 3 of the 27 functions in `legacy.py` (measured 2026-08-22 by profile trace over
`generate_session_script`: only `roll_d20`, `safe_randint` and `get_derived_skills` execute —
everything `process_session_completion` owns is invisible to it):

  1. FUENTES    — md5 of each symbol's SOURCE TEXT, wherever it now lives. A move that drops,
                  reindents or edits a line fails here, naming the symbol.
  2. SUPERFICIE — the names importable from `posada.engine`. A move that forgets to re-export
                  fails here, naming the name. This is what catches a symbol that vanished from
                  BOTH the code and the baseline, which instrument 1 alone cannot see.
  3. GUION      — the spec's own net, kept because it is free and it is the only one that proves
                  the RUNNER still runs. Asserts BOTH directions: same seed -> same script, and
                  different seed -> different script, so the comparator cannot be vacuous.

Phase 3 of `context/specs/posada-robusta.md`. Instrument 1 is what makes the move tasks safe;
2 and 3 alone are green for a botched move.
"""
import hashlib
import inspect
import json
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402

fallos = []
comprobaciones = 0

# The three names `from posada.engine.legacy import *` does not re-export, because they start
# with an underscore. Reached explicitly by module, so this tuple moves as they do.
PRIVADAS = (
    ('posada.engine.inventario', '_auto_equip'),
    ('posada.engine.mercado', '_seed_items_if_empty'),
    ('posada.engine.mercado', '_seed_guild_upgrades'),
)


def _md5(texto):
    return hashlib.md5(texto.encode()).hexdigest()


def _fuente(obj):
    """Source text of a function, dedented.

    `inspect.getsource` includes decorators, and that is deliberate: `@transaction.atomic` must
    move WITH its function, and a move that drops it has to fail here.
    """
    return inspect.cleandoc(inspect.getsource(obj))


def superficie_actual():
    import posada.engine as E
    return sorted(n for n in dir(E) if not n.startswith('_'))


def fuentes_actuales():
    """md5 of every public symbol reachable from `posada.engine`, plus the three private ones.

    Data tables are hashed by CONTENT (json, sorted keys), not by source text: moving a dict to
    another module may reflow it, and what must not change is what it holds.
    """
    import importlib
    import posada.engine as E
    fuentes = {}
    for nombre in superficie_actual():
        obj = getattr(E, nombre)
        if inspect.isfunction(obj):
            fuentes[nombre] = _md5(_fuente(obj))
        elif isinstance(obj, (dict, list, tuple, set, int, float, str)):
            fuentes[nombre] = _md5(json.dumps(obj, sort_keys=True, default=str,
                                              ensure_ascii=False))
    for modulo, nombre in PRIVADAS:
        obj = getattr(importlib.import_module(modulo), nombre)
        fuentes[nombre] = _md5(_fuente(obj))
    return fuentes
# Frozen 2026-08-22 against HEAD ed00551 + the .bak deletion, BEFORE any move.
# 45 names. Task 9 removed `import *`: the 21 accidental exports it carried — every
# Django model legacy.py imported, plus Sum/random/timedelta/timezone/transaction — are GONE, and
# nothing outside imported them (verified by grep before this baseline was cut). What remains is
# the surface the package actually means to have, plus one name per submodule. It includes the Django models and stdlib names that
# `from posada.engine.legacy import *` re-exports by accident — that pollution is real,
# it is what Task 9 removes, and freezing it here is what makes its removal visible.
SUPERFICIE = [
    "CATEGORY_SYNERGY",
    "CLASS_PROFICIENCIES",
    "CLASS_SKILL_PROFICIENCIES",
    "COIN_COLORS",
    "FLAVOR_ADV",
    "FLAVOR_MONSTER",
    "MONSTER_COLORS",
    "SKILL_STAT_MAP",
    "XP_PER_MINUTE",
    "add_item_to_inventory",
    "add_wealth_from_dict",
    "calculate_chart_reward",
    "calculate_sell_value",
    "can_afford",
    "check_level_up",
    "consolidate_wealth",
    "context",
    "data",
    "distribute_random_stats",
    "distribute_tithe",
    "economia",
    "estados",
    "evaluate_daily_penalties",
    "generate_session_script",
    "get_chart_completion_status",
    "get_commonwealth_value",
    "get_derived_skills",
    "get_imperial_value",
    "get_item_score",
    "get_xp_requirement",
    "graficos",
    "habitos",
    "inventario",
    "is_class_allowed",
    "market_phase",
    "mercado",
    "pay_with_change",
    "process_session_completion",
    "progresion",
    "roll_d20",
    "runner",
    "safe_randint",
    "sesion",
    "states",
    "universal_consolidate"
]

# 36 bodies: 24 public functions + 3 private + 9 data tables. Counted, not inherited.
FUENTES = {
    "CATEGORY_SYNERGY": "b182bd1e7af9c7ef93d578296a26f3ab",
    "CLASS_PROFICIENCIES": "47fadaf703f2c4b7c049c19a396d3f79",
    "CLASS_SKILL_PROFICIENCIES": "fdb99131abf8a52650f138dd24d22838",
    "COIN_COLORS": "8dbfc5167236337ff84f32bf97b6354f",
    "FLAVOR_ADV": "634378ed2784ad4e433fce30c4adc9bd",
    "FLAVOR_MONSTER": "fcada5ab867dd153b9401ab14ea8d18e",
    "MONSTER_COLORS": "d99b1aff849af15fdfb54e6a45ed05ec",
    "SKILL_STAT_MAP": "9274fc1a1823e7176dc16add95390779",
    "XP_PER_MINUTE": "d3d9446802a44259755d38e6d163e820",
    "_auto_equip": "1a68d0fac768d427e0642df344a29b61",
    "_seed_guild_upgrades": "5a891598990b0a0eb772e8757f63c1c6",
    "_seed_items_if_empty": "266823a5f83a7f59f5e1ac46d6829af4",
    "add_item_to_inventory": "5aa419a75f25cb04682bf66db1b02041",
    "add_wealth_from_dict": "c4182212816e154b214d143834008ebb",
    "calculate_chart_reward": "7f77c705b155a257398f285cd3f422d1",
    "calculate_sell_value": "41e52a7a2b88dee992335c069d737162",
    "can_afford": "30978988e3113c23e39595a7815823cd",
    "check_level_up": "c6724d2434254e3c9a4ee0264df91ecb",
    "consolidate_wealth": "de23177e3037c7651c928e3b0eee033a",
    "distribute_random_stats": "6df7795485fffc0fa6011d78de805066",
    "distribute_tithe": "f2f69dd0efc8117e5e5afff4241c00e8",
    "evaluate_daily_penalties": "62600d00f2e7cdfc23e73a6dbe9f531a",
    "generate_session_script": "12a6df418e11606b04115a73819afb76",
    "get_chart_completion_status": "e00dd844f2a70365699a41f5f3595cab",
    "get_commonwealth_value": "0b88fbaa1342341f44695d0550efd49f",
    "get_derived_skills": "5a45e116b7ab8ae8c57b236567de8a33",
    "get_imperial_value": "e46680af659c65ab4f51498f4d74b08d",
    "get_item_score": "f6fa7ffbf0b426ae45d324abdd6e9e4a",
    "get_xp_requirement": "0fd16a08fbc8236243145267b71fb80a",
    "is_class_allowed": "8935dd8c86ca57ac0bac2780bc6543c8",
    "market_phase": "7f7e8b029d610171a33c8a3a01733ed0",
    "pay_with_change": "8b5d5ed5f0e2a4855925fcf539497a1a",
    "process_session_completion": "90a7c9dd2f61e713a8e1a0da476983c9",
    "roll_d20": "db44d39f2f24f0baeaa3e57d322394f9",
    "safe_randint": "3feb445f6f5cf076341d29c8785dcb35",
    "universal_consolidate": "df917abea87ef51b130f7e57477a1765"
}


def probar_superficie():
    global comprobaciones
    actual = superficie_actual()
    faltan = sorted(set(SUPERFICIE) - set(actual))
    sobran = sorted(set(actual) - set(SUPERFICIE))
    comprobaciones += 1
    if faltan:
        fallos.append(f"posada.engine dejo de exportar: {faltan}")
    if sobran:
        fallos.append(f"posada.engine exporta simbolos nuevos sin actualizar SUPERFICIE: {sobran}")
    if not faltan and not sobran:
        print(f"  OK superficie publica intacta ({len(actual)} nombres)")


def probar_fuentes():
    global comprobaciones
    actual = fuentes_actuales()
    perdidas = sorted(set(FUENTES) - set(actual))
    cambiadas = sorted(n for n in FUENTES if n in actual and actual[n] != FUENTES[n])
    nuevas = sorted(set(actual) - set(FUENTES))
    comprobaciones += 1
    if perdidas:
        fallos.append(f"simbolos que desaparecieron: {perdidas}")
    if cambiadas:
        fallos.append(
            f"el CUERPO de estos simbolos cambio, y una tarea de movimiento solo podia "
            f"moverlos: {cambiadas}")
    if nuevas:
        fallos.append(f"simbolos nuevos sin actualizar FUENTES: {nuevas}")
    if not (perdidas or cambiadas or nuevas):
        print(f"  OK {len(FUENTES)} cuerpos byte-identicos")


def probar_guion():
    """The spec's own net. Both directions, so the comparator cannot be vacuous."""
    global comprobaciones
    from posada.models import Adventurer
    from posada.engine.runner import generate_session_script

    def guion(semilla):
        return json.dumps(generate_session_script(semilla, 25, list(Adventurer.objects.all())),
                          default=str, sort_keys=True, ensure_ascii=False)

    with transaction.atomic():
        a, b, c = guion(4242), guion(4242), guion(4243)
        transaction.set_rollback(True)

    comprobaciones += 1
    if a != b:
        fallos.append("el guion dejo de ser reproducible con la misma semilla")
    elif a == c:
        fallos.append(
            "el comparador del guion es VACUO: dos semillas distintas dan el mismo guion")
    else:
        print(f"  OK guion reproducible y sensible a la semilla ({len(json.loads(a))} eventos)")


if __name__ == '__main__':
    probar_superficie()
    probar_fuentes()
    probar_guion()
    if fallos:
        print(f"\n{len(fallos)} FALLOS de {comprobaciones} instrumentos:\n")
        for f in fallos:
            print(f"  {f}\n")
        raise SystemExit(1)
    print(f"{comprobaciones} instrumentos OK")
