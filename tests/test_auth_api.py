"""Toda ruta bajo /api/ exige X-Bunker-Api-Token, salvo la allowlist.

Las rutas salen del RESOLVEDOR de Django, nunca de una lista a mano. Una lista escrita a mano es
como `movil_estado` se habria quedado fuera: es una vista Django PLANA al lado de 18 de DRF, y una
comprobacion que recorra los ViewSets encuentra 18 cosas verdes y ningun agujero. Por eso el
guardia es un MIDDLEWARE y no `DEFAULT_PERMISSION_CLASSES`, que solo alcanza a vistas de DRF.

Run: docker compose exec -T web python -m tests.test_auth_api
"""
import os
import pathlib

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.test import Client                       # noqa: E402
from django.urls import get_resolver                 # noqa: E402

from bunker_core.auth import ABIERTAS as ABIERTAS_DEL_CODIGO   # noqa: E402

# LITERAL, y no la del middleware. Importar `ABIERTAS` y comprobar contra ella hace que la prueba
# se mueva CON el codigo: vaciar la allowlist salia VERDE porque la expectativa se vaciaba a la
# vez y `/api/health/` caia en la rama del 403. Medido invirtiendo, no leyendo.
# `/api/health/` tiene que seguir abierta porque la pide el healthcheck de `web`
# (docker-compose.yml:49) y los tres scrapers esperan a ese healthcheck para arrancar.
ABIERTAS = {'/api/health/'}

fallos = 0


def check(cond, etiqueta):
    global fallos
    if cond:
        print(f'  ok  {etiqueta}')
    else:
        print(f'  FALLA {etiqueta}')
        fallos += 1


def andar(res, prefijo=''):
    """Recursivo, y con el prefijo acumulado. El recorrido de un solo nivel del borrador perdia
    las rutas de los `include()` anidados y contaba dos veces las de primer nivel."""
    for p in res.url_patterns:
        if hasattr(p, 'url_patterns'):
            yield from andar(p, prefijo + str(p.pattern))
        else:
            yield prefijo + str(p.pattern)


# El router de DRF deja los anclajes de regex dentro del patron (`^directories/$`): sin quitarlos
# la URL no es pedible y el Client devolveria 404 — que no es 403 y habria pasado por agujero.
rutas = sorted({'/' + r.replace('^', '').replace('$', '')
                for r in andar(get_resolver())
                if r.startswith('api/') and '<' not in r and '(' not in r})

check(ABIERTAS_DEL_CODIGO == frozenset(ABIERTAS),
      f'la allowlist del codigo es exactamente la esperada; el codigo dice '
      f'{sorted(ABIERTAS_DEL_CODIGO)} y aqui se espera {sorted(ABIERTAS)}')

c = Client()

# VACUIDAD PRIMERO. Si el recorrido no encuentra rutas, TODO lo de abajo es verdad por vacio —
# y este fichero entero diria que la API esta protegida sin haber pedido una sola URL.
check(len(rutas) >= 40, f'el resolvedor encontro {len(rutas)} rutas concretas bajo /api/ (medidas 50)')
check(any(r.startswith('/api/movil/') for r in rutas),
      'el recorrido incluye las vistas Django PLANAS (/api/movil/), que es el agujero que '
      'una permission_class de DRF habria dejado abierto')

sin_guardia = []
for ruta in rutas:
    r = c.get(ruta)
    if ruta in ABIERTAS:
        check(r.status_code != 403,
              f'{ruta} sigue ABIERTA sin cabecera (llego {r.status_code}); la pide el '
              f'healthcheck de `web` y sin ella los tres scrapers no arrancan')
    elif r.status_code != 403:
        sin_guardia.append(f'{ruta} -> {r.status_code}')

check(not sin_guardia,
      f'{len(rutas) - len(ABIERTAS)} rutas sin cabecera responden 403; se colaron: {sin_guardia[:6]}')

# Y CON la cabecera, las mismas rutas responden lo de siempre: un guardia que rompe a todo el
# mundo tambien saldria verde en la mitad de arriba.
tok = os.environ['BUNKER_API_TOKEN']
cab = {'X-Bunker-Api-Token': tok}
check(c.get('/api/movil/estado/', headers=cab).status_code == 200,
      'con la cabecera, /api/movil/estado/ (vista plana) responde 200')
check(c.get('/api/books/library/', headers=cab).status_code == 200,
      'con la cabecera, /api/books/library/ (ViewSet de DRF) responde 200')
check(c.get('/api/stats/timeline/?module=books', headers=cab).status_code == 200,
      'con la cabecera, /api/stats/timeline/ responde 200')

# Un token EQUIVOCADO no es lo mismo que ninguno, y las dos tienen que dar 403.
check(c.get('/api/books/library/', headers={'X-Bunker-Api-Token': 'no-soy'}).status_code == 403,
      'un token equivocado tambien da 403')

