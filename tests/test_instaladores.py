"""The two installers do the same steps, in the same order.

    .venv/bin/python -m tests.test_instaladores

Two files that do the same thing drift apart. A single installer written in Python was the
alternative, and Alonso chose the native pair on 2026-08-31 knowing that. This check is the
mitigation of that decision, not decoration — same shape as `tests/test_backup_apps.py`, which
watches the drift between two hand-written lists.

Each step is marked in both files with a `#PASO: <name>` comment.

WHY THIS IS NOT `sh == ps1` AND NOTHING ELSE: an empty list equals an empty list. If the marker
comment ever changes shape, `pasos()` returns `[]` for both files and the equality passes while
measuring nothing — the same vacuous green that bit Tasks 2, 4 and 5 on 2026-08-31. The count
guard runs FIRST and fails loudly instead.

`install.ps1` CANNOT BE RUN OR VERIFIED FROM THIS MACHINE. This check proves the two files
declare the same steps; it does NOT prove the PowerShell one works. Nothing in this repo can.
"""
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent

fallos = 0


def check(cond, etiqueta):
    global fallos
    if cond:
        print(f'  ok  {etiqueta}')
    else:
        print(f'  FALLA {etiqueta}')
        fallos += 1


def pasos(fichero):
    """Los marcadores REALES, no las menciones en la prosa.

    Anclado a principio de linea a proposito. Sin el ancla, la cabecera de cada instalador
    —que explica que los `#PASO:` deben coincidir— se contaba como un paso mas, y los dos
    ficheros declaraban 7 en vez de 6. Es el mismo defecto que corrompio `cli/doctor.py` el
    2026-08-31: un patron que caso la mencion del docstring en vez de la lista.
    """
    ruta = RAIZ / fichero
    if not ruta.exists():
        return None
    return re.findall(r'(?m)^\s*#PASO:\s*(\S+)', ruta.read_text(encoding='utf-8'))


def lineas_ejecutables(texto):
    """El fichero sin sus comentarios de linea entera.

    Un instalador puede EXPLICAR por que no usa sudo sin invocarlo. Comprobar sobre el texto
    crudo confunde la explicacion con el hecho.
    """
    return '\n'.join(l for l in texto.splitlines() if not l.lstrip().startswith('#'))


sh, ps1 = pasos('install.sh'), pasos('install.ps1')

check(sh is not None, 'install.sh existe')
check(ps1 is not None, 'install.ps1 existe')

if sh is None or ps1 is None:
    print(f"\ntest_instaladores: {fallos} FALLOS (falta un instalador)")
    raise SystemExit(1)

# VACUIDAD PRIMERO. Menos de 6 marcadores significa que el patron dejo de casar, y entonces la
# igualdad de abajo compara [] con [] y sale verde sin haber leido un solo paso.
check(len(sh) >= 6, f'install.sh declara {len(sh)} pasos (menos de 6 = el patron no casa)')
check(len(ps1) >= 6, f'install.ps1 declara {len(ps1)} pasos (menos de 6 = el patron no casa)')

check(sh == ps1,
      f'los pasos coinciden y en el mismo orden\n'
      f'      sh : {sh}\n'
      f'      ps1: {ps1}')

# Un paso repetido en un fichero y no en el otro pasaria la igualdad si ambos derivaran, pero
# un duplicado dentro de UN fichero es casi siempre un copiar-pegar a medias.
check(len(sh) == len(set(sh)), f'install.sh no repite ningun paso: {sh}')

# LAS DOS COMPROBACIONES DE ABAJO CORREN SOBRE LOS DOS FICHEROS, no solo sobre el de bash.
# Cuando solo miraban `install.sh`, borrar la generacion de `BUNKER_API_TOKEN` de `install.ps1`
# dejaba este fichero VERDE mientras cada instalacion de Windows levantaba una API que responde
# 503 a todo. Vigilar la lista de pasos y no su contenido es vigilar la mitad.
textos = {f: (RAIZ / f).read_text(encoding='utf-8') for f in ('install.sh', 'install.ps1')}

# NINGUN INSTALADOR NECESITA `sudo`. El de antes hacia `sudo ln -sf` para un enlace que pip ya
# crea en .venv/bin/bunker: pedia la contrasena del usuario para nada.
for fichero, texto in textos.items():
    check('sudo' not in lineas_ejecutables(texto), f'{fichero} no invoca sudo')

# Los cuatro secretos se generan por instalacion. Un valor por defecto escrito en el fichero es
# un valor publico, y `bunker_core/auth.py` es ahora la unica autenticacion de la API.
for secreto in ['POSTGRES_PASSWORD', 'DJANGO_SECRET_KEY', 'BUNKER_BACKUP_TOKEN', 'BUNKER_API_TOKEN']:
    for fichero, texto in textos.items():
        check(secreto in texto, f'{fichero} nombra {secreto}')

print(f"\ntest_instaladores: {len(sh)} pasos · {'0 fallos' if not fallos else f'{fallos} FALLOS'}")
raise SystemExit(1 if fallos else 0)
