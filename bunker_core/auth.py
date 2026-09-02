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
import secrets

from django.http import JsonResponse

# `/api/health/` la pide el healthcheck de `web` en docker-compose.yml:49, y los tres scrapers
# esperan a ese healthcheck para arrancar (`depends_on: service_healthy`). Cerrarla no protege
# nada nuevo —no devuelve datos de la coleccion— y deja el stack entero sin levantar.
ABIERTAS = frozenset({'/api/health/'})

CABECERA = 'X-Bunker-Api-Token'


class TokenDeBunker:
    """Exige `X-Bunker-Api-Token` en todo `/api/`, salvo `ABIERTAS`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and request.path not in ABIERTAS:
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
