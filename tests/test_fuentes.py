"""Relevance: does an item mention a watched author or series?

Runs inside the container:

    docker compose exec -T web python -m tests.test_fuentes

Ten of the twelve book strategies sweep an entire *novedades* page and never read the watch list,
so the board is 79 % rows nobody asked for. The obvious filter — does the title contain a watched
keyword — is falsified by the data: FIVE of the ten watchers are author names, and an author name
does not appear inside the title of their book. Measured 2026-08-30 against the 252 live rows, a
title-only filter discards 42 rows across 8 watched series, including the 14 One Punch-Man volumes
(watched through `Yusuke Murata`) and the 9 Punpun ones (through `Inio Asano`).

The end-to-end half drives the REAL view against the LIVE database, like tests/test_dedup.py, so
its fixture titles carry the ZZPrueba prefix. Do NOT rename them into realistic titles: the suite's
verdict would start depending on what the radar found last night.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402
from django.test import RequestFactory  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from books.models import Watcher, WishlistItem  # noqa: E402
from books.views import add_wishlist_item  # noqa: E402
from bunker_core.dedup import es_vigilado  # noqa: E402
from movies.models import MovieWatcher, MovieWishlist  # noqa: E402
from movies.views import MovieWishlistViewSet  # noqa: E402
from music.models import MusicWatcher, MusicWishlist  # noqa: E402
from music.views import MusicWishlistViewSet  # noqa: E402

VIGILADOS = ['Yusuke Murata', 'Berserk', 'Mariana Enriquez']

# (titulo, autor, esperado, por que)
CASOS = [
    ('ZZPrueba Berserk 42', 'Berserk', True,
     'la serie llega en el campo de autor: las estrategias la escriben ahi, medido 2026-08-31'),
    ('ZZPrueba Berserk 42', '', False,
     'y SUELTA en el titulo ya no basta — 33 filas de basura entraban por esa via'),
    ('ZZPrueba One Punch-Man 24', 'Yusuke Murata', True,
     'EL CASO QUE IMPORTA: la serie NO se vigila, su autor SI'),
    ('ZZPrueba Este es el mar', 'Mariana Enríquez', True,
     'el autor llega acentuado y el vigilado no'),
    ('ZZPrueba Incluye paginas a color', '', False, 'reclamo de tienda'),
    ('ZZPrueba ARZAK El pequeno panteon', 'Moebius', False, 'autor real, no vigilado'),
    ('ZZPrueba One Punch-Man 24', '', False,
     'sin autor no hay nada que casar: por eso la estrategia debe etiquetar'),
]

# El corpus documentado del handoff 045, con el signo que la regla nueva les debe dar. Diez de
# basura y seis colaboraciones legitimas. Los vigilados son los VIVOS de musica: esta tabla no
# escribe nada, solo interroga la regla.
VIGILADOS_CREDITO = ['Daft Punk', 'Justice', 'The Chemical Brothers', 'Kavinsky']
EXCLUSIONES_CREDITO = {'Kavinsky': ['M!das', 'Mdas', 'Finesse Ngara']}

# (titulo, persona, esperado, por que)
CASOS_CREDITO = [
    # -- la via de la PERSONA: credito entero, no subcadena
    ('Think or Sink: 1984-85 Recordings', 'Justice League (2)', False,
     "'Justice' esta DENTRO de un credito mas largo"),
    ('Key To World Peace', 'Prophetic Justice Ministry', False, 'idem, en medio del nombre'),
    ('Victorious 2. 0', 'Victorious Cast & Victoria Justice', False,
     "el credito es 'victoria justice', no 'justice'"),
    ('Nightcall - Single', 'Kavinsky, Angèle & Phoenix', True,
     'LA QUE IMPORTA: colaboracion real, el vigilado es un credito entero'),
    ('Get Lucky / Spacer', 'Daft Punk / Sheila & B. Devotion', True, 'separador "/"'),
    ('Outsider (Donald Durand Rework)', 'Kavinsky & Donald Durand', True, 'separador "&"'),
    ('Galvanize [Chris Lake Remix]', 'The Chemical Brothers & Chris Lake', True,
     'el vigilado lleva articulo y sigue siendo un credito entero'),
    # -- la via del TITULO: solo dentro de una clausula de credito
    ('Justice - Single', 'Sevana', False, 'el vigilado suelto en el titulo no cuenta (x33)'),
    ('Divine Justice', 'Oscar Sanchez (3)', False, 'idem'),
    ('Stephen King', 'Ariel Bosi', False, 'un libro SOBRE King no es un libro DE King'),
    ('Starboy (feat. Daft Punk) [Kygo Remix] - Single', 'The Weeknd', True,
     'LA QUE IMPORTA: clausula feat. con el vigilado como credito entero'),
    ('Take Me Out (Daft Punk Remix)', 'Franz Ferdinand', True,
     'clausula de remix — esta fila esta VIVA en el tablon'),
    ('Justice (feat. Trombone Shorty) - Single', 'Dumpstaphunk', False,
     "'Justice' es el titulo, esta FUERA de la clausula"),
    ('Take a Hint (feat. Victoria Justice & Elizabeth Gillies)', 'Victorious Cast', False,
     'los creditos de la clausula son otros dos'),
    ('Digital Love (Daft Punk Cover)', 'Different Dream', False,
     'una version ajena: la clausula no abre ni cierra como credito'),
    ('Kavinsky (Nightcall) [AI COVER] - Single', 'MUSICODE', False,
     'el vigilado esta fuera de toda clausula'),
    # -- las exclusiones
    # EL TECHO, en sus DOS filas: son dos grafias del mismo homonimo keniano y excluyen filas
    # distintas — en el titulo el credito es 'mdas' y en el artista es 'm das'. Un solo caso
    # dejaba una de las dos sin ejercitar y pasaba por buena (visto en /code-review).
    ('Tingisha (feat. Kavinsky, Mchina & Mdas) - Single', 'Finesse Ngara', False,
     "el homonimo por la clausula del titulo: lo separa la exclusion 'Mdas'"),
    ('Nairobi Nights', 'Kavinsky & M!das', False,
     "el homonimo por el campo de artista: lo separa la exclusion 'M!das'"),
]

# Los ViewSets de cine y musica son DRF y necesitan su fabrica, que sabe de `format=json`.
_FABRICA = APIRequestFactory()

def rollback(fn):
    """Corre `fn` y deshace TODO lo que escriba, pase o falle.

    Mismo patron que tests/test_dedup.py, y aqui se gano a pulso: sin el, una inversion que
    fallaba su assert dejaba su fila de prueba en el tablon VIVO — y esa fila hacia que la
    siguiente corrida pasara por `ya_conocido` en vez de por la guardia de relevancia, con lo que
    la inversion de libros salia verde y la guardia se podia borrar entera sin que nadie lo viera.
    """
    try:
        with transaction.atomic():
            fn()
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _publicar(titulo, autor):
    """POST a /api/books/wishlist/add/ through the real view. Returns the status code."""
    peticion = RequestFactory().post(
        '/api/books/wishlist/add/',
        data={'title': titulo, 'author_string': autor},
        content_type='application/json',
    )
    return add_wishlist_item(peticion).status_code


def run_tests():
    for titulo, autor, esperado, porque in CASOS:
        check(es_vigilado(titulo, autor, VIGILADOS) is esperado,
              f"{'acepta' if esperado else 'rechaza'} '{titulo[:34]}' ({porque})")

    for titulo, persona, esperado, porque in CASOS_CREDITO:
        check(es_vigilado(titulo, persona, VIGILADOS_CREDITO, EXCLUSIONES_CREDITO) is esperado,
              f"{'acepta' if esperado else 'rechaza'} '{titulo[:38]}' ({porque})")

    # Suelo anti-vacuidad: sin vigilados la guardia no puede opinar. Que devuelva False es lo
    # correcto AQUI; es la vista quien decide no aplicarla cuando la tabla esta vacia.
    check(es_vigilado('ZZPrueba lo que sea', '', []) is False,
          'sin vigilados, es_vigilado dice False')

    # `request.data` es JSON: el campo de persona puede llegar como lista, dict o numero. La
    # regla vieja los stringificaba en un f-string; la nueva los pasa a `unicodedata.normalize`,
    # que levanta TypeError -> 500 en los tres caminos de escritura. Encontrado en la revision.
    for raro in (['Daft Punk'], {'a': 1}, 42, None):
        check(es_vigilado('ZZPrueba', raro, ['Daft Punk']) in (True, False),
              f'un campo de persona {type(raro).__name__} no revienta la guardia')
    check(es_vigilado(['ZZPrueba'], '', ['Daft Punk']) is False,
          'y un titulo que no es cadena tampoco')

    # La aguja y el pajar tienen que normalizarse IGUAL. `_creditos` parte por `/` y `&` y borra
    # la puntuacion; si el vigilado solo pasa por `_sin_acentos`, un nombre con puntuacion no
    # casa NI CONSIGO MISMO y el vigilado queda mudo para siempre sin avisar. Encontrado por
    # `/code-review` el 2026-08-31, y con el cae la exclusion `M!das` del docstring.
    for nombre in ('AC/DC', "Guns N' Roses", 'Simon & Garfunkel', 'M.I.A.', 'Earth, Wind & Fire'):
        check(es_vigilado('ZZPrueba lo que sea', nombre, [nombre]) is True,
              f'un vigilado con puntuacion casa consigo mismo: {nombre!r}')
    check(es_vigilado('ZZPrueba', 'Kavinsky & M!das', ['Kavinsky'], {'Kavinsky': ['M!das']}) is False,
          "la exclusion 'M!das' escrita como se lee SI excluye")

    # Y cada grafia excluye SU fila, no la del vecino: sin esto una sola entrada de la lista
    # sostiene las dos filas y la otra puede estar rota sin que nada lo diga.
    check(es_vigilado('Tingisha (feat. Kavinsky, Mchina & Mdas)', 'Finesse Ngara',
                      ['Kavinsky'], {'Kavinsky': ['Mdas']}) is False,
          "'Mdas' sola excluye la fila de la clausula del titulo")
    check(es_vigilado('Nairobi Nights', 'Kavinsky & M!das',
                      ['Kavinsky'], {'Kavinsky': ['M!das']}) is False,
          "'M!das' sola excluye la fila del campo de artista")
    check(es_vigilado('Nairobi Nights', 'Kavinsky & M!das',
                      ['Kavinsky'], {'Kavinsky': ['Mdas']}) is True,
          "y NO se cubren entre si: 'Mdas' no salva la fila del artista")

    rollback(_libros_end_to_end)
    rollback(_las_tres_sedes)

    print(f"\ntest_fuentes: {_checks}/{_checks}")


def _libros_end_to_end():
    # La guardia tiene que estar EN EL CAMINO DE ESCRITURA, no solo existir. Un `es_vigilado`
    # correcto que nadie llama deja el tablon exactamente como estaba.
    vivos = list(Watcher.objects.filter(is_active=True).values_list('keyword', flat=True))
    check(bool(vivos), f'hay vigilados vivos contra los que probar: {len(vivos)}')

    basura = 'ZZPrueba Incluye paginas a color y un panteon'
    # BORRAR ANTES DE POSTEAR, y no solo despues. La vista responde 200 por DOS motivos —
    # `ya_conocido` y `es_vigilado`— y el status no los distingue. Si esta fila sobrevive de una
    # corrida anterior, el 200 lo da el filtro de duplicados y esta prueba pasa SIN QUE LA
    # GUARDIA DE RELEVANCIA EXISTA.
    #
    # No es hipotetico: el 2026-08-30, una inversion de esta misma prueba fallo su assert antes
    # de limpiar, dejo la fila en el tablon VIVO, y desde entonces la inversion de libros salia
    # VERDE mientras cine y musica salian rojas. La guardia se podia borrar entera sin que nadie
    # se enterase. *Una prueba que escribe en la base viva tiene que limpiar ANTES, no despues:
    # despues no corre cuando falla.*
    WishlistItem.objects.filter(title=basura).delete()
    # `_publicar` manda `author_string` siempre, aunque sea vacio: esa es la forma del radar.
    check(_publicar(basura, '') == 200,
          'la vista RECHAZA (200, no 201) una fila DEL RADAR que no menciona a ningun vigilado')
    check(WishlistItem.objects.filter(title=basura).count() == 0,
          'y no ha escrito ninguna fila')
    WishlistItem.objects.filter(title=basura).delete()

    # El reciproco. Sin esto la prueba anterior pasaria igual con una guardia que rechaza todo.
    #
    # El titulo NO puede contener el vigilado, o la fila entraria POR TITULO y esta prueba diria
    # "casa por autor" sin haberlo probado. Paso exactamente eso en la primera version: eligio
    # 'Chainsaw Man' como autor y lo metio dentro del titulo. La linea de abajo es lo que
    # impide que vuelva a ser vacua.
    autor_vivo = next((v for v in vivos if ' ' in v), vivos[0])
    relevante = 'ZZPrueba Tomo Suelto Sin Serie Reconocible 99'
    check(es_vigilado(relevante, '', vivos) is False,
          'el titulo de la prueba no casa por si solo: lo que se prueba es el AUTOR')
    WishlistItem.objects.filter(title=relevante).delete()  # ANTES, por lo mismo de arriba
    check(_publicar(relevante, autor_vivo) == 201,
          f"la vista ACEPTA (201) un titulo que solo casa por AUTOR ('{autor_vivo}')")
    WishlistItem.objects.filter(title=relevante).delete()


# (etiqueta, poster, modelo de vigilancia, modelo de tablon, campo de la PERSONA)
#
# El campo de persona se llama distinto en cada sede y esa es la unica asimetria: `author_string`
# en libros, `director` en cine, `artist` en musica. Los tres estan poblados en produccion —
# medido el 2026-08-30: libros los rellena la estrategia, cine 13 de 13 filas y musica 10 de 10.
SEDES = (
    ("cine", lambda d: MovieWishlistViewSet.as_view({"post": "create"})(
        _FABRICA.post("/", d, format="json")), MovieWatcher, MovieWishlist, "director"),
    ("musica", lambda d: MusicWishlistViewSet.as_view({"post": "create"})(
        _FABRICA.post("/", d, format="json")), MusicWatcher, MusicWishlist, "artist"),
)


def _las_tres_sedes():
    """Cine y musica tienen el MISMO defecto que libros, y medido es peor.

    Los dos vigilados de cine son DIRECTORES ('John Carpenter', 'Denis Villeneuve') y el unico de
    musica es una BANDA ('Daft Punk'). Medido el 2026-08-30 sobre las filas vivas: 10 de 13 del
    tablon de cine y 7 de 10 del de musica NO mencionan a su vigilado en el titulo — 'Incendies',
    'Arrival', 'Dune' son todas de Villeneuve; 'Random Access Memories', 'Discovery' y 'Homework'
    son todas de Daft Punk. Un filtro por titulo aqui borraria practicamente el tablon entero.
    """
    for etiqueta, postear, W, L, campo in SEDES:
        vivos = list(W.objects.filter(is_active=True).values_list('keyword', flat=True))
        check(bool(vivos), f'{etiqueta}: hay vigilados vivos ({len(vivos)})')
        persona = vivos[0]

        basura = f'ZZPrueba Recopilatorio Ajeno {etiqueta} 99'
        check(es_vigilado(basura, '', vivos) is False,
              f'{etiqueta}: el titulo de prueba no casa por si solo')
        L.objects.filter(title=basura).delete()
        # Con el campo de persona PUESTO: es la forma del scraper, que es a quien juzga la
        # guardia. Sin el campo seria un alta a mano y se aceptaria (ver el bloque de arriba).
        check(postear({"title": basura, campo: "ZZAlguien Ajeno"}).status_code == 200,
              f'{etiqueta}: RECHAZA (200) una fila DEL RADAR que no menciona a ningun vigilado')
        check(L.objects.filter(title=basura).count() == 0,
              f'{etiqueta}: y no ha escrito ninguna fila')

        # El reciproco por el campo de PERSONA, que es la mitad que un filtro por titulo pierde.
        L.objects.filter(title=basura).delete()
        resp = postear({"title": basura, campo: persona})
        check(resp.status_code == 201,
              f"{etiqueta}: ACEPTA (201) por {campo}='{persona}' con el titulo sin casar")
        L.objects.filter(title=basura).delete()

    # EL MOVIL POSTEA SOLO {title}, sin campo de persona (movil/app.js:571). La guardia existe
    # para filtrar la manguera del scraper —que SIEMPRE etiqueta: 0 de 519 filas producidas
    # carecen de campo de persona, libros incluidos via `enriquecer`— no para juzgar lo que
    # Alonso teclea a mano. Sin esto, 'Berserk 42' escrito en el telefono se descarta con un 200
    # y la cola lo da por transmitido: el usuario ve "anotado" y no hay fila. Encontrado por
    # /code-review el 2026-08-31.
    for etiqueta, postear, W, L, campo in SEDES:
        aMano = f'ZZPrueba Tecleado A Mano {etiqueta} 77'
        L.objects.filter(title=aMano).delete()
        check(postear({"title": aMano}).status_code == 201,
              f'{etiqueta}: un alta MANUAL (solo title, sin {campo}) se ACEPTA')
        L.objects.filter(title=aMano).delete()

    # La exclusion tiene que llegar por la VISTA. Un `es_vigilado` que la respeta y una vista que
    # no se la pasa dejan el tablon exactamente igual que antes. Fuera del bucle: es de musica.
    tocadas = MusicWatcher.objects.filter(keyword='Kavinsky', is_active=True).update(
        exclusiones='M!das, Mdas, Finesse Ngara')
    check(tocadas == 1,
          'hay un vigilado Kavinsky VIVO al que ponerle la exclusion (si no, lo de abajo es vacuo)')
    homonimo = 'ZZPrueba Tingisha (feat. Kavinsky, Mchina & Mdas)'
    MusicWishlist.objects.filter(title=homonimo).delete()
    postear_musica = SEDES[1][1]
    check(postear_musica({"title": homonimo, "artist": "Finesse Ngara"}).status_code == 200,
          'musica: la VISTA rechaza (200) el homonimo excluido')
    check(MusicWishlist.objects.filter(title=homonimo).count() == 0,
          'y no ha escrito ninguna fila')
    MusicWishlist.objects.filter(title=homonimo).delete()


if __name__ == "__main__":
    run_tests()
