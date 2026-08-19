"""Check that the backup covers every app that owns data. Runs inside the container:

    docker compose exec -T web python -m tests.test_backup_apps

There are TWO lists of apps to dump and they are written by hand in two files:
`BACKUP_APPS` in `bunker_core/views.py` (the API and the TUI's manual backup) and the
`dumpdata` line in `scripts/backup.sh` (the nightly cron). Nothing connects them to the app
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
    check(len(propias) >= 5, f"el registro ve las apps del proyecto: {propias}")

    for label in propias:
        check(label in BACKUP_APPS,
              f"'{label}' tiene modelos y está en BACKUP_APPS (bunker_core/views.py)")

    # El cron nocturno lleva su propia lista escrita a mano en el shell.
    guion = os.path.join(str(settings.BASE_DIR), 'scripts', 'backup.sh')
    with open(guion, encoding='utf-8') as f:
        linea = next((l for l in f if 'dumpdata' in l), '')
    check(linea, f"scripts/backup.sh todavía tiene una línea dumpdata")
    nombradas = set(re.findall(r'[a-z_]+', linea.split('dumpdata', 1)[1]))
    for label in propias:
        check(label in nombradas,
              f"'{label}' también está en el dumpdata de scripts/backup.sh")

    # Y al revés: una app borrada del proyecto que siga en la lista rompe el dumpdata entero
    # con LookupError, y el cron se lo come.
    for label in BACKUP_APPS:
        check(label in propias,
              f"BACKUP_APPS no nombra apps que ya no existen: '{label}'")

    print(f"\ntest_backup_apps: {_checks}/{_checks}")


if __name__ == "__main__":
    run_tests()
