"""One deduplication rule for the three boards — books, films and music.

There were three before this file, and none of them could see a volume number:

    books/views.py      title EXACT + buy_url EXACT, case-sensitive
    book_radar.js:71    Fuse.js at threshold 0.15, in Node, over the whole board
    movies/music        title__iexact

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


# Un campo de persona lista VARIOS creditos: 'Kavinsky, Angele & Phoenix',
# 'Daft Punk / Sheila & B. Devotion'. Comparar el vigilado contra cada credito ENTERO es lo que
# separa 'Kavinsky' de 'Justice League (2)'. Medido el 2026-08-31 sobre 519 filas producidas por
# un barrido real de los tres radares: la subcadena metia 45 filas y 43 eran basura.
#
# ` x ` y `with` NO son separadores, a proposito: sobre los 162 campos de persona distintos de
# los dos corpus no cambian UN SOLO troceado, y `\bx\b` puede partir un nombre real por la mitad.
_SEPARADOR = re.compile(r'\s*(?:[,&/+;]|\bfeat\.?\b|\bft\.?\b|\bfeaturing\b|\bvs\.?\b)\s*')

# La UNICA via por la que el titulo cuenta. Un vigilado suelto en el titulo metia 33 filas de
# basura de golpe ('Justice - Single' de Sevana, 'Divine Justice' de Oscar Sanchez) y las dos
# unicas filas legitimas que la via del titulo ha producido jamas lo llevaban dentro de una
# clausula: 'Starboy (feat. Daft Punk)' y 'Take Me Out (Daft Punk Remix)'.
# ponytail: un solo nivel de parentesis. 'Song (feat. Justice (3))' da el credito 'justice 3'
# y el vigilado 'Justice' se pierde. Medido: 0 titulos anidados en las 519 filas de un barrido
# real, y los sufijos de Discogs ('(2)', '(3)') aparecen en el campo de ARTISTA, no dentro de
# una clausula. El dia que aparezcan, la salida es un contador de profundidad, no otra regex.
_CLAUSULA = re.compile(r'[(\[]([^)\]]*)[)\]]')
_ABRE_CREDITO = re.compile(r'^\s*(?:feat\.?|ft\.?|featuring)\b', re.IGNORECASE)
_CIERRA_CREDITO = re.compile(r'\b(?:remix|edit|rework|mashup|mix)\s*$', re.IGNORECASE)
# Una version ajena NO es una colaboracion: 'Digital Love (Daft Punk Cover)' lo toca otro grupo.
_NO_ES_CREDITO = re.compile(r'\b(?:cover|tribute|karaoke)\b', re.IGNORECASE)


def _creditos(texto):
    """Los creditos enteros de un campo de persona, normalizados y sin puntuacion.

    `str(texto)` y no `texto` a secas: el campo llega de `request.data`, que es JSON, y un
    `"artist": ["a"]` traia un TypeError desde `unicodedata.normalize` -> 500 en los tres
    caminos de escritura. La regla vieja lo stringificaba en un f-string y devolvia 200.
    """
    for trozo in _SEPARADOR.split(_sin_acentos('' if not texto else str(texto))):
        limpio = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', trozo)).strip()
        if limpio:
            yield limpio


def _creditos_del_titulo(titulo):
    """Los creditos que un titulo declara: '(feat. X)' o '(X Remix)'. Nada mas.

    Se lee sobre el titulo CRUDO, no normalizado: los parentesis y los corchetes son la
    delimitacion, y `_sin_acentos` no los toca pero `_creditos` si los borraria.
    """
    for cuerpo in _CLAUSULA.findall('' if not titulo else str(titulo)):
        if _NO_ES_CREDITO.search(cuerpo):
            continue
        if _ABRE_CREDITO.search(cuerpo):
            cuerpo = _ABRE_CREDITO.sub('', cuerpo)
        elif _CIERRA_CREDITO.search(cuerpo):
            cuerpo = _CIERRA_CREDITO.sub('', cuerpo)
        else:
            continue
        for credito in _creditos(cuerpo):
            yield credito


def _casa(palabra, presentes):
    """¿Esta el vigilado entre los creditos presentes, normalizado IGUAL que ellos?

    La aguja pasa por `_creditos` como el pajar, y no solo por `_sin_acentos`. Sin esto las dos
    partes se normalizan distinto y un vigilado con puntuacion no casa NI CONSIGO MISMO:
    'AC/DC' se parte en {'ac', 'dc'} del lado del credito y se queda en 'ac/dc' del lado del
    vigilado, asi que el vigilado queda mudo para siempre y nada lo dice. Lo mismo mataba la
    exclusion 'M!das', que del lado del credito es 'm das'.

    Un vigilado de varios creditos ('Simon & Garfunkel') casa cuando estan TODOS.
    """
    propios = set(_creditos(palabra))
    return bool(propios) and propios <= presentes



def es_vigilado(titulo, autor, palabras, exclusiones=None):
    """¿Menciona este item a alguno de los vigilados, por titulo O por autor?

    Por autor, y no solo por titulo, porque CINCO de los diez vigilados son nombres de persona
    ('Yusuke Murata', 'Inio Asano') y un nombre de autor no aparece dentro del titulo de su libro.
    Medido el 2026-08-30 sobre las 252 filas vivas: un filtro solo por titulo descarta 42 filas de
    8 series vigiladas, incluidas las 14 de One Punch-Man y las 9 de Punpun — que son exactamente
    los descubrimientos que el arreglo de la deduplicacion existia para dejar entrar.

    El autor puede llegar acentuado de la fuente ('Mariana Enríquez') y el vigilado escribirse sin
    acento, asi que las dos partes pasan por _sin_acentos.

    Y por CREDITO y no por subcadena desde el 2026-08-31, que es la mitad que faltaba medir. Sobre
    519 filas producidas por un barrido real: la via del titulo metia 42 filas y solo UNA era
    legitima, y la subcadena del campo de persona metia otras 3, las 3 basura. Las series de
    libros no la necesitan — sus filas llegan con la serie en el campo de autor
    ('Chainsaw Man #4' :: autor 'Chainsaw Man'), asi que casan por credito igual.

    ⚠ Y ese autor NO siempre lo pone la fuente: `scraper/book_radar.config.js:enriquecer` rellena
    el campo vacio con el primer vigilado que sea SUBCADENA del titulo, o con 'Desconocido'
    (63 de 223 filas de un barrido real). Asi que para LIBROS la regla de subcadena sobre el
    titulo sigue viva una capa mas arriba, en el scraper, y esta guardia no la ve. Que eso sea
    correcto depende del vigilado: para una serie ('Berserk 21' -> autor 'Berserk') es exacto,
    para una persona puede etiquetar un libro SOBRE alguien como si fuera SUYO. Medirlo exige
    capturar la salida de la estrategia ANTES de `enriquecer`; no esta hecho.

    ponytail: un homonimo con el mismo formato de credito entra igual — 'Kavinsky & M!das' (un
    artista keniano) es indistinguible de 'Kavinsky & Donald Durand' para cualquier regla de
    cadenas, y 'Liberty & Justice' de 'Daft Punk / Sheila'. Lo resuelve `exclusiones`, a mano y
    solo cuando alguien nota el homonimo. Si algun dia hay que automatizarlo, la salida es
    comparar el identificador de la fuente (`discogs_id` ya viaja en el payload de musica), no
    afinar mas la cadena.
    """
    presentes = set(_creditos(autor)) | set(_creditos_del_titulo(titulo))
    exclusiones = exclusiones or {}
    for palabra in palabras:
        if not _casa(palabra, presentes):
            continue
        if any(_casa(x, presentes) for x in exclusiones.get(palabra, ())):
            continue
        return True
    return False


def desglosar(pares):
    """[('Kavinsky', 'M!das, Mdas')] -> (['Kavinsky'], {'Kavinsky': ['M!das', 'Mdas']}).

    Los tres tableros guardan las exclusiones como texto separado por comas en su propia tabla de
    vigilancia, y las tres vistas necesitan exactamente esta forma para `es_vigilado`.
    """
    vigilados, exclusiones = [], {}
    for palabra, crudas in pares:
        vigilados.append(palabra)
        lista = [e.strip() for e in (crudas or '').split(',') if e.strip()]
        if lista:
            exclusiones[palabra] = lista
    return vigilados, exclusiones


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
