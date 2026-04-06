import requests
import re


def clean_movie_title(raw_title):
    """Limpia la basura comercial para que TMDB pueda entenderlo."""
    if not raw_title:
        return None
    clean = re.sub(
        r'(?i)(blu-ray|bluray|dvd|4k|uhd|steelbook|edición|edition|import|combo|pack)', '', raw_title)
    return re.split(r'[-(\[]', clean)[0].strip()


def search_upcitemdb_api(barcode):
    """Nodo 1: API Comercial Principal"""
    try:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200 and resp.json().get('items'):
            return resp.json()['items'][0]['title']
    except:
        pass
    return None


def search_upcindex_scraper(barcode):
    """Nodo 2: Scraper de emergencia (Base de datos abierta)"""
    try:
        url = f"https://www.upcindex.com/{barcode}"
        resp = requests.get(
            url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5.0)
        if resp.status_code == 200:
            # Extracción rápida con Regex para no requerir BeautifulSoup
            match = re.search(r'<title>(.*?)</title>',
                              resp.text, re.IGNORECASE)
            if match:
                title = match.group(1).replace(
                    "UPC", "").replace(barcode, "").strip()
                if len(title) > 3 and "No found" not in title:
                    return title
    except:
        pass
    return None


def search_searchupc_api(barcode):
    """Nodo 3: API Secundaria"""
    try:
        url = f"https://www.searchupc.com/handlers/upcsearch.ashx?request_type=3&upc={barcode}"
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('0') and data['0'].get('productname'):
                return data['0']['productname']
    except:
        pass
    return None


def resolve_barcode_exhaustively(barcode):
    """El Patrón Chain of Responsibility. Salta de nodo en nodo hasta encontrar el título."""

    print(f"[ORÁCULO COMERCIAL] Iniciando rastreo para EAN: {barcode}")

    raw_title = search_upcitemdb_api(barcode)
    if raw_title:
        print(
            f"[ORÁCULO COMERCIAL] ¡Encontrado en Nodo 1 (UPCitemdb)! -> {raw_title}")
        return clean_movie_title(raw_title)

    raw_title = search_upcindex_scraper(barcode)
    if raw_title:
        print(
            f"[ORÁCULO COMERCIAL] ¡Encontrado en Nodo 2 (UPCIndex)! -> {raw_title}")
        return clean_movie_title(raw_title)

    raw_title = search_searchupc_api(barcode)
    if raw_title:
        print(
            f"[ORÁCULO COMERCIAL] ¡Encontrado en Nodo 3 (SearchUPC)! -> {raw_title}")
        return clean_movie_title(raw_title)

    print(f"[ORÁCULO COMERCIAL] Búsqueda exhaustiva fallida. Código desconocido.")
    return None
