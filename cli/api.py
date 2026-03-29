import requests
from typing import Dict, Optional
from rich.console import Console
import re
import time
import random
import os
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

console = Console()

COMIC_VINE_KEY = "8db1d3de48158f3b4b5c2faadbb572818fddf245"
HEADERS_CV = {"User-Agent": "LibraryManagerCLI/1.0 (Comic Scanner)"}
GOOGLE_BOOKS_KEY = os.getenv("GOOGLE_BOOKS_KEY", "")


def fetch_from_comicvine(isbn: str) -> Optional[Dict]:
    """Oracle 1: Comic Vine API (Especialista en Cómics y Mangas)"""
    url = f"https://comicvine.gamespot.com/api/search/?api_key={COMIC_VINE_KEY}&format=json&resources=volume,issue&query={isbn}"

    try:
        response = requests.get(url, headers=HEADERS_CV, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("error") != "OK" or data.get("number_of_total_results", 0) == 0:
            return None

        comic = data.get("results", [])[0]
        if not comic:
            return None

        volume_data = comic.get("volume") or {}
        title = comic.get("name") or volume_data.get("name") or "Unknown Comic"
        issue_num = comic.get("issue_number") or ""

        full_title = f"{title} #{issue_num}" if issue_num else title

        publisher_data = comic.get("publisher") or {}
        publisher = publisher_data.get("name") or ""

        image_data = comic.get("image") or {}
        cover_url = image_data.get("medium_url") or ""

        description = comic.get("deck") or comic.get("description") or ""

        if description:
            description = re.sub('<[^<]+?>', '', description).strip()

        return {
            "source": "Comic Vine",
            "title": full_title,
            "subtitle": "",
            "author": "Varios Autores (Cómic)",
            "publisher": publisher,
            "categories": ["Comics & Graphic Novels"],
            "page_count": 0,
            "publish_date": comic.get("cover_date", ""),
            "cover_url": cover_url,
            "description": description[:800] + "..." if len(description) > 800 else description,
        }
    except Exception as e:
        console.print(
            f"[dim yellow] Comic Vine falló ({e}). Pasando a Google Books...[/dim yellow]")
        return None


def fetch_from_google_books(isbn: str) -> Optional[Dict]:
    """Oracle 2: Google Books API (Primary Comercial con Tolerancia a Fallos)"""

    if GOOGLE_BOOKS_KEY:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_BOOKS_KEY}"
    else:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"

    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)

            # Interceptamos el estrangulamiento de red
            if response.status_code == 429:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                console.print(
                    f"[dim yellow] Estrangulamiento en Google (429). Reintentando en {sleep_time:.1f}s...[/dim yellow]")
                time.sleep(sleep_time)
                continue  # Volvemos a intentar el ciclo

            response.raise_for_status()
            data = response.json()

            if "items" not in data or not data["items"]:
                return None

            volume_info = data["items"][0].get("volumeInfo") or {}
            authors = volume_info.get("authors") or ["Unknown Author"]
            images = volume_info.get("imageLinks") or {}
            cover_url = images.get("thumbnail") or ""
            cover_url = cover_url.replace("http://", "https://")
            categories = volume_info.get("categories") or []

            return {
                "source": "Google Books",
                "title": volume_info.get("title", "Unknown Title"),
                "subtitle": volume_info.get("subtitle", ""),
                "author": authors[0] if authors else "Unknown Author",
                "publisher": volume_info.get("publisher", ""),
                "categories": categories[:3],
                "page_count": volume_info.get("pageCount", 0),
                "publish_date": volume_info.get("publishedDate", ""),
                "cover_url": cover_url,
                "description": volume_info.get("description", ""),
            }
        except Exception as e:
            console.print(
                f"[dim yellow] Falló Google Books ({e}). Intentando Fallback final...[/dim yellow]")
            return None

    return None  # Si agota los 3 intentos, se rinde y pasa a OpenLibrary


def fetch_from_openlibrary(isbn: str) -> Optional[Dict]:
    """Oracle 3: OpenLibrary API (Rarezas y Antiguos)"""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    headers = {"User-Agent": "LibraryManagerCLI/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        key = f"ISBN:{isbn}"
        if key not in data:
            return None

        book = data[key]

        authors = book.get("authors") or [{"name": "Unknown Author"}]
        publishers = book.get("publishers") or [{"name": ""}]
        subjects = book.get("subjects") or []
        cover_data = book.get("cover") or {}

        return {
            "source": "OpenLibrary",
            "title": book.get("title", "Unknown Title"),
            "subtitle": book.get("subtitle", ""),
            "author": authors[0].get("name", "Unknown Author"),
            "publisher": publishers[0].get("name", ""),
            "categories": [sub.get("name", "") for sub in subjects[:3]],
            "page_count": book.get("number_of_pages", 0),
            "publish_date": book.get("publish_date", ""),
            "cover_url": cover_data.get("large") or cover_data.get("medium") or "",
            "description": "",
        }
    except Exception as e:
        return None


def fetch_book_by_isbn(isbn: str) -> list:
    """
    El Gateway Federado Concurrente.
    Dispara hilos en paralelo a Comic Vine, Google Books y OpenLibrary simultáneamente.
    Retorna una lista con todas las versiones encontradas.
    """
    console.print(
        f"[cyan] Despertando a los Oráculos para el ISBN {isbn}...[/cyan]")

    results = []

    # ThreadPoolExecutor para lanzar las 3 peticiones de red al mismo tiempo
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Mapea los hilos a sus respectivas funciones
        future_to_api = {
            executor.submit(fetch_from_comicvine, isbn): "Comic Vine",
            executor.submit(fetch_from_google_books, isbn): "Google Books",
            executor.submit(fetch_from_openlibrary, isbn): "OpenLibrary"
        }

        # A medida que los oráculos van respondiendo (el primero que termine), procesa sus datos
        for future in concurrent.futures.as_completed(future_to_api):
            api_name = future_to_api[future]
            try:
                data = future.result()
                if data:
                    console.print(
                        f"  [green]✔ {api_name} encontró una coincidencia.[/green]")
                    results.append(data)
                else:
                    console.print(
                        f"  [dim]✘ {api_name} no encontró registros.[/dim]")
            except Exception as e:
                console.print(
                    f"  [dim red] Error interno en {api_name}: {e}[/dim red]")

    return results
