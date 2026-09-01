"""The CLI's ONLY HTTP seat.

There was `cli/config.py:BASE_URL` and nothing else: the 111 calls under `cli/` went straight
to `httpx.get/post/patch/delete`, so the base URL had one home and the auth header would have
had 111. Measured 2026-08-31: 111 calls across 8 files — library_screen 37, movie_screens 29,
music_screens 29, main 7, screens 6, and one each in doctor/modals/tabs.

`httpx` has no module-level default headers (it is not `axios.defaults`), so the only way 111
sites send one header is for them to stop being 111 sites.

NOT named `cli/api.py`, which the plan asked for: that name is taken by a live 192-line ISBN
oracle that `books/views.py:13` imports and runs inside `web`. Overwriting it would have
deleted `fetch_book_by_isbn` from under a Django view.
"""
import httpx

from cli import config

# ponytail: four loose functions, not a shared `httpx.Client`. The ceiling is connection
# pooling — every call opens its own TCP connection to localhost. Swap for a module-level
# `httpx.Client(headers=..., base_url=...)` the day a screen makes enough calls for the
# handshake to show up, or the day this needs a default timeout in one place.


# NO `X-Bunker-Token`, que es lo que el plan pedia: ESE NOMBRE YA ESTA COGIDO. Es el contrato de
# /api/backup/ y /api/restore/, que `bunker_core/views.py:47` lee y compara con BUNKER_BACKUP_TOKEN,
# y que `cli/tui/screens.py:670,686` mandan a mano. Reusarlo pisaba el token de respaldo con el de
# la API: medido contra el servidor vivo, respaldo y restauracion respondian 403. Y `setdefault`
# no bastaba como arreglo de fondo: en la Tarea 5 el middleware guarda TODO /api/, respaldo
# incluido, asi que esa peticion tiene que llevar LOS DOS tokens a la vez — y dos valores no caben
# en una cabecera. Nombres distintos es lo unico que sobrevive a la Tarea 5.
CABECERA = 'X-Bunker-Api-Token'


def _con_token(kw):
    # Las cabeceras del llamador GANAN, la nuestra incluida (`setdefault`): pasar por este modulo
    # no debe poder pisar en silencio un valor que el llamador puso a proposito. Y se copia el
    # dict: mutar el del llamador le mete nuestra cabecera en llamadas que no pasan por aqui.
    cabeceras = dict(kw.pop('headers', None) or {})
    cabeceras.setdefault(CABECERA, config.API_TOKEN)
    return {**kw, 'headers': cabeceras}


def get(url, **kw):     return httpx.get(url, **_con_token(kw))
def post(url, **kw):    return httpx.post(url, **_con_token(kw))
def patch(url, **kw):   return httpx.patch(url, **_con_token(kw))
def delete(url, **kw):  return httpx.delete(url, **_con_token(kw))
