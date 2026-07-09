import os
import requests

# Reemplaza con tu token de Last.fm, o configúralo en tu archivo .env
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")
USER_AGENT = "BunkerDisquera/1.0"

def enrich_album_data(artist: str, title: str):
    """
    Oráculo de Last.fm: Busca información detallada de un álbum.
    Retorna un diccionario con duration_minutes, tracklist y cover_url.
    """
    if not LASTFM_API_KEY or LASTFM_API_KEY == "TU_TOKEN_AQUI":
        print("Aviso: Falta el token de Last.fm (LASTFM_API_KEY). Usando mock de prueba.")
        return {
            "duration_minutes": 61,
            "tracklist": [
                {"title": "One More Time", "duration": 320},
                {"title": "Aerodynamic", "duration": 207},
                {"title": "Digital Love", "duration": 298},
                {"title": "Harder, Better, Faster, Stronger", "duration": 224}
            ],
            "cover_url": "https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png"
        }

    url = "https://ws.audioscrobbler.com/2.0/"
    headers = {"User-Agent": USER_AGENT}

    params = {
        "method": "album.getinfo",
        "api_key": LASTFM_API_KEY,
        "artist": artist,
        "album": title,
        "format": "json"
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10.0)
        resp.raise_for_status()
        
        data = resp.json()
        if 'error' in data or 'album' not in data:
            return None
            
        album_data = data['album']
        
        # 1. Extraer Tracklist y calcular duración total
        tracklist = []
        total_seconds = 0
        
        tracks = album_data.get('tracks', {}).get('track', [])
        # Last.fm returns a dict if there's only one track, or list if multiple
        if isinstance(tracks, dict):
            tracks = [tracks]
            
        for t in tracks:
            duration_sec = int(t.get('duration', 0) or 0)
            total_seconds += duration_sec
            tracklist.append({
                "title": t.get('name', 'Desconocido'),
                "duration": duration_sec
            })
            
        duration_minutes = round(total_seconds / 60) if total_seconds > 0 else None
        
        # 2. Extraer Cover URL (priorizar mega o extralarge)
        cover_url = None
        images = album_data.get('image', [])
        for img in reversed(images):
            if img.get('#text'):
                cover_url = img.get('#text')
                # Si encontramos un extralarge o mega, nos detenemos (vienen en orden ascendente de tamaño usualmente)
                if img.get('size') in ['mega', 'extralarge']:
                    break

        return {
            "duration_minutes": duration_minutes,
            "tracklist": tracklist,
            "cover_url": cover_url
        }

    except Exception as e:
        print(f"Error conectando con Last.fm: {e}")
        return None
