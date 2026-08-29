#!/bin/bash
# bunker/scripts/respaldo_pilas.sh
# Nightly dump of the THREE stacks this machine runs, driven by a systemd user timer.
#
# Why here, and why one script for three repositories: until 2026-08-27 the Bunker was the only
# stack, and its backup was a cron INSIDE its web image (`bunker_crontab` + `backup.sh`). The
# split left `~/dev/posada` and `~/dev/ajedrez` with 531 + 15 rows and no recurring copy at all.
# Three copies of the same in-image cron is the expensive answer to that; one host-side timer is
# one place to change and one place to check.
#
# 2026-08-29: THIS IS NOW THE ONLY MECHANISM. The in-image cron was deleted, because it never
# caught up — it fired only on nights the laptop happened to be awake at 00:00 and went seven
# nights in a row producing nothing. `Persistent=true` below is precisely that difference.
#
# It lives in the Bunker's repo because the Bunker is the only one of the three with a
# `scripts/`, and a clone brings it. The absolute paths below are host-specific ON PURPOSE:
# this is a timer for this laptop, not a deployment artifact.

set -uo pipefail

# `docker` is in /usr/bin, which IS on the short default PATH — but with lingering enabled the
# user manager starts at boot with no graphical session, and pinning it is what `ronda-doze`
# had to learn the hard way when its sqlite3 vanished. One line, no surprises.
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

DESTINO="/home/alonso/dev/respaldos"
MAX=7

# nombre : directorio del proyecto : apps con modelos
#
# The app lists were MEASURED, not read off a settings file: `apps.get_models()` in each live
# stack, minus Django's own four. `posada_core` and `chess_core` have no models at all, so they
# are correctly absent. Re-measure before editing this line:
#   docker compose exec -T web python manage.py shell -c \
#     "from django.apps import apps; print(sorted({m._meta.app_label for m in apps.get_models()}))"
PILAS=(
  "bunker:/home/alonso/dev/bunker:catalog movies disquera bunker_core"
  "posada:/home/alonso/dev/posada:posada"
  "ajedrez:/home/alonso/dev/ajedrez:chess_study"
)

fallos=()
echo "===== RESPALDO $(date '+%Y-%m-%d %H:%M:%S') ====="

for entrada in "${PILAS[@]}"; do
    nombre="${entrada%%:*}"
    resto="${entrada#*:}"
    proyecto="${resto%%:*}"
    apps="${resto#*:}"

    dir="$DESTINO/$nombre"
    mkdir -p "$dir"
    fichero="$dir/${nombre}_$(date +%Y%m%d_%H%M%S).json"

    # `--project-directory` explicito, NUNCA un `cd`. Un `cd` persiste dentro de la misma
    # invocacion y ya hizo que dos pilas distintas se compararan contra si mismas una vez.
    if ! docker compose --project-directory "$proyecto" exec -T web \
            python manage.py dumpdata $apps --format=json --indent=2 > "$fichero.tmp" 2>/dev/null
    then
        echo "  FALLO  $nombre: dumpdata no completo (¿pila levantada?)"
        rm -f "$fichero.tmp"
        fallos+=("$nombre")
        continue
    fi

    # Un volcado que nadie conto no es un respaldo. Se exige JSON valido Y al menos un objeto:
    # `dumpdata` sobre una app vacia devuelve `[]` con codigo 0, que es exito sintactico y una
    # perdida silenciosa. Esta es la comprobacion que separa "el fichero existe" de "el fichero
    # sirve", y la razon por la que el temporal no llega al directorio hasta pasarla.
    n=$(python3 -c "
import json,sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print(-1); raise SystemExit
print(len(d) if isinstance(d, list) else -1)" "$fichero.tmp" 2>/dev/null)

    if [ "${n:--1}" -lt 1 ]; then
        echo "  FALLO  $nombre: el volcado no es una lista JSON con objetos (n=$n)"
        rm -f "$fichero.tmp"
        fallos+=("$nombre")
        continue
    fi

    mv "$fichero.tmp" "$fichero"
    echo "  ok     $nombre: $n objetos -> $(basename "$fichero")"

    # Rotacion: los $MAX mas recientes. `ls -t` sobre un directorio que solo contiene estos
    # volcados; el temporal ya no esta aqui cuando esto corre.
    ls -t "$dir"/*.json 2>/dev/null | tail -n +$((MAX + 1)) | xargs -r rm --
done

if [ ${#fallos[@]} -gt 0 ]; then
    echo "RESPALDO INCOMPLETO: ${fallos[*]}"
    exit 1
fi
echo "Las tres pilas respaldadas."
