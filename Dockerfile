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

# Instalar cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copia el resto del código del proyecto al contenedor
COPY . /app/

# Configurar cron
COPY bunker_crontab /etc/cron.d/bunker-cron
RUN chmod 0644 /etc/cron.d/bunker-cron
RUN crontab /etc/cron.d/bunker-cron
RUN touch /var/log/cron.log

CMD cron && python manage.py runserver 0.0.0.0:8000