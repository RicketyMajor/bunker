"""Standalone check for the deduplication rule the three boards share.

Run: docker compose exec -T web python -m tests.test_dedup

Every pair below is a REAL pair measured on 2026-08-30 against the live boards, not an invented
string. The defect this rule exists to fix was found by measuring the old one: `book_radar.js`
built a Fuse.js index at threshold 0.15 and could not tell volume 15 of a series from volume 1,
so it discarded it. Leave-one-out over the 250 live rows put that at 68 false drops, 27 %.

The pairs are crossed on string distance and that is the whole point: the false pair
'Junji Ito ... #2' / '#3' scores 0.975 and the true pair 'One Punch-Man #33' / 'One Punch-Man 33'
scores 0.970. No cutoff separates them. The volume number does.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from bunker_core.dedup import clave, ya_conocido  # noqa: E402


class Fila:
    """Stands in for a model row: `ya_conocido` only ever reads `.title`."""

    def __init__(self, title):
        self.title = title


# (a, b, conocido, por que). `conocido` es lo que ya_conocido([a], b) debe responder.
PARES = (
    ("Berserk 21", "Berserk 17", False, "tomos distintos de la misma serie"),
    ("Chainsaw man 08", "Chainsaw man 01", False, "tomos distintos, cero a la izquierda"),
    ("Berserk #2", "Berserk #29", False, "2 y 29 no son el mismo tomo"),
    ("Dandadan 01", "Dandadan 12", False, "tomos distintos"),
    ("Berserk Deluxe Volume 1 (en Inglés)", "Berserk Deluxe Volume 15 (en Inglés)", False,
     "el caso que destapó el defecto: el 15 se descartaba por parecerse al 1"),
    ("Dune: Part Two", "Dune: Part Three", False, "dos películas distintas de la misma saga"),
    ("Chainsaw Man #4", "Chainsaw man 04", True, "mismo tomo, otra puntuación"),
    ("One Punch-Man #33", "One Punch-Man 33", True, "mismo tomo, sin almohadilla"),
    ("ULISES Y GYRANO", "ULISES Y CYRANO", True, "errata de tienda, 0.93"),
    ("The Thing", "The Thing", True, "idéntico"),
    ("Berserk Deluxe Volume 15 (en Inglés)", "Berserk Deluxe Volume #15 (en Ingles)", True,
     "el marcador cambia de forma: sin borrarlo de la base esto da 0.87 y entra dos veces"),
    ("Berserk Deluxe Volume 15 (en Inglés)", "Berserk Deluxe Vol. 15 (en Inglés)", True,
     "'Vol.' y 'Volume' son el mismo marcador"),
)


def test_la_regla_sobre_pares_reales():
    for a, b, esperado, motivo in PARES:
        obtenido = ya_conocido([Fila(a)], b)
        assert obtenido is esperado, (
            f"{b!r} contra un tablón con {a!r}: se esperaba "
            f"{'conocido' if esperado else 'NUEVO'} ({motivo}), salió "
            f"{'conocido' if obtenido else 'NUEVO'}. claves: {clave(a)} vs {clave(b)}"
        )
    print(f"OK · {len(PARES)}/{len(PARES)} pares reales resueltos como se midió")


def test_el_numero_es_compuerta_dura():
    """Bases idénticas y números distintos no pueden coincidir, por parecidas que sean."""
    assert not ya_conocido([Fila("Dandadan 1")], "Dandadan 2"), (
        "dos tomos consecutivos con la MISMA base colapsaron: el número no está actuando "
        "como compuerta, sólo como un carácter más del texto"
    )
    print("OK · el número separa aunque la base sea idéntica")


def test_un_tablon_vacio_no_conoce_nada():
    """Guardia de vacuidad, ARRIBA de los casos que dependen de que el tablón tenga filas."""
    assert not ya_conocido([], "Cualquier Cosa"), "un tablón vacío dijo conocer algo"
    print("OK · un tablón vacío no conoce nada")


def test_clave_extrae_el_numero_final():
    assert clave("Chainsaw Man #4") == clave("Chainsaw man 04"), (
        f"la clave no normaliza la puntuación: {clave('Chainsaw Man #4')} "
        f"vs {clave('Chainsaw man 04')}"
    )
    base, num = clave("TRON: Legacy - The Complete Edition")
    assert num is None, f"un título sin número suelto sacó número: {num!r}"
    print("OK · clave() normaliza puntuación y no inventa números")



from django.db import transaction  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from catalog.models import WishlistItem  # noqa: E402
from catalog.views import add_wishlist_item  # noqa: E402
from disquera.models import MusicWishlist  # noqa: E402
from disquera.views import MusicWishlistViewSet  # noqa: E402
from movies.models import MovieWishlist  # noqa: E402
from movies.views import MovieWishlistViewSet  # noqa: E402

FABRICA = APIRequestFactory()


def _postear_libro(datos):
    return add_wishlist_item(FABRICA.post("/", datos, format="json"))


def _postear_peli(datos):
    return MovieWishlistViewSet.as_view({"post": "create"})(
        FABRICA.post("/", datos, format="json"))


def _postear_disco(datos):
    return MusicWishlistViewSet.as_view({"post": "create"})(
        FABRICA.post("/", datos, format="json"))


# (etiqueta, poster, modelo, dos titulos ya en el tablon, la entrega NUEVA, la MISMA otra vez)
#
# LOS TITULOS LLEVAN PREFIJO A PROPOSITO, y no es cosmetica. Estas pruebas conducen la vista
# real, que consulta `.objects.all()` — la tabla VIVA, no un fixture. La primera version usaba
# los pares medidos ('Dune: Part Two', 'Alive 2007', 'Berserk Deluxe Volume 1') y salio roja al
# instante: 'Dune: Part Three' YA es una fila del tablon de cine, asi que la novedad respondia
# 200 con el predicado viejo y la prueba acusaba a un defecto que no estaba ahi. Peor: el
# veredicto habria dependido de lo que el radar encontrase esa noche. Los pares reales viven
# arriba, en PARES, que no toca la base. Verificado el 2026-08-30: ninguno de estos seis
# titulos es `ya_conocido` en ninguna de las tres tablas vivas.
#
# El repetido de libros NO es 'ZZPrueba Deluxe Volume 15' a secas: esa base pierde '(en ingles)'
# y da 0.74, por debajo del corte. El que vale es el que cambia la FORMA del marcador, que es el
# caso real de dos tiendas escribiendo el mismo tomo.
#
# Y LOS TRES REPETIDOS DIFIEREN POR PUNTUACION, NUNCA SOLO POR MAYUSCULAS. Medido el
# 2026-08-30: con 'zzprueba: part three' revertir cine o musica salia VERDE, porque el
# `title__iexact` viejo ya cazaba el cambio de caja. Dos de las tres sedes quedaban sin probar
# tras una inversion que parecia correcta. Un check verde en las dos direcciones no es un check.
#
# Cine es el caso mas ajustado de los tres: sin numero que actue de compuerta, se separa solo
# por parecido de base (0.83 contra un corte de 0.90). Es tambien el unico que representa una
# saga numerada con palabras, que es como se nombran las peliculas.
SEDES = (
    ("libros", _postear_libro, WishlistItem,
     ["ZZPrueba Deluxe Volume 1 (en Inglés)", "ZZPrueba Deluxe Volume 9 (en Inglés)"],
     "ZZPrueba Deluxe Volume 15 (en Inglés)", "ZZPrueba Deluxe Volume #15 (en Ingles)"),
    ("cine", _postear_peli, MovieWishlist,
     ["ZZPrueba: Part One", "ZZPrueba: Part Two"],
     "ZZPrueba: Part Three", "ZZPrueba - Part Three"),
    ("musica", _postear_disco, MusicWishlist,
     ["ZZPrueba 1997", "ZZPrueba 2007"],
     "ZZPrueba 2020", "ZZPrueba #2020"),
)


def rollback(fn):
    try:
        with transaction.atomic():
            fn()
            raise transaction.TransactionManagementError("rollback")
    except transaction.TransactionManagementError:
        pass


def test_una_novedad_entra_en_las_tres_sedes():
    def cuerpo():
        for etiqueta, postear, modelo, previos, nuevo, _ in SEDES:
            for titulo in previos:
                modelo.objects.create(title=titulo)
            antes = modelo.objects.count()
            resp = postear({"title": nuevo})
            assert resp.status_code == 201, (
                f"{etiqueta}: {nuevo!r} contra un tablón con {previos} dio "
                f"{resp.status_code}, se esperaba 201. Es el defecto original: una novedad "
                f"descartada por parecerse a sus hermanas de serie"
            )
            assert modelo.objects.count() == antes + 1, f"{etiqueta}: respondió 201 sin guardar"
    rollback(cuerpo)
    print("OK · una entrega nueva de una serie vigilada entra en las tres sedes (201)")


def test_el_mismo_item_no_entra_dos_veces():
    def cuerpo():
        for etiqueta, postear, modelo, _, nuevo, repetido in SEDES:
            postear({"title": nuevo})
            despues_de_la_primera = modelo.objects.count()
            resp = postear({"title": repetido})
            assert resp.status_code == 200, (
                f"{etiqueta}: {repetido!r} repetido dio {resp.status_code}, se esperaba 200"
            )
            assert modelo.objects.count() == despues_de_la_primera, (
                f"{etiqueta}: guardó el duplicado igual"
            )
    rollback(cuerpo)
    print("OK · el mismo item escrito de otra forma responde 200 sin guardar")


def test_la_lista_negra_sigue_contando():
    """El filtro lee la tabla entera, no el tablón visible: un item rechazado no vuelve."""
    def cuerpo():
        for etiqueta, postear, modelo, _, nuevo, repetido in SEDES:
            # Se planta el REPETIDO y se postea el NUEVO: plantar el mismo texto dejaba la
            # prueba verde tambien con el predicado viejo, y no probaba nada.
            modelo.objects.create(title=repetido, is_rejected=True)
            antes = modelo.objects.count()
            resp = postear({"title": nuevo})
            assert resp.status_code == 200, (
                f"{etiqueta}: un item en lista negra dio {resp.status_code}; volvería al tablón"
            )
            assert modelo.objects.count() == antes, f"{etiqueta}: resucitó un item rechazado"
    rollback(cuerpo)
    print("OK · la lista negra sigue contando como 'ya conocido' en las tres sedes")


if __name__ == "__main__":
    PRUEBAS = [
        test_un_tablon_vacio_no_conoce_nada,
        test_clave_extrae_el_numero_final,
        test_el_numero_es_compuerta_dura,
        test_la_regla_sobre_pares_reales,
        test_una_novedad_entra_en_las_tres_sedes,
        test_el_mismo_item_no_entra_dos_veces,
        test_la_lista_negra_sigue_contando,
    ]
    for prueba in PRUEBAS:
        prueba()
    print(f"\ntest_dedup: {len(PRUEBAS)}/{len(PRUEBAS)}")
