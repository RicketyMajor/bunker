# Instalador del Bunker para Windows (PowerShell 5.1 o superior).
#
# Su gemelo es install.sh, y `tests/test_instaladores.py` comprueba que los dos declaran los
# mismos `#PASO:` en el mismo orden. Si anades, quitas o reordenas un paso alli, hazlo aqui.
#
# ADVERTENCIA HONESTA: este fichero NO SE PUEDE EJECUTAR NI VERIFICAR desde la maquina de
# desarrollo, que es Linux. La comprobacion de deriva prueba que declara los mismos pasos que su
# gemelo — NO prueba que funcione. La primera corrida real en Windows es la primera prueba.
#
# Si Windows se niega a ejecutarlo:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

# `$ErrorActionPreference = 'Stop'` NO aborta por el codigo de salida de un comando NATIVO en
# Windows PowerShell 5.1: `$PSNativeCommandUseErrorActionPreference` llego en PS 7.3. Sin esto,
# un `migrate` que falla deja seguir el script y este imprime "Instalacion completada" con la
# base sin migrar — mientras install.sh aborta por su `set -euo pipefail`. Los instaladores
# tienen que fallar igual, no solo declarar los mismos pasos.
function Abortar-Si-Fallo($que) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Fallo: $que (codigo $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
}
$VenvDir = '.venv'

function Paso($t) { Write-Host "`n> $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "  $t" -ForegroundColor Yellow }

Write-Host '================================================' -ForegroundColor Cyan
Write-Host '          Instalador del Bunker                 ' -ForegroundColor Cyan
Write-Host '================================================' -ForegroundColor Cyan

#PASO: requisitos
Paso 'Comprobando requisitos...'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host '  Falta python.' -ForegroundColor Red; exit 1
}
# `docker compose` (V2, sin guion), igual que ensure_infrastructure_up.
docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host '  Falta docker compose (V2).' -ForegroundColor Red; exit 1
}
Write-Host '  python y docker compose, presentes.'

#PASO: entorno
Paso "Creando el entorno virtual ($VenvDir)..."
python -m venv $VenvDir
$Py = Join-Path $VenvDir 'Scripts\python.exe'
& $Py -m pip install --upgrade pip | Out-Null
& $Py -m pip install -r requirements.txt | Out-Null
& $Py -m pip install -e . | Out-Null
Write-Host "  Dependencias instaladas. El comando queda en $VenvDir\Scripts\bunker.exe."

# EL BUNDLE DEL MOVIL. `bunker_core/static/movil/dist/` esta en .gitignore, asi que un clon
# fresco NO lo trae y sin el `/movil/` y `/panel/` se sirven sin su JavaScript.
# Se construye en un contenedor de Node porque Docker ya es requisito y Node no.
# Sin `-u` aqui a proposito: en Docker Desktop la propiedad de los ficheros la resuelve el
# propio Docker, y un `id -u` de Linux no existe en Windows.
Write-Host '  Construyendo el bundle del movil...'
docker run --rm -e HOME=/tmp -e npm_config_cache=/tmp/.npm -v "${PWD}:/app" -w /app node:20-alpine sh -c "npm ci --silent && npm run build" | Out-Null
Abortar-Si-Fallo 'construir el bundle'
if (-not (Test-Path 'bunker_core/static/movil/dist/main.js')) {
    Write-Host '  El bundle no se construyo.' -ForegroundColor Red; exit 1
}
Write-Host '  Bundle construido.'

