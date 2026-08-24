FROM python:3.12-slim

# Variables de entorno para que Python no genere archivos .pyc 
# y envíe los logs directamente a la terminal 
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# directorio de trabajo dentro del contenedor
WORKDIR /app
# Copia primero el archivo de dependencias para aprovechar el caché de Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Instalar cron y el motor UCI. Debian deja el binario en /usr/games/stockfish,
# que es exactamente la ruta por defecto de STOCKFISH_PATH en chess_study/views.py.
RUN apt-get update && apt-get install -y cron stockfish && rm -rf /var/lib/apt/lists/*

# Copia el resto del código del proyecto al contenedor
COPY . /app/

# Configurar cron. Solo /etc/cron.d: ese formato acepta el campo de usuario ("root").
# Instalarlo ademas con `crontab` lo interpretaba como crontab de usuario, donde el sexto
# campo ya es el comando, y la tarea intentaba ejecutar el binario inexistente "root".
COPY bunker_crontab /etc/cron.d/bunker-cron
RUN chmod 0644 /etc/cron.d/bunker-cron
RUN touch /var/log/cron.log

# Dump the environment to /etc/bunker.env before starting cron: cron jobs do not inherit
# compose's variables (only PID 1 receives them), and backup.sh needs the POSTGRES_* ones.
# --insecure: with DEBUG=False runserver stops serving /static/, and the phone requests
# {% static 'movil/dist/main.js' %}, which would 404. One flag instead of adding
# whitenoise + collectstatic to a single-user service behind the tailnet.
# ponytail: --insecure serves static files with no caching and no compression; the day the
# panel feels slow on the phone is when whitenoise earns its place.
CMD printenv | grep -E '^(POSTGRES_|TZ=)' > /etc/bunker.env && cron && python manage.py runserver --insecure 0.0.0.0:8000
