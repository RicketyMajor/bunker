# Usa una imagen oficial y ultra ligera de Node.js
FROM node:20-alpine

# Instalar Chromium y dependencias para Puppeteer.
# node:20-alpine ya trae nodejs y npm: instalarlos desde los repos de Alpine metia una
# segunda version de Node en la imagen.
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

# Puppeteer usa el Chrome instalado en el sistema
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia primero el manifiesto para aprovechar la caché de Docker.
# El lockfile tambien: sin el, `npm install` resolvia versiones nuevas en cada build.
COPY package.json package-lock.json ./

# Instala exactamente lo que fija el lockfile
RUN npm ci

# Copia el resto del código
COPY . .

# docker-compose.yml sobreescribe esto con `command:` por radar; el default apunta al de
# libros porque "npm start" no existe en package.json.
CMD ["npm", "run", "start:books"]