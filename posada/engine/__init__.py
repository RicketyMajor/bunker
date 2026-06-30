"""posada.engine — Motor de la Posada RPG.

Este paquete reemplaza al antiguo módulo monolítico engine.py.
Re-exporta todos los símbolos públicos para mantener 100% de
compatibilidad hacia atrás con imports existentes como:

    from .engine import generate_session_script, process_session_completion, ...
    from posada.engine import consolidate_wealth, ...
"""
# Re-exportar todo el contenido legacy (funciones, constantes, etc.)
from posada.engine.legacy import *  # noqa: F401,F403

# Re-exportar la función principal desde el runner modular
from posada.engine.runner import generate_session_script  # noqa: F401
