# Usamos una imagen oficial y ultra ligera de Node.js
FROM node:20-alpine

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el package.json para aprovechar la caché de Docker
COPY package.json ./

# Instalamos las dependencias
RUN npm install

# Copiamos el resto del código
COPY . .

# Comando para iniciar el servicio
CMD ["npm", "start"]