import requests
from typing import Dict, Optional
from rich.console import Console

console = Console()


def fetch_book_by_isbn(isbn: str) -> Optional[Dict]:
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"

    # 1. Añadimos un User-Agent. OpenLibrary pide esto para no bloquearte.
    headers = {
        "User-Agent": "LibraryManagerCLI/1.0 (Proyecto Universitario, contacto: alonso@localhost.com)"
    }

    try:
        # 2. Aumentamos el timeout a 15 segundos y pasamos los headers
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        key = f"ISBN:{isbn}"
        if key not in data:
            return None

        book_info = data[key]

        authors = book_info.get("authors", [{"name": "Unknown Author"}])
        publishers = book_info.get("publishers", [{"name": ""}])
        subjects = book_info.get("subjects", [])

        # Buscamos la descripción real primero
        description_data = book_info.get("description", "")
        if isinstance(description_data, dict):
            description_data = description_data.get("value", "")

        # Buscamos las notas como respaldo
        notes_data = book_info.get("notes", "")
        if isinstance(notes_data, dict):
            notes_data = notes_data.get("value", "")

        # Nos quedamos con la descripción si existe, sino usamos las notas
        final_description = description_data.strip(
        ) if description_data else notes_data.strip()

        cover_info = book_info.get("cover", {})
        cover_url = cover_info.get("large") or cover_info.get("medium") or ""

        return {
            "title": book_info.get("title", "Unknown Title"),
            "subtitle": book_info.get("subtitle", ""),
            "author": authors[0]["name"] if authors else "Unknown Author",
            "publisher": publishers[0]["name"] if publishers else "",
            "categories": [sub["name"] for sub in subjects[:3]],
            "page_count": book_info.get("number_of_pages", 0),
            "publish_date": book_info.get("publish_date", ""),
            "cover_url": cover_url,
            "description": final_description,  # Usamos nuestra nueva variable mejorada
        }

    except requests.exceptions.Timeout:
        # Ahora sabremos si fue culpa del servidor por lentitud
        console.print(
            "[bold red]⚠️ El servidor de OpenLibrary tardó demasiado en responder (Timeout).[/bold red]")
        return None
    except Exception as e:
        # Ahora sabremos si nuestro código se rompió por un dato faltante que no previmos
        console.print(
            f"[bold red]⚠️ Error interno procesando el JSON: {e}[/bold red]")
        return None
