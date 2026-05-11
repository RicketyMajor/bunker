import os
import requests

# Reemplaza con tu token de Discogs, o configúralo en tu archivo .env
DISCOGS_TOKEN = os.getenv("DISCOGS_API_KEY", "")
# Discogs requiere que identifiques tu aplicación con un User-Agent personalizado
USER_AGENT = "BunkerDisquera/1.0"


def search_album_discogs(query: str, search_type="barcode"):
    """Oráculo de Discogs: Busca por código de barras EAN/UPC o por título."""
    if not DISCOGS_TOKEN or DISCOGS_TOKEN == "TU_TOKEN_AQUI":
        print("Error: Falta el token de Discogs.")
        return None

    url = "https://api.discogs.com/database/search"
    headers = {"User-Agent": USER_AGENT}

    # Parámetros base
    params = {
        "token": DISCOGS_TOKEN,
        "type": "release"  # Solo buscamos lanzamientos físicos oficiales
    }

    if search_type == "barcode":
        params["barcode"] = query
    else:
        params["q"] = query

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10.0)
        resp.raise_for_status()
        results = resp.json().get('results', [])

        if not results:
            return None

        # Tomamos la primera coincidencia (la más relevante)
        data = results[0]

        # Discogs devuelve el título en formato "Artista - Titulo". Lo separamos:
        title_raw = data.get('title', '')
        artist = "Desconocido"
        title = title_raw
        if " - " in title_raw:
            parts = title_raw.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()

        # Detección inteligente de formato
        formats = data.get('format', [])
        format_type = "CD"  # Por defecto
        if "Vinyl" in formats:
            format_type = "VINYL"
        elif "Cassette" in formats:
            format_type = "CASSETTE"

        # Mapeo a nuestro modelo de Django
        return {
            "title": title,
            "artist": artist,
            "label": data.get('label', [''])[0] if data.get('label') else "Independiente",
            "release_year": int(data.get('year')) if data.get('year') and data.get('year').isdigit() else None,
            # Unimos géneros y estilos
            "genres": data.get('genre', []) + data.get('style', []),
            "cover_url": data.get('cover_image'),
            "format_type": format_type,
            "discogs_id": data.get('id')
        }
    except Exception as e:
        print(f"Error conectando con Discogs: {e}")
        return None
