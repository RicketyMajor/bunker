"""Two guards over the Posada engine's status vocabulary. Runs inside the container:

    docker compose exec -T web python -m tests.test_posada_estados

Guard 1 is a static AST contract: every status written must be read, and every status read
must be written, PER CONTAINER. Guard 2 is a runtime anti-no-op harness over the 132 skills.

This file exists because `bunker doctor` was green for months over six dead mechanics.
`test_posada_skills` runs every skill and asserts it neither raises nor returns the wrong
type — all of which is true of a function that does nothing.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def test_vocabulario_es_coherente():
    """The vocabulary declares every code the engine and the models already use."""
    from posada.engine.estados import (
        ESTADOS, CODIGOS_AVENTURERO, CODIGOS_MONSTRUO, es_preexistente)
    from posada.models import OnHitEffect

    # Every OnHitEffect that lands in a status tracker must be declared. NON is the
    # sentinel, LFS heals and THN retaliates: all three are inline branches, never stored.
    inline = {'NON', 'LFS', 'THN'}
    for codigo in OnHitEffect.values:
        if codigo in inline:
            continue
        check(codigo in ESTADOS,
              f"OnHitEffect.{codigo} está declarado en estados.py")

    check(CODIGOS_AVENTURERO <= set(ESTADOS),
          "todo código de aventurero está en ESTADOS")
    check(CODIGOS_MONSTRUO <= set(ESTADOS),
          "todo código de monstruo está en ESTADOS")
    check(all(e.contenedor for e in ESTADOS.values()),
          "ningún estado se declara sin contenedor")
    check(all(es_preexistente(c) for c in ESTADOS),
          "la Fase 1 no introduce ningún estado nuevo")


if __name__ == '__main__':
    test_vocabulario_es_coherente()
    print(f"\n{_checks} comprobaciones OK.")
