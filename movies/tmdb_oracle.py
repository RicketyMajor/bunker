import os
import requests

# Recomendación: Añade TMDB_API_KEY a tu archivo .env
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "TU_CLAVE_AQUI")


def search_movie_tmdb(title: str):
    """Oráculo de The Movie Database (Búsqueda por título)"""
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "es-ES",
        "page": 1
    }

    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        results = resp.json().get('results', [])

        if not results:
            return None

        # Toma la primera coincidencia
        movie_data = results[0]
        movie_id = movie_data.get('id')

        # Hacem una segunda petición para obtener detalles completos (como duración y director)
        detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=es-ES&append_to_response=credits"
        detail_resp = requests.get(detail_url).json()

        # Extrae el director del bloque 'credits'
        crew = detail_resp.get('credits', {}).get('crew', [])
        director = next(
            (member['name'] for member in crew if member['job'] == 'Director'), "Desconocido")

        # Extrae el reparto (Top 3 actores)
        cast_list = detail_resp.get('credits', {}).get('cast', [])[:3]
        cast_names = ", ".join([actor['name'] for actor in cast_list])

        # Mapea al modelo de Django
        return {
            "title": detail_resp.get('title'),
            "original_title": detail_resp.get('original_title'),
            "director": director,
            "cast": cast_names,
            "release_year": int(detail_resp.get('release_date', '0')[:4]) if detail_resp.get('release_date') else None,
            "duration_minutes": detail_resp.get('runtime'),
            "genres": [g['name'] for g in detail_resp.get('genres', [])],
            "synopsis": detail_resp.get('overview'),
            "poster_url": f"https://image.tmdb.org/t/p/w500{detail_resp.get('poster_path')}" if detail_resp.get('poster_path') else None
        }
    except Exception as e:
        print(f"Error en Oráculo TMDB: {e}")
        return None
