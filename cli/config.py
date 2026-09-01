import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# Try to load .env from the project root if it exists
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

BASE_URL = os.environ.get("BUNKER_API_URL", "http://localhost:8009")

# Puerto que exponen los tuneles SSH del escaner movil (-R 80:localhost:<API_PORT>).
# Se deriva de BASE_URL para que cambiar el puerto en un solo sitio siga bastando.
API_PORT = urlparse(BASE_URL).port or (443 if BASE_URL.startswith("https") else 80)

# Sin valor por defecto a proposito: el backend falla cerrado si no esta configurado,
# y un default escrito en el repositorio no protegeria nada.
BACKUP_TOKEN = os.environ.get("BUNKER_BACKUP_TOKEN", "")

# Vacio por defecto A PROPOSITO, igual que BUNKER_BACKUP_TOKEN: un valor de relleno en un
# fichero de ejemplo es un token publicado.
# OJO: HOY NO LO LEE NADIE. El middleware que lo exige es la Tarea 5 del plan de instalacion
# portable; `bunker_core/settings.py:MIDDLEWARE` lleva los siete de serie y ninguno mas. Esto
# lo MANDA (cabecera `X-Bunker-Api-Token`) para que cuando el lector se encienda ya este ahi.
API_TOKEN = os.environ.get("BUNKER_API_TOKEN", "")
