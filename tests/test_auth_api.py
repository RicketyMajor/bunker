"""Toda ruta bajo /api/ exige X-Bunker-Api-Token, salvo la allowlist.

Las rutas salen del RESOLVEDOR de Django, nunca de una lista a mano. Una lista escrita a mano es
como `movil_estado` se habria quedado fuera: es una vista Django PLANA al lado de 18 de DRF, y una
comprobacion que recorra los ViewSets encuentra 18 cosas verdes y ningun agujero. Por eso el
guardia es un MIDDLEWARE y no `DEFAULT_PERMISSION_CLASSES`, que solo alcanza a vistas de DRF.

Run: docker compose exec -T web python -m tests.test_auth_api
"""
import io
import os
import pathlib

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.core.handlers.wsgi import WSGIRequest    # noqa: E402
from django.http import HttpResponse                 # noqa: E402
from django.test import Client                       # noqa: E402
from django.urls import get_resolver                 # noqa: E402

from bunker_core.auth import ABIERTAS as ABIERTAS_DEL_CODIGO   # noqa: E402
from bunker_core.auth import TokenDeBunker           # noqa: E402

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
check(len(rutas) >= 40, f'el resolvedor encontro {len(rutas)} rutas concretas bajo /api/ (medidas 49 el 2026-09-02, tras retirar /api/backups/)')
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

# --- /admin/ IS NOT MOUNTED UNLESS ASKED FOR ---
#
# 41 routes this middleware does NOT cover — they are not under `/api/` — which the `0.0.0.0`
# port publishes to the whole LAN. The only thing between them and the collection was Django's
# login, inert only because there are no accounts. See `bunker_core/urls.py` for why it is closed
# by NOT mounting it rather than with an IP guard.
#
# The expectation is tied to the FLAG, not to "404 always": turning the admin on is legitimate
# (it is the watchers' only UI) and a suite that goes red for using it would push towards not
# running it. What it pins is that the mount and the flag cannot diverge.
_admin_pedido = os.environ.get('BUNKER_ADMIN') == '1'
_admin_montado = any(str(p.pattern).startswith('admin/') for p in get_resolver().url_patterns)
check(_admin_montado == _admin_pedido,
      f'/admin/ mounted={_admin_montado} and BUNKER_ADMIN=1 asked={_admin_pedido}: they agree')
check(c.get('/admin/').status_code == (302 if _admin_pedido else 404),
      f'and /admin/ answers accordingly ({c.get("/admin/").status_code})')

# --- THE REPEATED-SLASH VECTOR ---
#
# `//api/books/library/` does not start with `/api/`. Un-normalised, the guard's `startswith` lets
# it through whole.
#
# ⚠ THIS CANNOT BE MEASURED WITH THE `Client`, which is why handoff 049 recorded it backwards as
# "gives 404, the resolver saves it". The `Client` parses `//api/x` as a PROTOCOL-RELATIVE URL: it
# takes `api` as the host and requests `/x`. That 404 was the harness. Verified 2026-09-02 by
# spying on the middleware: under the `Client`, `request.path` arrives as `/books/library/`.
#
# It is invisible against the live server too, for the opposite reason: `runserver`'s WSGI layer
# collapses the slashes and `PATH_INFO` arrives already clean (raw request line in the log, 403 in
# the response). That is a property of the DEVELOPMENT server. Behind a WSGI that does not
# collapse, `request.path` keeps both slashes — checked by building the `WSGIRequest` by hand,
# which is what `_al_guardia` does. It is measured where the defect can exist, not where the
# environment already hides it.
_PASA = 299   # sentinel: NOT a code any view returns, so a 299 can only come from the
              # `get_response` below — that is, "the guard let it through".


def _al_guardia(path_info, token=None):
    entorno = {'REQUEST_METHOD': 'GET', 'PATH_INFO': path_info, 'SCRIPT_NAME': '',
               'SERVER_NAME': 'testserver', 'SERVER_PORT': '80', 'wsgi.input': io.BytesIO()}
    if token is not None:
        entorno['HTTP_X_BUNKER_API_TOKEN'] = token
    guardia = TokenDeBunker(lambda _req: HttpResponse('paso', status=_PASA))
    return guardia(WSGIRequest(entorno)).status_code


# VACUITY FIRST, IN BOTH DIRECTIONS: if the sentinel were unreachable, everything below would be
# "403 always" and would come out green with the guard shutting the door on everyone.
check(_al_guardia('/movil/') == _PASA,
      'the sentinel is reachable: what is not /api/ passes through the guard')
check(_al_guardia('/api/books/library/') == 403,
      'positive control: the canonical route with no header gives 403')
check(_al_guardia('/api/books/library/', tok) == _PASA,
      'and WITH the header it passes through (otherwise the 403s below would say nothing)')

# ⚠ `/api//books/library/` IS THE ONE THAT ATTRIBUTES NOTHING, and that is measured: with the
# normalisation removed by hand, 3 of these 4 go red and that one stays GREEN — it already starts
# with `/api/`, so its internal slash never entered the decision. It stays as a regression guard on
# the "still passes" side, not as proof of the normalisation. The ones that prove it start `//`.
for vector in ['//api/books/library/', '///api/books/library/', '/api//books/library/',
               '//api//books//library/']:
    check(_al_guardia(vector) == 403,
          f'{vector} does NOT bypass the guard (repeated slashes normalised before deciding)')
    check(_al_guardia(vector, tok) == _PASA,
          f'{vector} WITH the header passes: the guard normalises to DECIDE, not to route')

# The allowlist is compared against the already-normalised path, or `//api/health/` would become
# paid-for and `web`'s healthcheck — which the three scrapers wait on to start — would begin
# failing.
check(_al_guardia('//api/health/') == _PASA,
      '//api/health/ stays open: the allowlist is read against the normalised path')

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