# EL RESPALDO NECESITA LOS DOS TOKENS, y son cabeceras distintas a proposito: `X-Bunker-Token` lo
# lee bunker_core/views.py contra BUNKER_BACKUP_TOKEN, y este middleware lee la suya. Compartir
# nombre haria el respaldo IMPOSIBLE de satisfacer con dos secretos distintos.
check(c.post('/api/backup/', headers=cab).status_code == 403,
      'el respaldo con el token de la API pero SIN el suyo sigue siendo 403')
respaldo = {**cab, 'X-Bunker-Token': os.environ['BUNKER_BACKUP_TOKEN']}
check(c.post('/api/backup/', headers=respaldo).status_code == 200,
      'el respaldo con LAS DOS cabeceras pasa las dos guardias')

# Lo que NO es /api/ no lo toca: el telefono tiene que poder cargar el caparazon sin token.
check(c.get('/movil/').status_code == 200, '/movil/ sigue abierta (el telefono pide el token ahi)')

# EL TOKEN NO PUEDE APARECER EN NADA QUE SE SIRVA SIN TOKEN. `/movil/` y `/panel/` quedan abiertas
# para que el telefono cargue el caparazon y le PIDA el token; si el token viaja dentro de esa
# pagina, cualquiera en la LAN que la abra se lo lleva y el mecanismo entero no protege nada. Desde
# que el puerto es 0.0.0.0 (2026-09-01) «cualquiera en la LAN» dejo de ser hipotetico.
#
# SON CINCO SUPERFICIES, NO UNA. El plan nombraba `/movil/`. Contadas contra el servidor vivo:
# `/movil/`, `/panel/` y `/movil/asset/app.html` responden 200 sin cabecera (24269 bytes, el mismo
# HTML las tres), y los dos bundles bajo `/static/`.
#
# LOS BUNDLES SE LEEN DEL DISCO A PROPOSITO: el Client de test NO sirve `/static/` — devuelve un
# 404 de 179 bytes, y `token not in cuerpo` sobre ese 404 sale VERDE sin haber mirado el bundle.
# El disco vale como sujeto porque es byte a byte lo que se sirve: md5 comparados contra
# `curl` el 2026-09-01 (main.js a022821e…, selftest.js 680698c9…).
RAIZ = pathlib.Path(__file__).resolve().parent.parent

# SON OCHO RUTAS, NO TRES. `/movil/sw.js`, `/movil/manifest.json` y `/movil/selftest/` tambien
# se sirven sin cabecera y tambien son plantillas renderizadas: un `{{ token }}` en el service
# worker se distribuiria a cada telefono que lo cachee, y esta comprobacion no lo veria.
for ruta in ['/movil/', '/panel/', '/movil/asset/app.html',
             '/movil/sw.js', '/movil/manifest.json', '/movil/selftest/']:
    r = c.get(ruta)
    # VACUIDAD PRIMERO: un 404, un redirect o un cuerpo vacio tampoco contienen el token, y
    # pasarian la comprobacion de abajo sin haber servido la pagina.
    # El umbral es 200 bytes y no 1000: `manifest.json` es legitimamente pequeno. Lo que la
    # guardia tiene que descartar es un 404 (179 bytes) o un cuerpo vacio, no una pagina corta.
    check(r.status_code == 200 and len(r.content) > 200,
          f'{ruta} se sirve de verdad sin cabecera ({r.status_code}, {len(r.content)} bytes)')
    check(tok.encode() not in r.content, f'el token NO viaja en {ruta}')

# Los BUNDLES y TAMBIEN LAS FUENTES SIN EMPAQUETAR. `runserver --insecure` sirve todo lo que
# hay bajo `static/`, asi que `estado.js` y sus hermanos se descargan igual que el bundle: una
# build que inlinease el token en la fuente pasaria una comprobacion que solo mire `dist/`.
_ESTATICOS = ['dist/main.js', 'dist/selftest.js',
              'app.js', 'estado.js', 'panel.js', 'queue.js', 'main.js', 'selftest.js']
for nombre in _ESTATICOS:
    ruta = RAIZ / 'bunker_core/static/movil' / nombre
    # NO `read_bytes()` a pelo: `dist/` esta en .gitignore, asi que en un clon recien instalado
    # —antes del paso del bundle— esto lanzaba FileNotFoundError y MATABA el modulo a media
    # comprobacion. El traceback ocultaba que faltaba el bundle y las comprobaciones de despues
    # no llegaban a correr. Un fichero que falta es un FALLO con nombre, no una excepcion.
    if not ruta.exists():
        check(False, f'{nombre} existe (falta el bundle: corre `npm run build`)')
        continue
    datos = ruta.read_bytes()
    check(len(datos) > 200, f'{nombre} tiene contenido ({len(datos)} bytes)')
    check(tok.encode() not in datos, f'el token NO viaja en {nombre}')


print(f"\ntest_auth_api: {len(rutas)} rutas · {'0 fallos' if not fallos else f'{fallos} FALLOS'}")
raise SystemExit(1 if fallos else 0)
