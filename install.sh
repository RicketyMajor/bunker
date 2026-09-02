#!/usr/bin/env bash
# Instalador del Bunker para Linux y macOS.
#
# Su gemelo es install.ps1, y `tests/test_instaladores.py` comprueba que los dos declaran los
# mismos `#PASO:` en el mismo orden. Si anades, quitas o reordenas un paso aqui, hazlo alli.
#
# NO USA `sudo`. El de antes hacia `sudo ln -sf` para crear un enlace que pip ya deja en
# .venv/bin/bunker: pedia la contrasena del usuario para nada.
set -euo pipefail

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
paso() { echo -e "\n${GREEN}▶ $1${NC}"; }
aviso() { echo -e "${YELLOW}  $1${NC}"; }

# La capsula se resuelve ANTES del `cd`, o una ruta relativa dada desde otro directorio deja
# de existir en cuanto cambiamos de sitio.
CAPSULA="${1:-}"
[ -n "$CAPSULA" ] && CAPSULA=$(readlink -f "$CAPSULA")

cd "$(dirname "$0")"
VENV_DIR=".venv"

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}          Instalador del Bunker                 ${NC}"
echo -e "${CYAN}================================================${NC}"

#PASO: requisitos
paso "Comprobando requisitos..."
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}  Falta python3.${NC}"; exit 1; }
# `docker compose` (V2, sin guion), igual que ensure_infrastructure_up.
docker compose version >/dev/null 2>&1 || { echo -e "${RED}  Falta docker compose (V2).${NC}"; exit 1; }
echo "  python3 y docker compose, presentes."

#PASO: entorno
paso "Creando el entorno virtual (${VENV_DIR})..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install -r requirements.txt >/dev/null
"$VENV_DIR/bin/python" -m pip install -e . >/dev/null
echo "  Dependencias instaladas. El comando queda en ${VENV_DIR}/bin/bunker."

# EL BUNDLE DEL MOVIL. `bunker_core/static/movil/dist/` esta en .gitignore, asi que un clon
# fresco NO lo trae y sin el `/movil/` y `/panel/` se sirven sin su JavaScript: el telefono ve
# un caparazon muerto. Medido el 2026-09-01 instalando en un clon limpio — el instalador salia
# con EXIT=0 y `doctor` daba 6 problemas, dos de ellos por esto.
# Se construye en un contenedor de Node y no con un `npm` del host, porque Docker ya es
# requisito y Node no: asi no se anade una dependencia mas a la maquina que instala.
# `-u` no es cosmetico: sin el, node_modules/ y dist/ quedan de root y el usuario no puede
# reconstruirlos despues sin sudo.
echo "  Construyendo el bundle del movil..."
# `-e HOME` y `-e npm_config_cache` NO son adorno: con `-u <uid>` el contenedor no encuentra
# entrada de passwd para ese uid, pone HOME=/ y npm apunta su cache a `/.npm`, que no es
# escribible. `node:20-alpine` trae un usuario `node` en el uid 1000, asi que esto SOLO funciona
# por accidente en una maquina cuyo usuario sea 1000. Medido a uid 1501: sin estas dos variables
# FALLA, con ellas OK. En macOS —que este README nombra— el primer usuario es el 501.
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -e npm_config_cache=/tmp/.npm \
    -v "$PWD":/app -w /app node:20-alpine \
    sh -c "npm ci --silent && npm run build" >/dev/null
[ -s bunker_core/static/movil/dist/main.js ] || { echo -e "${RED}  El bundle no se construyo.${NC}"; exit 1; }
echo "  Bundle construido."

