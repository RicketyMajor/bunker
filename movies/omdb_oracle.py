import os
import requests

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
                "release_year": int(data.get('Year')[:4]) if data.get('Year') else None,
                "genres": data.get('Genre', '').split(', '),
                "synopsis": data.get('Plot'),
                "cast": data.get('Actors'),
                "poster_url": data.get('Poster') if data.get('Poster') != "N/A" else None
            }
    except:
        pass
    return None
