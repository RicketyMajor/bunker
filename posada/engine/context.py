"""Contexto de sesión para la State Machine del motor de Deep Work.

SessionContext centraliza todo el estado mutable que antes eran variables
locales desperdigadas en el bucle principal de generate_session_script.
"""
from dataclasses import dataclass, field


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
