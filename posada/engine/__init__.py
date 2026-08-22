"""posada.engine — Motor de la Posada RPG.

Split out of the monolithic `legacy.py` in Phase 3 (2026-08-22): 1,395 lines and 27 functions
became seven modules, none over 210 lines. The star import that used to live here is gone —
it re-exported `legacy.py`'s own imports too, so `posada.engine.Sum`, `.random`, `.timezone`
and all fifteen Django models were part of this package's public surface by accident.

The list below IS the public surface, and `tests/test_engine_split.py` fails if it drifts.
"""
from posada.engine.data.tablas import (  # noqa: F401
    COIN_COLORS, MONSTER_COLORS, XP_PER_MINUTE, CATEGORY_SYNERGY, FLAVOR_MONSTER,
    SKILL_STAT_MAP, CLASS_SKILL_PROFICIENCIES, FLAVOR_ADV, CLASS_PROFICIENCIES,
)
from posada.engine.economia import (  # noqa: F401
    universal_consolidate, calculate_sell_value, add_wealth_from_dict, get_imperial_value,
    get_commonwealth_value, can_afford, pay_with_change, consolidate_wealth,
)
from posada.engine.inventario import (  # noqa: F401
    get_item_score, add_item_to_inventory, is_class_allowed,
)
from posada.engine.mercado import market_phase  # noqa: F401
from posada.engine.progresion import (  # noqa: F401
    safe_randint, get_derived_skills, roll_d20, distribute_tithe, distribute_random_stats,
    get_xp_requirement, check_level_up,
)
from posada.engine.habitos import evaluate_daily_penalties  # noqa: F401
from posada.engine.sesion import process_session_completion  # noqa: F401
from posada.engine.graficos import get_chart_completion_status, calculate_chart_reward  # noqa: F401
from posada.engine.runner import generate_session_script  # noqa: F401
