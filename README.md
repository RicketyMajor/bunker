# BUNKER (NeoLibrary 3.0)

Bunker es un Centro de Operaciones Multimedia operado 100% desde la terminal (TUI). Diseñado con una arquitectura de microservicios, permite gestionar tu biblioteca de libros y colección de películas físicas, apoyado por Scrapers que vigilan nuevos lanzamientos en segundo plano.

## Características Principales

- **Interfaz TUI:** Navegación por pestañas, modales flotantes, y un "Grid Cinematográfico" construidos con Textual y Typer.
- **Scraper (Node.js):** Un scraper asíncrono que busca novedades literarias en Google Books y estrenos cinematográficos en The Movie Database (TMDB).
- **Escáner Móvil:** Levanta un túnel SSH en background y renderiza un código QR en ASCII dentro de la terminal para escanear códigos de barras (ISBN/UPC) con la cámara de tu teléfono.
- **Transacciones Distribuidas:** Sincronización automática entre el registro de hábitos anuales y el inventario principal.

---

## Requisitos

Asegúrate de tener instalados los siguientes componentes en tu sistema operativo (Linux/macOS):

- [Python 3.10+](https://www.python.org/downloads/)
- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/)
- `git`
- Una API Key gratuita de [The Movie Database (TMDB)](https://developer.themoviedb.org/docs/getting-started)

---

## Guía de Instalación

Sigue estos pasos en orden para desplegar la arquitectura completa en tu máquina local.

### 1. Clonar el Repositorio

```bash
git clone [https://github.com/RicketyMajor/library-manager.git](https://github.com/RicketyMajor/library-manager.git)
cd library-manager
```

### 2. Configurar Variables de Entorno

```bash
touch .env
```

```
TMDB_API_KEY=...
```

### 3. Levantar Docker

```bash
docker-compose up -d --build
```

### 4. Ejecutar Migraciones de Base de Datos

```bash
docker-compose exec web python manage.py migrate
```

### 5. Crear Superusuario

```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Instalar el Cliente de Terminal

```bash
chmod +x install.sh
./install.sh
```
