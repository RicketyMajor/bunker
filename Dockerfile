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

# No extra packages. `stockfish` was installed here for `chess_study`, which left for
# ~/dev/ajedrez on 2026-08-27. `cron` followed it out on 2026-08-29, with `bunker_crontab`,
# `scripts/backup.sh` and the `/etc/bunker.env` dump the CMD used to write for it — see the
# backup section of README.md for why the host timer replaced it outright.

# Copia el resto del código del proyecto al contenedor
COPY . /app/

# --insecure: with DEBUG=False runserver stops serving /static/, and the phone requests
# {% static 'movil/dist/main.js' %}, which would 404. One flag instead of adding
# whitenoise + collectstatic to a single-user service behind the tailnet.
# ponytail: --insecure serves static files with no caching and no compression; the day the
# panel feels slow on the phone is when whitenoise earns its place.
CMD ["python", "manage.py", "runserver", "--insecure", "0.0.0.0:8000"]