#PASO: secretos
paso "Generando los secretos de ESTA instalacion..."
# La IP sale de cli/main.py:get_local_ip(), que ya resuelve el NAT de WSL2, y NO de
# `hostname -I`: en WSL2 esa devuelve la IP interna, que desde el telefono no existe.
IP=$("$VENV_DIR/bin/python" -c "from cli.main import get_local_ip; print(get_local_ip())" 2>/dev/null || echo "")
if [ -f .env ]; then
    aviso ".env ya existe: sus secretos no se tocan. Borralo si quieres unos nuevos."
    # PERO SE COMPRUEBAN. Un `.env` de antes del 2026-08-31 trae `BUNKER_API_TOKEN` VACIO, y
    # `bunker_core/auth.py` falla cerrado: sin el, TODA ruta bajo /api/ responde 503. Como
    # `/api/health/` esta en la allowlist, la espera de mas abajo recibiria su 200, las
    # migraciones correrian y este script diria "Instalacion completada" con la TUI, la PWA y
    # los tres scrapers muertos. Un instalador que deja algo roto tiene que decirlo.
    FALTAN=""
    for CLAVE in POSTGRES_PASSWORD DJANGO_SECRET_KEY BUNKER_BACKUP_TOKEN BUNKER_API_TOKEN; do
        VALOR=$(sed -n "s/^${CLAVE}=//p" .env | head -1)
        [ -n "$VALOR" ] || FALTAN="$FALTAN $CLAVE"
    done
    if [ -n "$FALTAN" ]; then
        echo -e "${RED}  Tu .env tiene estas claves VACIAS:${NC}$FALTAN"
        echo -e "${RED}  Sin BUNKER_API_TOKEN toda la API responde 503. Rellenalas y repite.${NC}"
        echo -e "  Genera cada valor con:"
        echo -e "    ${YELLOW}python3 -c \"import secrets,string; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(43)))\"${NC}"
        exit 1
    fi
    echo "  Los cuatro secretos estan presentes."
else
    cp .env.example .env
    # Alfanumericos a proposito: un `$` o un `#` dentro de un .env es una mina para el parser
    # de compose — medido el 2026-08-22 al rotar SECRET_KEY.
    for CLAVE in POSTGRES_PASSWORD DJANGO_SECRET_KEY BUNKER_BACKUP_TOKEN BUNKER_API_TOKEN; do
        VALOR=$(python3 -c "import secrets,string; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(43)))")
        python3 - "$CLAVE" "$VALOR" <<'PY'
import pathlib, re, sys
clave, valor = sys.argv[1], sys.argv[2]
p = pathlib.Path('.env')
t = p.read_text(encoding='utf-8')
if re.search(rf'^{clave}=.*$', t, flags=re.M):
    t = re.sub(rf'^{clave}=.*$', f'{clave}={valor}', t, flags=re.M)
else:
    t += f'\n{clave}={valor}\n'
p.write_text(t, encoding='utf-8')
PY
    done
    # La IP de LAN entra en ALLOWED_HOSTS porque el puerto es 0.0.0.0: sin ella, el movil recibe
    # un 400 de Django que no dice por que.
    :
fi

# LA IP VA A ALLOWED_HOSTS SIEMPRE, no solo cuando el .env es nuevo. Estaba dentro del `else` y
# el mensaje final de abajo la anunciaba igual: quien ya tenia .env —el caso comun al
# actualizar— recibia una URL que Django contesta con un 400 pelado, porque con DEBUG=False
# ALLOWED_HOSTS decide. El mensaje prometia lo que el script no habia configurado.
if [ -n "$IP" ]; then
        python3 - "$IP" <<'PY'
import pathlib, re, sys
ip = sys.argv[1]
p = pathlib.Path('.env')
t = p.read_text(encoding='utf-8')
m = re.search(r'^DJANGO_ALLOWED_HOSTS=(.*)$', t, flags=re.M)
actuales = [h.strip() for h in (m.group(1) if m else '').split(',') if h.strip()]
if ip not in actuales:
    actuales.append(ip)
