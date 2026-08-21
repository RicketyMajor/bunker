#!/usr/bin/env bash
# Nightly round: does the exact alarm fire the flush while the phone is in Doze?
#
# The one caveat left over from 2026-08-15. That round proved the alarm starts the process on
# schedule in standby bucket RARE, but the phone was awake and on the charger at the time — and a
# charging device NEVER enters Doze, so the case this script exists for was structurally
# unobservable over USB. Hence adb over the network — tailnet or LAN, see DIRECCIONES — and an
# unplugged phone.
#
# Reads only. It seeds a throwaway ISBN into the queue and deletes nothing; the row it creates in
# ScanInbox is removed at the end, after asserting it is the right one.
#
# Scheduled by ~/.config/systemd/user/ronda-doze.{service,timer} — outside the repository, so a
# clone does not bring it. `systemctl --user list-timers ronda-doze\*` is how you check it is
# still there. The first attempt at this was a TRANSIENT unit and it evaporated on the next
# reboot with nobody noticing (2026-08-16).
set -uo pipefail

ADB="$HOME/Android/sdk/platform-tools/adb"
# Two addresses, tried in order, and the order is the hypothesis: the tailnet rides mobile data
# and the LAN does not, so if MIUI sleeps Wi-Fi at night the tailnet is the one that survives.
#
# It is NOT that the LAN is dead. Handoff 018 recorded it as unreachable and that was a daytime
# artefact: measured 2026-08-18 at 21:57 both answered `shell true`, the LAN in 9 ms. Swapping one
# address for the other would have fixed nothing. What three aborted rounds never established is
# which link is up at 03:00 — so the round now tries both and the log names the winner, which is
# the evidence that was missing.
DIRECCIONES=("100.81.4.38:5555" "192.168.0.4:5555")
TELEFONO=""
APP="cl.alonso.bunker"
BASE="/home/alonso/dev/bunker"
SALIDA="$BASE/scraper_logs/ronda_doze_$(date +%Y%m%d_%H%M).txt"
ESPERA=1500  # 25 min: the alarm is 15, plus room for Doze's own batching

exec > >(tee -a "$SALIDA") 2>&1
echo "===== RONDA DOZE $(date '+%F %T') ====="

a() { timeout 30 "$ADB" -s "$TELEFONO" "$@"; }
# Without a timeout, for the log capture only: the wrapper above would kill logcat after 30 s and
# take `Start proc` with it — the one line in this whole script that proves anything.
alarga() { "$ADB" -s "$TELEFONO" "$@"; }

# --- Preconditions. Each one is a reason to abort rather than produce a result nobody can read.

# La ventana primero, porque es gratis y porque es la que fallaba en silencio. Un timer que pierde
# las 03:00 por suspension dispara en cuanto la maquina despierta: el 2026-08-16 corrio a las
# 14:37 y dejo un log que parece evidencia y no lo es. Doze necesita el telefono quieto,
# desenchufado y sin tocar, y eso es de madrugada. `Persistent=false` no basta — systemd reevalua
# el OnCalendar al reanudar aunque no sea persistente, asi que el cerrojo tiene que estar aqui.
HORA=$(date +%-H)  # %-H y no %H: "09" no es un entero valido para `test -gt`, es octal invalido
if [ "${RONDA_FORZAR:-0}" != "1" ] && [ "$HORA" -gt 5 ]; then
  echo "ABORTA: son las $(date '+%H:%M') y la ronda solo mide algo entre las 00:00 y las 05:59."
  echo "        Para una ronda a mano, con el telefono ya desenchufado: RONDA_FORZAR=1 $0"
  exit 1
fi

for d in "${DIRECCIONES[@]}"; do
  timeout 20 "$ADB" connect "$d" >/dev/null 2>&1
  # `shell true` and not the exit code of `connect`: adb reports "connected" for a socket that
  # opens and then goes nowhere, which is exactly what a half-asleep phone offers.
  if timeout 30 "$ADB" -s "$d" shell true >/dev/null 2>&1; then TELEFONO="$d"; break; fi
done
if [ -z "$TELEFONO" ]; then
  echo "ABORTA: el telefono no responde en ninguna direccion (${DIRECCIONES[*]})."
  echo "        Sin adb no hay evidencia de por que arranco."
  exit 1
fi
echo "enlace: $TELEFONO"

ENCHUFADO=$(a shell dumpsys battery | grep -cE "^  (AC|USB|Wireless) powered: true")
PANTALLA=$(a shell dumpsys power | grep -oE "mWakefulness=[A-Za-z]+" | head -1)
echo "enchufado=$ENCHUFADO  $PANTALLA"
if [ "$ENCHUFADO" != "0" ]; then
  echo "ABORTA: el telefono esta cargando. Doze no engancha nunca mientras carga — este es"
  echo "        exactamente el sesgo que la ronda del 2026-08-15 no pudo evitar por USB."
  exit 1
