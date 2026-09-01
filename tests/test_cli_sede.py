"""`cli/sede.py` — the CLI's single HTTP seat.

Runs on the HOST: no database, no container. `httpx` is stabbed on the module the seat
actually reaches through, so nothing leaves the machine.

    .venv/bin/python -m tests.test_cli_sede

What it pins is the seat's one promise: every call carries `X-Bunker-Api-Token`, and nothing
else about the call changes. The seat exists because `httpx` has no module-level default
headers — unlike `axios.defaults`, which is why the scraper needs one line and this needs
a module.

NOT `cli/api.py`, which the plan asked for: that name is TAKEN by a live 192-line ISBN
oracle (`fetch_book_by_isbn`) that `books/views.py:13` imports and runs inside `web`.
"""
import cli.sede as sede

fallos = 0


def check(cond, etiqueta):
    global fallos
    if cond:
        print(f'  ok  {etiqueta}')
    else:
        print(f'  FALLA {etiqueta}')
        fallos += 1


capturado = {}


def cab(nombre):
    """La cabecera, o None. Nunca KeyError: un fallo tiene que ser un FALLA atribuible,
    no una excepcion que aborta las comprobaciones de abajo."""
    return dict(capturado.get('headers') or {}).get(nombre)


def falso(url, **kw):
    capturado.clear()
    capturado.update(url=url, **kw)

    class R:
        status_code = 200

    return R()


for verbo in ('get', 'post', 'patch', 'delete'):
    setattr(sede.httpx, verbo, falso)

sede.get('http://x/api/books/')
check(cab(sede.CABECERA) == sede.config.API_TOKEN,
      'sede.get manda la cabecera de la API')

sede.post('http://x/api/books/', json={'a': 1}, headers={'Otra': 'z'})
check(cab('Otra') == 'z', 'no pisa las cabeceras que le pasan')
check(cab(sede.CABECERA) == sede.config.API_TOKEN,
      'y anade la suya junto a ellas')
check(capturado.get('json') == {'a': 1}, 'el resto de kwargs viaja intacto')

# Los cuatro verbos, no solo los dos de arriba: `delete` es el que mas duele si se escapa.
for verbo in ('get', 'post', 'patch', 'delete'):
    getattr(sede, verbo)('http://x/api/books/1/')
    check(cab(sede.CABECERA) == sede.config.API_TOKEN,
          f'sede.{verbo} manda la cabecera')

# `headers=None` explicito no es lo mismo que no pasarlo: httpx lo acepta y `dict(None)` revienta.
sede.get('http://x/api/books/', headers=None)
check(cab(sede.CABECERA) == sede.config.API_TOKEN,
      'headers=None no revienta y sigue mandando la cabecera')

# El dict del llamador NO se muta: reusarlo en dos llamadas no debe acumular nada nuestro.
mias = {'Otra': 'z'}
sede.get('http://x/api/books/', headers=mias)
check(mias == {'Otra': 'z'}, 'no muta el dict de cabeceras del llamador')

# EL CHOQUE DE NOMBRES, que es lo que rompio el respaldo. `X-Bunker-Token` ya era el contrato de
# /api/backup/ y /api/restore/ (bunker_core/views.py:47) y screens.py:670,686 lo mandan a mano con
# BUNKER_BACKUP_TOKEN. La sede lo pisaba con el de la API: 403 medido contra el servidor vivo.
check(sede.CABECERA != 'X-Bunker-Token',
      'la cabecera de la API NO se llama como la del respaldo')

sede.post('http://x/api/backup/', headers={'X-Bunker-Token': 'EL-DE-RESPALDO'})
check(cab('X-Bunker-Token') == 'EL-DE-RESPALDO',
      'un X-Bunker-Token del llamador llega INTACTO (el respaldo depende de esto)')
check(cab(sede.CABECERA) == sede.config.API_TOKEN,
      'y la de la API viaja ADEMAS, no en su lugar')

# `setdefault`, no asignacion: un llamador que ponga la nuestra a proposito gana.
sede.get('http://x/api/', headers={sede.CABECERA: 'EL-MIO'})
check(cab(sede.CABECERA) == 'EL-MIO', 'un valor explicito del llamador gana sobre el nuestro')

# La sede NO es el oraculo de ISBN. Si algun dia alguien reusa el nombre, esto enrojece.
import cli.api
check(hasattr(cli.api, 'fetch_book_by_isbn'),
      'cli/api.py sigue siendo el oraculo de ISBN que books/views.py importa')

print(f"\ntest_cli_sede: {'0 fallos' if not fallos else f'{fallos} FALLOS'}")
raise SystemExit(1 if fallos else 0)
