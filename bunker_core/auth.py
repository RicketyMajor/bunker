"""La UNICA sede de autenticacion de la API.

Un MIDDLEWARE y no `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']`, y la razon esta medida: los
permisos de DRF solo alcanzan a vistas de DRF. `movil_estado` y `movil_assets` —que sirven al
telefono su estado de lectura entero y su manifiesto de assets— son vistas Django PLANAS sin
`@api_view` (comprobado 2026-08-31), asi que una permission_class las habria dejado abiertas de
par en par mientras las 18 comprobaciones sobre los ViewSets salian verdes.

Falla CERRADO, igual que `bunker_core/views.py:_reject_if_bad_token`: sin `BUNKER_API_TOKEN` en el
entorno no se atiende nada, y se dice con un 503. Un valor por defecto escrito en el codigo es un
valor publico, y un valor publico no protege nada.

NO comparte cabecera con el respaldo. `X-Bunker-Token` es de `/api/backup/` y `/api/restore/`, que
`views.py` compara contra `BUNKER_BACKUP_TOKEN`; esta es `X-Bunker-Api-Token`. Una peticion de
respaldo pasa por las DOS guardias, y con un solo nombre de cabecera eso seria imposible de
satisfacer con dos secretos distintos — la salida facil (igualarlos) convierte el token que se
reparte a tres scrapers, la PWA y el APK en la llave de `loaddata`.
"""
import os
import re
import secrets

from django.http import JsonResponse

# `/api/health/` la pide el healthcheck de `web` en docker-compose.yml:49, y los tres scrapers
# esperan a ese healthcheck para arrancar (`depends_on: service_healthy`). Cerrarla no protege
# nada nuevo —no devuelve datos de la coleccion— y deja el stack entero sin levantar.
ABIERTAS = frozenset({'/api/health/'})

CABECERA = 'X-Bunker-Api-Token'

# `//api/books/library/` does not start with `/api/`, so without this the `startswith` below lets
# it through whole. It is NOT exploitable today, and the reason is not this guard: measured
# 2026-09-02 against the live server, the request line arrives raw — `GET //api/books/library/` is
# what the access log shows — but `runserver`'s WSGI layer collapses the slashes and `PATH_INFO`
# reaches Django already as `/api/...`. That is a property of the DEVELOPMENT server, not of the
# Bunker: build a `WSGIRequest` by hand with `PATH_INFO='//api/x/'` and `request.path` DOES keep
# both slashes. The day this runs behind gunicorn the hole is real, and it costs one substitution.
#
# ⚠ THE TEST `Client` CANNOT MEASURE THIS VECTOR, which is why handoff 049 recorded it backwards.
# It parses `//api/x` as a protocol-relative URL: it takes `api` as the HOST and requests `/x`,
# which 404s. That 404 was the harness, not the guard. It is checked in `tests/test_auth_api.py`
# by calling the middleware with `PATH_INFO` set by hand.
_BARRAS = re.compile(r'/{2,}')


class TokenDeBunker:
    """Exige `X-Bunker-Api-Token` en todo `/api/`, salvo `ABIERTAS`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Normalised to DECIDE, never to route: the resolver still sees `request.path` untouched,
        # so this cannot make reachable a route that is not reachable today.
        ruta = _BARRAS.sub('/', request.path)
        if ruta.startswith('/api/') and ruta not in ABIERTAS:
            # Se lee por peticion y no al importar: asi apagar la variable es una inversion que
            # se puede correr sin reconstruir el contenedor, y el coste es un dict lookup.
            esperado = os.environ.get('BUNKER_API_TOKEN')
            if not esperado:
                return JsonResponse(
                    {"error": "BUNKER_API_TOKEN no esta configurado en el servidor."}, status=503)
            recibido = request.headers.get(CABECERA) or ''
            # compare_digest y no `==`: la comparacion de cadenas corta en el primer byte
            # distinto, y eso es un oraculo de tiempo sobre el token.
            if not secrets.compare_digest(recibido, esperado):
                return JsonResponse(
                    {"error": "Acceso denegado: token ausente o invalido."}, status=403)
        return self.get_response(request)
