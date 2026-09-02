"""Toda ruta bajo /api/ exige X-Bunker-Api-Token, salvo la allowlist.

Las rutas salen del RESOLVEDOR de Django, nunca de una lista a mano. Una lista escrita a mano es
como `movil_estado` se habria quedado fuera: es una vista Django PLANA al lado de 18 de DRF, y una
comprobacion que recorra los ViewSets encuentra 18 cosas verdes y ningun agujero. Por eso el
guardia es un MIDDLEWARE y no `DEFAULT_PERMISSION_CLASSES`, que solo alcanza a vistas de DRF.

Run: docker compose exec -T web python -m tests.test_auth_api
"""
import os

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

print(f"\ntest_auth_api: {len(rutas)} rutas · {'0 fallos' if not fallos else f'{fallos} FALLOS'}")
raise SystemExit(1 if fallos else 0)
