"""One deduplication rule for the three boards — books, films and music.

There were three before this file, and none of them could see a volume number:

    catalog/views.py    title EXACT + buy_url EXACT, case-sensitive
    book_radar.js:71    Fuse.js at threshold 0.15, in Node, over the whole board
    movies/disquera     title__iexact

The Fuse one was the dangerous one. Measured on 2026-08-30 against the 250 live rows, leave-one-out:
if every title on the board arrived today as a discovery, 93 would be dropped, and 68 of those
(27 % of the board) are DIFFERENT VOLUMES of a watched series. Five of the ten watched targets are
numbered manga.

No threshold fixes that, and the numbers say why: the false pair 'Junji Ito ... #2' / '#3' scores
0.975 and the true pair 'One Punch-Man #33' / 'One Punch-Man 33' scores 0.970. They are crossed.
String distance is measuring the wrong quantity. The volume number is the signal, so here it is a
hard gate rather than one more character in the text.

CORTE calibrated against the live board, not chosen: 1.0 -> 31 pairs, 0.90 -> 36, 0.80 -> 39,
0.70 -> 46 and at 0.70 it collapses 'Dune: Part Two' with 'Dune: Part Three'. The five pairs 0.90
buys over an exact key are all real store typos ('ULISES Y GYRANO' / 'ULISES Y CYRANO').
"""
import difflib
import re
import unicodedata

CORTE = 0.90

# El ultimo entero suelto de 1-4 digitos, con su marcador si lo lleva pegado delante. El
# `(?!.*\d)` es lo que lo hace el ULTIMO: sin el, 'Berserk Deluxe Volume 9' saca el 9 igual
# pero 'One Punch-Man #15' sacaria el 1.
_NUMERO = re.compile(r'(?:#|vol\.?|volume|tomo)?\s*(\d{1,4})\b(?!.*\d)')

# Y lo que quede del marcador se borra de la base. Sin esto la regla es ASIMETRICA y se midio
# fallando: 'Volume 15' consume la palabra `volume` como marcador, pero 'Volume #15' consume
# solo el `#`, asi que `volume` sobrevive en una base y no en la otra -> 0.87, por debajo del
# corte, y el mismo tomo entra dos veces.
_MARCADOR = re.compile(r'\b(?:vol|volume|tomo)\b')


def _sin_acentos(texto):
    descompuesto = unicodedata.normalize('NFD', texto or '')
    return ''.join(c for c in descompuesto if unicodedata.category(c) != 'Mn').lower().strip()


def clave(titulo):
    """('base sin puntuacion', '4') — o (base, None) si el titulo no lleva numero suelto."""
    texto = _sin_acentos(titulo)
    encontrado = _NUMERO.search(texto)
    if encontrado:
        numero = str(int(encontrado.group(1)))
        base = texto[:encontrado.start()] + ' ' + texto[encontrado.end():]
    else:
        numero = None
        base = texto
    base = re.sub(r'[^a-z0-9 ]', ' ', base)
    base = _MARCADOR.sub(' ', base)
    return re.sub(r'\s+', ' ', base).strip(), numero


def ya_conocido(filas, titulo):
    """¿Alguna de `filas` es este mismo item? Mismo numero Y base parecida.

    `filas` es un queryset o cualquier iterable de objetos con `.title`. Se recorre entero: son
    250 filas en el tablon mas grande y esto corre en un POST que ocurre unas decenas de veces
    por barrido de 12 h.

    ponytail: barrido lineal sobre el tablon completo. El techo esta en unos pocos miles de
    filas; a partir de ahi, prefiltra los candidatos por la primera palabra de la base antes de
    puntuar, o pasa la comparacion a un indice trigram de Postgres.
    """
    base, numero = clave(titulo)
    for fila in filas:
        otra_base, otro_numero = clave(fila.title)
        if otro_numero != numero:
            continue
        if otra_base == base:
            return True
        if difflib.SequenceMatcher(None, otra_base, base).ratio() >= CORTE:
            return True
    return False