#PASO: secretos
Paso 'Generando los secretos de ESTA instalacion...'
# La IP sale de cli/main.py:get_local_ip(), que ya resuelve el NAT de WSL2, y NO de ipconfig.
$Ip = ''
try { $Ip = (& $Py -c "from cli.main import get_local_ip; print(get_local_ip())").Trim() } catch { $Ip = '' }
if (Test-Path '.env') {
    Aviso '.env ya existe: sus secretos no se tocan. Borralo si quieres unos nuevos.'
    # PERO SE COMPRUEBAN. Un .env anterior al 2026-08-31 trae BUNKER_API_TOKEN VACIO, y
    # bunker_core/auth.py falla cerrado: sin el, TODA ruta bajo /api/ responde 503. Como
    # /api/health/ esta en la allowlist, la espera de mas abajo recibiria su 200 y este script
    # diria "Instalacion completada" con la TUI, la PWA y los tres scrapers muertos.
    $EnvTexto = Get-Content '.env' -Raw
    $Faltan = @()
    foreach ($Clave in @('POSTGRES_PASSWORD','DJANGO_SECRET_KEY','BUNKER_BACKUP_TOKEN','BUNKER_API_TOKEN')) {
        $M = [regex]::Match($EnvTexto, "(?m)^$Clave=(.*)$")
        if (-not $M.Success -or -not $M.Groups[1].Value.Trim()) { $Faltan += $Clave }
    }
    if ($Faltan.Count -gt 0) {
        Write-Host "  Tu .env tiene estas claves VACIAS: $($Faltan -join ', ')" -ForegroundColor Red
        Write-Host '  Sin BUNKER_API_TOKEN toda la API responde 503. Rellenalas y repite.' -ForegroundColor Red
        exit 1
    }
    Write-Host '  Los cuatro secretos estan presentes.'
} else {
    Copy-Item '.env.example' '.env'
    # Alfanumericos a proposito: un `$` o un `#` dentro de un .env es una mina para el parser de
    # compose — medido el 2026-08-22 al rotar SECRET_KEY.
    foreach ($Clave in @('POSTGRES_PASSWORD', 'DJANGO_SECRET_KEY', 'BUNKER_BACKUP_TOKEN', 'BUNKER_API_TOKEN')) {
        $Valor = & $Py -c "import secrets,string; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(43)))"
        $Valor = $Valor.Trim()
        $Texto = Get-Content '.env' -Raw
        if ($Texto -match "(?m)^$Clave=.*$") {
            $Texto = [regex]::Replace($Texto, "(?m)^$Clave=.*$", "$Clave=$Valor")
        } else {
            $Texto = $Texto + "`n$Clave=$Valor`n"
        }
        # WriteAllText con UTF8Encoding($false) y no `Set-Content -Encoding UTF8`: en PS 5.1
        # ese parametro escribe BOM, y un `\uFEFF` delante de la primera linea del .env deja de
        # ser un comentario para un parser estricto.
        [IO.File]::WriteAllText((Join-Path $PWD '.env'), $Texto, (New-Object Text.UTF8Encoding $false))
    }
    Write-Host '  Cuatro secretos generados.'
}

# LA IP VA A ALLOWED_HOSTS SIEMPRE, no solo cuando el .env es nuevo. Dentro del `else`, quien ya
# tenia .env —el caso comun al actualizar— recibia del mensaje final una URL que Django contesta
# con un 400 pelado, porque con DEBUG=False manda ALLOWED_HOSTS.
if ($Ip) {
        $Texto = Get-Content '.env' -Raw
        $M = [regex]::Match($Texto, '(?m)^DJANGO_ALLOWED_HOSTS=(.*)$')
        $Actuales = @()
        # @(...) obligatorio: con UN solo host la tuberia devuelve un [string], y el += de
        # abajo CONCATENA en vez de anadir -> DJANGO_ALLOWED_HOSTS=localhost192.168.0.8
        if ($M.Success) { $Actuales = @($M.Groups[1].Value.Split(',') | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() }) }
        if ($Actuales -notcontains $Ip) { $Actuales += $Ip }
        $Linea = 'DJANGO_ALLOWED_HOSTS=' + ($Actuales -join ',')
        if ($M.Success) {
            $Texto = [regex]::Replace($Texto, '(?m)^DJANGO_ALLOWED_HOSTS=.*$', $Linea)
        } else {
            $Texto = $Texto + "`n$Linea`n"
        }
        [IO.File]::WriteAllText((Join-Path $PWD '.env'), $Texto, (New-Object Text.UTF8Encoding $false))
    Write-Host "  IP de LAN en DJANGO_ALLOWED_HOSTS: $Ip"
}
Write-Host '  El token de la API lo necesitas para el movil:'
Aviso '    Select-String -Path .env -Pattern ''^BUNKER_API_TOKEN'''

