"""Standalone check for the contract between `guild_status` and the TUI that renders it.

Run: docker compose exec -T web python -m tests.test_guild_contract

This exists because the same defect has now shipped three times in one table, and every
time it looked like data:

  - `adv.get("adv_class", "BBN")`      -> every adventurer was a barbarian
  - `adv.get("current_hp", 0)`         -> every adventurer sat at 0/0 HP
  - `adv.get("is_recovering")`         -> every adventurer was "Disponible"

`dict.get` with a default cannot fail, so a key the payload never sends renders a constant
that is indistinguishable from a real value. The only thing that catches this class is
asserting the producer's key set against what the consumer actually reads.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from rest_framework.test import APIRequestFactory  # noqa: E402

from posada.views import guild_status  # noqa: E402

# Every key `cli/tui/posada_screens.py` reads off an adventurer dict. Adding an `adv.get(...)`
# there without adding it here is the bug this file exists to stop, so keep the two in step.
#   render_guild_status  -> posada_screens.py:2044-2065
#   the party filter     -> posada_screens.py:101
LEIDAS_POR_LA_TUI = {
    "id", "name", "class_name", "level", "xp", "hp", "wealth_summary", "is_recovering",
}

# Presence is not usefulness: `wealth` and `equipment` are present but are raw dicts, and
# rendering either lands a Python literal in a table cell. This check cannot know intent, so
# the keys that must never be rendered directly are named here instead.
NO_RENDERIZABLES = {"wealth", "equipment", "rpg_skills", "grimoire"}

fallos = 0


def check(cond, msg):
    """Returns whether it passed, so a failing test cannot also print its OK line."""
    global fallos
    if not cond:
        fallos += 1
        print(f"FALLÓ: {msg}")
    return bool(cond)


def test_el_payload_trae_todo_lo_que_la_tui_lee():
    resp = guild_status(APIRequestFactory().get("/"))
    check(resp.status_code == 200, f"guild_status respondió {resp.status_code}")

    aventureros = resp.data.get("adventurers")
    check(isinstance(aventureros, list), "el payload no trae una lista 'adventurers'")
    if not aventureros:
        print("AVISO · no hay aventureros en la base; el contrato no se pudo verificar")
        return

    completos = True
    for adv in aventureros:
        faltantes = LEIDAS_POR_LA_TUI - set(adv)
        completos &= check(not faltantes, f"«{adv.get('name')}» no trae {sorted(faltantes)}")
    if completos:
        print(f"OK · {len(aventureros)} aventurero(s) traen las "
              f"{len(LEIDAS_POR_LA_TUI)} claves que la TUI lee")


def test_la_tabla_recibe_una_celda_por_columna():
    """The row and its header are declared 130 lines apart, so nothing but this compares them.

    Textual pads a short row with blanks instead of raising, which is why six values into a
    seven-column table shifted every column silently for as long as it did.
    """
    import re
    fuente = open("cli/tui/posada_screens.py", encoding="utf-8").read()

    cabecera = re.search(
        r'table_adv\s*=\s*self\.query_one\("#all_adventurers_table",\s*DataTable\)\s*\n'
        r'\s*table_adv\.add_columns\((.*?)\)', fuente, re.S)
    check(cabecera is not None, "no se encontró el add_columns de #all_adventurers_table")
    if not cabecera:
        return
    columnas = len(re.findall(r'"[^"]+"', cabecera.group(1)))

    fila = re.search(r'table_adv\.add_row\((.*?)\n\s*\)', fuente, re.S)
    check(fila is not None, "no se encontró el add_row de table_adv")
    if not fila:
        return
    cuerpo = re.sub(r'#[^\n]*', '', fila.group(1))          # comments carry commas too
    celdas = [t for t in re.split(r',(?![^()]*\))', cuerpo)
              if t.strip() and not t.strip().startswith("key=")]

    ok = check(len(celdas) == columnas,
               f"la tabla declara {columnas} columnas y la fila manda {len(celdas)} celdas")

    for clave in NO_RENDERIZABLES:
        ok &= check(f'"{clave}"' not in cuerpo and f"'{clave}'" not in cuerpo,
                    f"la fila renderiza «{clave}», que es un dict crudo, no un texto")

    if ok:
        print(f"OK · la tabla del gremio manda {len(celdas)} celdas para {columnas} columnas, "
              f"ninguna cruda")


if __name__ == "__main__":
    PRUEBAS = [
        test_el_payload_trae_todo_lo_que_la_tui_lee,
        test_la_tabla_recibe_una_celda_por_columna,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_guild_contract: {len(PRUEBAS) - fallos}/{len(PRUEBAS)}")
    raise SystemExit(1 if fallos else 0)