fi

curl -s -o /dev/null --max-time 10 localhost:8009/api/movil/assets/ || {
  echo "ABORTA: Django no responde en localhost:8009"; exit 1; }

# El job se descubre AQUI y no donde se usa. Estaba despues de sembrar, asi que un aborto por
# "no encontre el job" — que es el normal cuando el proceso lleva rato muerto — dejaba la cola del
# telefono con un ISBN de prueba que se vaciaria solo en el siguiente flush, metiendo una fila
# falsa en el catalogo real. Medido el 2026-08-16. El id cambia entre dias, no entre segundos, asi
# que descubrirlo unos segundos antes de usarlo es seguro; sembrar antes de saberlo no lo era.
JOB=$(a shell dumpsys jobscheduler | grep -oE "JOB #u0a[0-9]+/[0-9]+: [a-f0-9]+ $APP" \
      | head -1 | grep -oE "/[0-9]+" | tr -d /)
if [ -z "${JOB:-}" ]; then
  echo "ABORTA: no encontre el job de $APP. Nada lo ha encolado desde el ultimo arranque"
  echo "        y sin job no hay forma headless de armar la alarma. Abre la app una vez."
  exit 1
fi

# --- Seed. A verb with a route, and an ISBN that cannot already exist.
ISBN="9793$(date +%d%H%M%S)"
TMP=$(mktemp -d)
python3 - "$TMP/cola.db" "$ISBN" <<'PY'
import sqlite3, sys, time, uuid
db = sqlite3.connect(sys.argv[1])
db.execute("PRAGMA user_version = 1")
db.execute("CREATE TABLE android_metadata (locale TEXT)")
db.execute("INSERT INTO android_metadata VALUES ('en_US')")
db.execute("""CREATE TABLE despachos (id TEXT PRIMARY KEY, verbo TEXT NOT NULL,
              payload TEXT NOT NULL, creado INTEGER NOT NULL, error TEXT)""")
db.execute("INSERT INTO despachos VALUES (?,?,?,?,NULL)",
           (str(uuid.uuid4()), "escaneo_libro", '{"isbn":"%s"}' % sys.argv[2], int(time.time()*1000)))
db.commit(); db.close()
PY

echo "--- sembrando ISBN $ISBN ---"
# El trap y no un `start` por cada rama: entre este stop y el arranque de T0 hay cuatro salidas
# posibles, y una sola que se olvide deja Django caido toda la noche sin nadie mirando.
trap 'docker compose -f "$BASE/docker-compose.yml" start web >/dev/null 2>&1' EXIT
docker compose -f "$BASE/docker-compose.yml" stop web >/dev/null 2>&1  # el flush DEBE fallar
a shell am kill "$APP"; sleep 2
a push "$TMP/cola.db" /sdcard/Download/cola.db >/dev/null
a shell "run-as $APP sh -c 'rm -f databases/cola.db-journal'"
a shell "cat /sdcard/Download/cola.db | run-as $APP sh -c 'cat > databases/cola.db'"

# --- Arm the alarm WITHOUT opening the app. Until Task 10 gives `Puente.encolar` a caller, the
#     only thing that runs `doWork` — and therefore `Despertador.sincronizar` — is the scheduler.
#     `$JOB` was discovered in the preconditions; see the note there for why.
a shell cmd jobscheduler run -f "$APP" "$JOB" >/dev/null 2>&1
sleep 12

PEND=$(a exec-out "run-as $APP cat databases/cola.db" > "$TMP/q.db" 2>/dev/null; \
       sqlite3 "$TMP/q.db" "SELECT count(*) FROM despachos;" 2>/dev/null)
# DespertadorReceiver specifically, not the package: WorkManager keeps its own alarms under this
# same package, so counting the package would report "armed" with our alarm absent. Measured
# 2026-08-15: two pending alarms for the package with none of them ours.
#
# Y acotado a la lista. Esta es la TERCERA version de este corte y las dos anteriores contaban
# alarmas que no existen:
#   1. hasta EOF          -> cuenta `Alarm Stats:`, que nombra al receptor una vez por disparo
#                            historico. Cazada a mano el 2026-08-15.
#   2. hasta Top Alarms/Alarm Stats -> entre la lista y esas dos hay NUEVE secciones mas, y una es
#                            `Removal history:`, que guarda `Reason=alarm_cancelled` con un
#                            Snapshot que repite el tag. Medido 2026-08-17: con la cola en 0 y la
#                            alarma recien cancelada, contaba 1.
# El corte correcto no nombra la seccion siguiente — nombra que empieza UNA: la lista va indentada
# a cuatro espacios o mas, y toda seccion de nivel superior empieza con dos y una letra.
# Contraste para verificar a mano: `Pending alarms per uid:` no lista nuestro uid cuando es 0.
ARMADA=$(a shell dumpsys alarm \
         | awk '/^  [0-9]+ pending alarms:/{f=1; next} f && /^  [A-Za-z]/{exit} f' \
         | grep -c "DespertadorReceiver")
