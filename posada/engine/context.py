"""Contexto de sesión para la State Machine del motor de Deep Work.

SessionContext centraliza todo el estado mutable que antes eran variables
locales desperdigadas en el bucle principal de generate_session_script.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field


@contextmanager
def hp_vivos(ctx, adventurers):
    """Lend `adv.current_hp` the live simulated value for the length of a skill dispatch.

    The engine simulates on `ctx.temp_hp`; `adv.current_hp` is the session-start snapshot plus
    whatever skills have written into it, and it is the field `sesion.py` persists. The two
    never meet: no skill can reach `ctx.temp_hp` (every writer of it lives in the engine's own
    state modules), and the dispatch context offers no other HP, so the 68 skills that condition
    on `caster.current_hp` read a value the simulation is not using. 20 of them condition on it
    again in the execution path, which is why this window has to cover execution and not only
    scoring.

    On the way in, `current_hp` takes the live value. On the way out, the live dict takes
    whatever the skill left, and `current_hp` is restored to what it was **plus that same
    delta** -- which is exactly what a skill doing `current_hp = min(max_hp, current_hp + heal)`
    produced before this existed. Persistence semantics are therefore unchanged, which is the
    point: `sesion.py:91` applies the replayed net only `if dmg > 0`, so a net heal is discarded
    and those direct writes are the ONLY thing that persists healing. Restoring the bare
    snapshot here would delete it.

    `finally`, because every path must leave through it -- a skill that raises, and combat's
    basic-attack branch. A leaked mirror hands `sesion.py` a live value where it expects the
    snapshot, and the session's damage would then be netted against the wrong base.
    """
    foto = {a.id: a.current_hp for a in adventurers}
    for a in adventurers:
        a.current_hp = ctx.temp_hp[a.id]
    vivo = {a.id: a.current_hp for a in adventurers}
    try:
        yield
    finally:
        for a in adventurers:
            delta = a.current_hp - vivo[a.id]
            ctx.temp_hp[a.id] = a.current_hp
            a.current_hp = max(0, min(a.max_hp, foto[a.id] + delta))


class ScriptList(list):
    """Lista de eventos del guion que auto-inyecta el estado actual."""

    def __init__(self, state_getter):
        super().__init__()
        self._state_getter = state_getter

    def append(self, item):
        try:
            item["state"] = self._state_getter()
        except Exception:
            item["state"] = "EXPLORING"
        super().append(item)


@dataclass
class SessionContext:
    """Estado completo de una sesión de Deep Work.

    Es el único argumento que reciben las funciones tick_* de cada estado,
    eliminando la necesidad de pasar docenas de variables sueltas.
    """
    # --- Core ---
    script: ScriptList = field(default_factory=list)
    adventurers: list = field(default_factory=list)
    monsters_db: list = field(default_factory=list)
    all_items_db: list = field(default_factory=list)
    total_seconds: int = 0
    current_second: int = 0
    state: str = "EXPLORING"

    # --- Combate ---
    active_monsters_group: list = field(default_factory=list)

    # --- Trackers de Habilidades ---
    session_skills_tracker: dict = field(default_factory=dict)
    combat_skills_tracker: dict = field(default_factory=dict)
    adv_status_tracker: dict = field(default_factory=dict)
    temp_hp: dict = field(default_factory=dict)

    # --- Tablas de Botín (cargadas en inicialización) ---
    coin_drops: dict = field(default_factory=dict)
    item_drops: dict = field(default_factory=dict)
