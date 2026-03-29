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

# Copia el resto del código del proyecto al contenedor
COPY . /app/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]