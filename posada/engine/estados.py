"""The Posada engine's single status vocabulary.

Every status name the engine can write or read is declared HERE and nowhere else. Before
this module there were two vocabularies: `OnHitEffect` in `models.py` used three-letter
codes (`STN`, `BLN`) and the engine invented long names (`STUNNED`, `BLINDED`). Nothing
crossed them, so a write nobody reads was undetectable and six mechanics were silently
dead for months under a green gate.

There are TWO containers and the same code can be alive in one and dead in the other:
`ctx.adv_status_tracker[adv.id]` (a set per adventurer) and `m['status']` (a set per
monster). `contenedor` records which ones a code is legal in, and the contract in
`tests/test_posada_estados.py` cross-references writers against readers per container.

`preexistente` is what lets the guard tell REPAIR from INVENTION. Everything declared in
this first pass predates the vocabulary; anything added later is `preexistente=False`, so
a failure involving it is a new mechanic misbehaving, not an old one still broken.
"""
from dataclasses import dataclass
from typing import FrozenSet

AVENTURERO = "aventurero"
MONSTRUO = "monstruo"


@dataclass(frozen=True)
class Estado:
    codigo: str
    nombre: str
    contenedor: FrozenSet[str]
    preexistente: bool = True


def _e(codigo, nombre, *contenedor, preexistente=True):
    return Estado(codigo, nombre, frozenset(contenedor), preexistente)


ESTADOS = {e.codigo: e for e in (
    # --- Daño por turno. Vivos en ambos contenedores desde siempre.
    _e('PSN', 'Veneno', AVENTURERO, MONSTRUO),
    _e('BLD', 'Sangrado', AVENTURERO, MONSTRUO),
    _e('BRN', 'Quemaduras', AVENTURERO, MONSTRUO),
    # --- Control. Escritos por on_hit_effect en ambos lados; los lectores pedían
    #     STUNNED y BLINDED, que es exactamente el defecto que este módulo cierra.
    _e('STN', 'Aturdimiento', AVENTURERO, MONSTRUO),
    _e('BLN', 'Ceguera', AVENTURERO, MONSTRUO),
    # --- Buffs y banderas de turno. Sólo del aventurero.
    _e('INSPIRED', 'Inspirado', AVENTURERO),
    _e('REACTION_USED', 'Reacción usada', AVENTURERO),
    _e('RAGING', 'Furia', AVENTURERO),
    _e('DODGING', 'Esquivando', AVENTURERO),
    _e('RECKLESS', 'Temerario', AVENTURERO),
    _e('INFUSED_WEAPON', 'Arma infundida', AVENTURERO),
)}

CODIGOS_AVENTURERO = frozenset(c for c, e in ESTADOS.items() if AVENTURERO in e.contenedor)
CODIGOS_MONSTRUO = frozenset(c for c, e in ESTADOS.items() if MONSTRUO in e.contenedor)

# Nombres legibles para los mensajes del guion. Reemplaza el dict `eff_names` que vivía
# suelto en `combat.py` y que sólo cubría cinco de los once códigos.
NOMBRES = {c: e.nombre for c, e in ESTADOS.items()}


def es_preexistente(codigo):
    """True if this status predates the vocabulary — i.e. Phase 1 repaired it, not invented it."""
    estado = ESTADOS.get(codigo)
    return bool(estado and estado.preexistente)
