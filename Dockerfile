# Usamos una imagen oficial de Python ligera
FROM python:3.12-slim

# Configuramos variables de entorno para que Python no genere archivos .pyc 
# y envíe los logs directamente a la terminal (útil para ver errores en Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Creamos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el archivo de dependencias para aprovechar el caché de Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del proyecto al contenedor
COPY . /app/

# El comando por defecto que se ejecutará al iniciar el contenedor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]