"""Check that the backup covers every app that owns data. Runs inside the container:

    docker compose exec -T web python -m tests.test_backup_apps

There are TWO lists of apps to dump and they are written by hand in two files:
`BACKUP_APPS` in `bunker_core/views.py` (the API and the TUI's manual backup) and the
`bunker` row of `scripts/respaldo_pilas.sh` (the host's nightly timer). Nothing connects
them to the app
registry, so a new app with models joins neither and the failure is silent: `dumpdata`
succeeds, the file is written, and the rows are simply not in it.

That already happened. `bunker_core` was in `INSTALLED_APPS` from the Transmisor work and got
its first model on 2026-08-19; until it was noticed the same day, a restore returned a Bunker
with no `last_entry_at` and a briefing that announced every achievement as new.

This check reads nothing but the registry and the two files, so it needs no fixtures and
cannot be satisfied by an empty database.
"""
import os
import re

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.apps import apps  # noqa: E402
from django.conf import settings  # noqa: E402

from bunker_core.views import BACKUP_APPS  # noqa: E402

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def _apps_del_proyecto():
    """Apps written in this repository that own at least one model.

    Located by path, not by a hardcoded list — a hardcoded list here would be the very bug
    this check exists to catch, one file further down.
    """
    raiz = str(settings.BASE_DIR)
    return sorted(c.label for c in apps.get_app_configs()
                  if str(c.path).startswith(raiz) and any(c.get_models()))


def run_tests():
    propias = _apps_del_proyecto()
    # Suelo anti-vacuidad, NO un inventario: si el registro devolviera una lista vacía el bucle
    # de abajo no comprobaría nada y este fichero saldría verde sin mirar. Era `>= 5` con seis
    # apps; son cuatro desde que posada y chess_study salieron el 2026-08-27. El número se baja
    # a mano al partir una app, y esa es justamente la señal de que hay que revisar las dos
    # listas de BACKUP_APPS.
    check(len(propias) >= 4, f"el registro ve las apps del proyecto: {propias}")

    for label in propias:
        check(label in BACKUP_APPS,
              f"'{label}' tiene modelos y está en BACKUP_APPS (bunker_core/views.py)")

    # El respaldo nocturno del host lleva su propia lista escrita a mano en el shell.
    # Apuntaba a `scripts/backup.sh` hasta el 2026-08-29, cuando el cron de la imagen se borró
    # por no dispararse jamás las noches con el portátil apagado. La deriva entre DOS listas a
    # mano sigue existiendo — sólo cambió cuál es la segunda.
    guion = os.path.join(str(settings.BASE_DIR), 'scripts', 'respaldo_pilas.sh')
    with open(guion, encoding='utf-8') as f:
        linea = next((l for l in f if l.lstrip().startswith('"bunker:')), '')
    check(linea, "scripts/respaldo_pilas.sh todavía tiene la fila de la pila `bunker`")
    # La fila es "nombre:ruta:app app app". Las apps son el ÚLTIMO campo, y partir por ':' es
    # lo único que las separa de la ruta — un `findall` sobre la línea entera recogería
    # `home`, `alonso` y `dev` y daría verde por accidente.
    nombradas = set(re.findall(r'[a-z_]+', linea.strip().strip('"').split(':')[-1]))
    # El suelo es 2, NO las 4 de hoy. Con 4 este guardia se disparaba primero al quitar una
    # app de la fila y daba un rojo con el mensaje equivocado ("no son apps de verdad") en vez
    # de dejar que el bucle de abajo nombrara la app que falta. Lo que defiende es que el split
    # por ':' casó ALGO, no cuántas apps hay.
    check(len(nombradas) >= 2,
          f"la fila de `bunker` nombra apps de verdad, no trozos de ruta: {sorted(nombradas)}")
    for label in propias:
        check(label in nombradas,
              f"'{label}' también está en el dumpdata de scripts/respaldo_pilas.sh")

    # Y al revés: una app borrada del proyecto que siga en la lista rompe el dumpdata entero
    # con LookupError, y el timer lo registra como un FALLO de la pila entera.
    for label in BACKUP_APPS:
        check(label in propias,
              f"BACKUP_APPS no nombra apps que ya no existen: '{label}'")

    print(f"\ntest_backup_apps: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