echo "tras el intento fallido: cola=$PEND  alarmas_pendientes=$ARMADA"
if [ "${PEND:-0}" != "1" ] || [ "${ARMADA:-0}" = "0" ]; then
  echo "ABORTA: la cola debia quedar en 1 y la alarma armada. Sin eso no hay nada que medir."
  exit 1  # el trap levanta `web`
fi

# --- T0. Server back, process dead, logcat clean, nobody touching anything.
a shell am kill "$APP"; sleep 2
docker compose -f "$BASE/docker-compose.yml" start web >/dev/null 2>&1; sleep 8
a logcat -c
T0=$(date '+%T')
echo "--- T0=$T0 · esperando ${ESPERA}s · doze=$(a shell dumpsys deviceidle get deep) ---"
alarga logcat -v time > "$TMP/logcat.txt" 2>&1 &
LOGPID=$!

# --- Wait, sampling Doze so the report can say whether it ever actually engaged.
LLEGADA=""
for i in $(seq 1 $((ESPERA/20))); do
  LLEGADA=$(docker compose -f "$BASE/docker-compose.yml" exec -T web python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','bunker_core.settings'); django.setup()
from catalog.models import ScanInbox
from django.utils import timezone
s = ScanInbox.objects.filter(isbn='$ISBN').first()
print(timezone.localtime(s.date_scanned).strftime('%H:%M:%S') if s else '')
" 2>/dev/null | tail -1)
  [ -n "$LLEGADA" ] && break
  [ $((i % 15)) -eq 0 ] && echo "  $(date '+%T') doze=$(a shell dumpsys deviceidle get deep 2>/dev/null)"
  sleep 20
done
kill $LOGPID 2>/dev/null

# --- Verdict. An arrival is not evidence; the reason the process started is.
echo "===== EVIDENCIA ====="
echo "llegada:        ${LLEGADA:-NO LLEGO}"
echo "doze al final:  $(a shell dumpsys deviceidle get deep 2>/dev/null)"
echo "bucket:         $(a shell am get-standby-bucket $APP 2>/dev/null)"
echo "cola:           $(a exec-out "run-as $APP cat databases/cola.db" > "$TMP/f.db" 2>/dev/null; \
                        sqlite3 "$TMP/f.db" 'SELECT count(*) FROM despachos;' 2>/dev/null)"
echo "--- por que arranco el proceso (lo unico que prueba algo) ---"
# En una variable y no `| head -3 || echo`: el estado de salida de una tuberia es el de `head`,
# que es 0 aunque `grep` no encuentre nada, asi que ese respaldo no podia dispararse nunca —
# justo en el caso en que hace falta, que es el logcat vacio.
ARRANQUE=$(grep -E "Start proc.*$APP" "$TMP/logcat.txt" 2>/dev/null | head -3)
echo "${ARRANQUE:-(sin logcat: se cayo el enlace con el telefono)}"
# Sin `|| echo "0"`: `grep -c` ya imprime 0 cuando no encuentra, y ademas sale con codigo 1, asi
# que el respaldo se sumaba y escribia el cero dos veces — en el caso normal, que es el que se lee.
echo "--- Displayed (debe ser 0) ---"
grep -c "Displayed $APP" "$TMP/logcat.txt" 2>/dev/null
echo "--- toques humanos desde T0 (debe ser 0) ---"
grep -cE "MiuiInputKeyEventLog|MTKPOWER_HINT_APP_TOUCH" "$TMP/logcat.txt" 2>/dev/null

# --- Clean up the row this script created, asserting identity first.
docker compose -f "$BASE/docker-compose.yml" exec -T web python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','bunker_core.settings'); django.setup()
from catalog.models import ScanInbox
s = ScanInbox.objects.filter(isbn='$ISBN').first()
if s: print('borrando la fila de prueba', s.id); s.delete()
" 2>/dev/null | tail -1
rm -rf "$TMP"
echo "===== FIN $(date '+%T') · informe en $SALIDA ====="
