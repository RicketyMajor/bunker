#!/usr/bin/env bash
# Nightly round: does the exact alarm fire the flush while the phone is in Doze?
#
# The one caveat left over from 2026-08-15. That round proved the alarm starts the process on
# schedule in standby bucket RARE, but the phone was awake and on the charger at the time — and a
# charging device NEVER enters Doze, so the case this script exists for was structurally
# unobservable over USB. Hence adb over Wi-Fi and an unplugged phone.
#
# Reads only. It seeds a throwaway ISBN into the queue and deletes nothing; the row it creates in
# ScanInbox is removed at the end, after asserting it is the right one.
set -uo pipefail

ADB="$HOME/Android/sdk/platform-tools/adb"
TELEFONO="192.168.0.4:5555"
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
timeout 20 "$ADB" connect "$TELEFONO" >/dev/null 2>&1
if ! a shell true >/dev/null 2>&1; then
  echo "ABORTA: el telefono no responde por Wi-Fi. Sin adb no hay evidencia de por que arranco."
  exit 1
fi

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
docker compose -f "$BASE/docker-compose.yml" stop web >/dev/null 2>&1  # el flush DEBE fallar
a shell am kill "$APP"; sleep 2
a push "$TMP/cola.db" /sdcard/Download/cola.db >/dev/null
a shell "run-as $APP sh -c 'rm -f databases/cola.db-journal'"
a shell "cat /sdcard/Download/cola.db | run-as $APP sh -c 'cat > databases/cola.db'"

# --- Arm the alarm WITHOUT opening the app. Until Task 10 gives `Puente.encolar` a caller, the
#     only thing that runs `doWork` — and therefore `Despertador.sincronizar` — is the scheduler.
JOB=$(a shell dumpsys jobscheduler | grep -oE "JOB #u0a[0-9]+/[0-9]+: [a-f0-9]+ $APP" \
      | head -1 | grep -oE "/[0-9]+" | tr -d /)
if [ -z "${JOB:-}" ]; then echo "ABORTA: no encontre el job de $APP"; exit 1; fi
a shell cmd jobscheduler run -f "$APP" "$JOB" >/dev/null 2>&1
sleep 12

PEND=$(a exec-out "run-as $APP cat databases/cola.db" > "$TMP/q.db" 2>/dev/null; \
       sqlite3 "$TMP/q.db" "SELECT count(*) FROM despachos;" 2>/dev/null)
# DespertadorReceiver specifically, not the package: WorkManager keeps its own alarms under this
# same package, so counting the package would report "armed" with our alarm absent. Measured
# 2026-08-15: two pending alarms for the package with none of them ours.
ARMADA=$(a shell dumpsys alarm | awk '/pending alarms:/,0' | grep -c "DespertadorReceiver")
echo "tras el intento fallido: cola=$PEND  alarmas_pendientes=$ARMADA"
if [ "${PEND:-0}" != "1" ] || [ "${ARMADA:-0}" = "0" ]; then
  echo "ABORTA: la cola debia quedar en 1 y la alarma armada. Sin eso no hay nada que medir."
  docker compose -f "$BASE/docker-compose.yml" start web >/dev/null 2>&1
  exit 1
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
grep -E "Start proc.*$APP" "$TMP/logcat.txt" 2>/dev/null | head -3 || echo "(sin logcat: el Wi-Fi cayo)"
echo "--- Displayed (debe ser 0) ---"
grep -c "Displayed $APP" "$TMP/logcat.txt" 2>/dev/null || echo "0"
echo "--- toques humanos desde T0 (debe ser 0) ---"
grep -cE "MiuiInputKeyEventLog|MTKPOWER_HINT_APP_TOUCH" "$TMP/logcat.txt" 2>/dev/null || echo "0"

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