linea = 'DJANGO_ALLOWED_HOSTS=' + ','.join(actuales)
t = re.sub(r'^DJANGO_ALLOWED_HOSTS=.*$', linea, t, flags=re.M) if m else t + '\n' + linea + '\n'
p.write_text(t, encoding='utf-8')
PY
    echo "  IP de LAN en DJANGO_ALLOWED_HOSTS: $IP"
fi
echo "  El token de la API lo necesitas para el movil:"
echo -e "    ${YELLOW}grep '^BUNKER_API_TOKEN=' .env${NC}"

#PASO: levantar
paso "Levantando los contenedores..."
docker compose up -d
# La misma perilla que lee cli/config.py, no una nueva. Si este Bunker no vive en el 8009 —otra
# maquina con el puerto ocupado, o un clon de prueba junto al stack vivo— esta espera tiene que
# mirar SU servidor: contra el 8009 fijo daria por bueno un Django que no es este.
# Se lee del ENTORNO y, si no esta, DE `.env` — que es donde `cli/config.py` la busca de verdad
# (`load_dotenv` + `os.getenv`). Mirando solo el entorno, quien la ponga en `.env` —el sitio
# documentado, linea 11 de `.env.example`— tendria esta espera apuntando al 8009 igualmente:
# exactamente el "daria por bueno un Django que no es este" que este comentario dice evitar.
BASE="${BUNKER_API_URL:-$(sed -n 's/^BUNKER_API_URL=//p' .env | head -1)}"
BASE="${BASE:-http://127.0.0.1:8009}"
echo "  Esperando a que Django responda en ${BASE}..."
for _ in $(seq 1 30); do
    CODIGO=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "${BASE}/api/health/" || echo 000)
    [ "$CODIGO" = "200" ] && break
    sleep 2
done
# Sin `-w` un `curl -s -o /dev/null` devuelve 0 con un 403 y esta espera se quedaria MUDA en vez
# de romperse — medido en scripts/ronda_doze.sh el 2026-08-31.
[ "${CODIGO:-000}" = "200" ] || { echo -e "${RED}  Django no respondio 200 en ${BASE}/api/health/ (llego ${CODIGO:-000}).${NC}"; exit 1; }
echo "  Django responde."

#PASO: migrar
paso "Aplicando migraciones..."
docker compose exec -T web python manage.py migrate

#PASO: restaurar
paso "Restaurando una capsula (opcional)..."
if [ -z "$CAPSULA" ]; then
    echo "  Sin capsula: el Bunker arranca vacio."
    echo -e "  Para cargar una: ${YELLOW}./install.sh <fichero.json>${NC}"
else
    [ -f "$CAPSULA" ] || { echo -e "${RED}  No existe: $CAPSULA${NC}"; exit 1; }
    # Se COPIA al contenedor en vez de asumir que `/app/<basename>` la contiene. El bind de
    # `.:/app` solo cubre el repositorio, asi que una capsula en ~/Descargas no estaria ahi — y
    # (Until 2026-09-02 `./backups/` was worse still: the `bunker_backups` volume mounted ON TOP
    # of `/app/backups`. That volume was retired; the `cp` is still the right move.)
    docker compose cp "$CAPSULA" web:/tmp/capsula.json
    # --ignorenonexistent NO es opcional: toda capsula anterior al 2026-08-27 nombra modelos de
    # `posada`/`chess_study`, que ya no viven aqui. 6 de 6 fallaban sin el.
    docker compose exec -T web python manage.py loaddata --ignorenonexistent /tmp/capsula.json
    docker compose exec -T web rm -f /tmp/capsula.json
fi

echo -e "\n${CYAN}================================================${NC}"
echo -e "${GREEN} Instalacion completada.${NC}"
echo -e "  Arranca la TUI con: ${YELLOW}${VENV_DIR}/bin/bunker enter${NC}"
echo -e "  Desde el movil:     ${YELLOW}${BASE/127.0.0.1/${IP:-<tu-IP-de-LAN>}}/movil/${NC}"
echo -e "${CYAN}================================================${NC}"
