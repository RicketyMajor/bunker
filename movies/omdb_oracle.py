import logging
import os
import requests

logger = logging.getLogger(__name__)

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")


def search_movie_omdb(title):
    """Oráculo de respaldo: OMDb API (Búsqueda por título)"""
    if not OMDB_API_KEY:
        return None

    url = "http://www.omdbapi.com/"
    params = {"t": title, "apikey": OMDB_API_KEY, "plot": "full"}

    try:
        resp = requests.get(url, params=params, timeout=5.0)
        data = resp.json()
        if data.get('Response') == 'True':
            return {
                "title": data.get('Title'),
                "director": data.get('Director'),
                "writers": data.get('Writer', '').split(', ')[0] if data.get('Writer') else "Desconocido",
                "production_company": data.get('Production', "Desconocida"),
                "release_year": int(data.get('Year')[:4]) if data.get('Year') else None,
                "genres": data.get('Genre', '').split(', '),
                "synopsis": data.get('Plot'),
                "cast": data.get('Actors'),
                "poster_url": data.get('Poster') if data.get('Poster') != "N/A" else None
            }
    except Exception:
        logger.warning("Fallo un nodo de oraculo OMDB", exc_info=True)
    return None
