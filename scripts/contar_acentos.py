#!/usr/bin/env python3
"""How many Python comment lines are still in Spanish, by ONE stated instrument.

    python3 scripts/contar_acentos.py [--detalle]

WHY THIS FILE EXISTS. `CLAUDE.md` says code comments are English; the tree has not caught up, and
the backlog has carried the size of that debt since July. FOUR sessions have produced FOUR
numbers — 289, 317, 278/279, and 461 here — and they were four different instruments, so none of
them could be compared with the previous one. That, not the debt, is what this file closes: from
now on the number has a name attached.

WHAT IT COUNTS, exactly:
  · files: `git ls-files '*.py'` — tracked only, so the venv and node_modules never enter;
  · `#` comments: via `tokenize`, NOT a regex. A `#` inside a string is not a comment, and a
    regex counts it;
  · docstring lines: via `ast`, on modules, classes and functions;
  · "Spanish" is approximated by an accented character or ñ. That is a PROXY and it undercounts:
    an unaccented Spanish comment ("Se lee por peticion y no al importar") is invisible to it.
    The real debt is larger than whatever this prints. Say so when quoting it.
"""
import ast
import collections
import io
import pathlib
import re
import subprocess
import sys
import tokenize

ACENTOS = re.compile(r'[áéíóúüñÁÉÍÓÚÜÑ¿¡]')
RAIZ = pathlib.Path(__file__).resolve().parent.parent


def contar():
    ficheros = subprocess.run(['git', 'ls-files', '*.py'], cwd=RAIZ,
                              capture_output=True, text=True).stdout.split()
    por_fichero = collections.Counter()
    totales = collections.Counter()
    for f in ficheros:
        try:
            src = (RAIZ / f).read_text(encoding='utf-8')
            toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
            arbol = ast.parse(src)
        except (OSError, SyntaxError, tokenize.TokenError):
            totales['ilegibles'] += 1
            continue
        com = [t.string for t in toks if t.type == tokenize.COMMENT]
        docs = [l for n in ast.walk(arbol)
                if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                for l in (ast.get_docstring(n, clean=False) or '').splitlines()]
        totales['comentarios'] += len(com)
        totales['docstrings'] += len(docs)
        a = sum(1 for c in com if ACENTOS.search(c))
        b = sum(1 for l in docs if ACENTOS.search(l))
        totales['comentarios_es'] += a
        totales['docstrings_es'] += b
        if a + b:
            por_fichero[f] = a + b
    return len(ficheros), totales, por_fichero


if __name__ == '__main__':
    n, t, por_fichero = contar()
    print(f"ficheros .py rastreados : {n}"
          + (f"  ({t['ilegibles']} ilegibles)" if t['ilegibles'] else ""))
    print(f"comentarios `#`         : {t['comentarios']:5d}  ·  con acento/ñ: {t['comentarios_es']}")
    print(f"lineas de docstring     : {t['docstrings']:5d}  ·  con acento/ñ: {t['docstrings_es']}")
    print(f"TOTAL con acento/ñ      : {t['comentarios_es'] + t['docstrings_es']}"
          f"  en {len(por_fichero)} ficheros")
    print("\n(proxy: un comentario en castellano SIN acentos no se cuenta. La deuda real es mayor.)")
    if '--detalle' in sys.argv:
        print("\npor fichero:")
        for f, c in por_fichero.most_common():
            print(f"  {c:4d}  {f}")