#PASO: levantar
Paso 'Levantando los contenedores...'
docker compose up -d
Abortar-Si-Fallo 'levantar los contenedores'
# La misma perilla que lee cli/config.py, no una nueva. Si este Bunker no vive en el 8009, esta
# espera tiene que mirar SU servidor: contra el 8009 fijo daria por bueno un Django que no es este.
# Del entorno y, si no, DE .env — que es donde cli/config.py la busca (load_dotenv).
$Base = $env:BUNKER_API_URL
if (-not $Base -and (Test-Path '.env')) {
    $M = [regex]::Match((Get-Content '.env' -Raw), '(?m)^BUNKER_API_URL=(.+)$')
    if ($M.Success) { $Base = $M.Groups[1].Value.Trim() }
}
if (-not $Base) { $Base = 'http://127.0.0.1:8009' }
Write-Host "  Esperando a que Django responda en $Base..."
$Codigo = 0
foreach ($i in 1..30) {
    try {
        # -UseBasicParsing y el try/catch: Invoke-WebRequest LANZA en 4xx/5xx, asi que un 403 no
        # puede quedarse mudo aqui como se quedaba `curl -s -o /dev/null` sin -w.
        $R = Invoke-WebRequest -Uri "$Base/api/health/" -TimeoutSec 3 -UseBasicParsing
        $Codigo = [int]$R.StatusCode
    } catch {
        $Codigo = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    }
    if ($Codigo -eq 200) { break }
    Start-Sleep -Seconds 2
}
if ($Codigo -ne 200) {
    Write-Host "  Django no respondio 200 en $Base/api/health/ (llego $Codigo)." -ForegroundColor Red; exit 1
}
Write-Host '  Django responde.'

#PASO: migrar
Paso 'Aplicando migraciones...'
docker compose exec -T web python manage.py migrate
Abortar-Si-Fallo 'aplicar las migraciones'

#PASO: restaurar
Paso 'Restaurando una capsula (opcional)...'
$Capsula = if ($args.Count -ge 1) { $args[0] } else { '' }
if (-not $Capsula) {
    Write-Host '  Sin capsula: el Bunker arranca vacio.'
    Aviso '  Para cargar una: .\install.ps1 <fichero.json>'
} else {
    if (-not (Test-Path $Capsula)) { Write-Host "  No existe: $Capsula" -ForegroundColor Red; exit 1 }
    # --ignorenonexistent NO es opcional: toda capsula anterior al 2026-08-27 nombra modelos de
    # `posada`/`chess_study`, que ya no viven aqui. 6 de 6 fallaban sin el.
    # It is COPIED into the container: the .:/app bind only covers the repository, so a capsule
    # outside the repo would not be there. (The `bunker_backups` volume, which also mounted over
    # /app/backups, was retired on 2026-09-02.)
    docker compose cp $Capsula web:/tmp/capsula.json
    Abortar-Si-Fallo 'copiar la capsula al contenedor'
    docker compose exec -T web python manage.py loaddata --ignorenonexistent /tmp/capsula.json
    Abortar-Si-Fallo 'restaurar la capsula'
    docker compose exec -T web rm -f /tmp/capsula.json
}

Write-Host ''
Write-Host '================================================' -ForegroundColor Cyan
Write-Host ' Instalacion completada.' -ForegroundColor Green
Write-Host "  Arranca la TUI con: $VenvDir\Scripts\bunker.exe enter"
$Destino = if ($Ip) { $Base -replace '127\.0\.0\.1', $Ip } else { $Base }
Write-Host "  Desde el movil:     $Destino/movil/"
Write-Host '================================================' -ForegroundColor Cyan
