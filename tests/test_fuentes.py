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
    ('ZZPrueba Berserk 42', '', True, 'la serie esta en el titulo'),
    ('ZZPrueba One Punch-Man 24', 'Yusuke Murata', True,
     'EL CASO QUE IMPORTA: la serie NO se vigila, su autor SI'),
    ('ZZPrueba Este es el mar', 'Mariana Enríquez', True,
     'el autor llega acentuado y el vigilado no'),
    ('ZZPrueba Incluye paginas a color', '', False, 'reclamo de tienda'),
    ('ZZPrueba ARZAK El pequeno panteon', 'Moebius', False, 'autor real, no vigilado'),
    ('ZZPrueba One Punch-Man 24', '', False,
     'sin autor no hay nada que casar: por eso la estrategia debe etiquetar'),
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

    # Suelo anti-vacuidad: sin vigilados la guardia no puede opinar. Que devuelva False es lo
    # correcto AQUI; es la vista quien decide no aplicarla cuando la tabla esta vacia.
    check(es_vigilado('ZZPrueba lo que sea', '', []) is False,
          'sin vigilados, es_vigilado dice False')

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
    check(_publicar(basura, '') == 200,
          'la vista RECHAZA (200, no 201) un titulo que no menciona a ningun vigilado')
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
        check(postear({"title": basura}).status_code == 200,
              f'{etiqueta}: RECHAZA (200) lo que no menciona a ningun vigilado')
        check(L.objects.filter(title=basura).count() == 0,
              f'{etiqueta}: y no ha escrito ninguna fila')

        # El reciproco por el campo de PERSONA, que es la mitad que un filtro por titulo pierde.
        L.objects.filter(title=basura).delete()
        resp = postear({"title": basura, campo: persona})
        check(resp.status_code == 201,
              f"{etiqueta}: ACEPTA (201) por {campo}='{persona}' con el titulo sin casar")
        L.objects.filter(title=basura).delete()


if __name__ == "__main__":
    run_tests()
