from __future__ import annotations

import re
import time
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

# En-tetes pour eviter les blocages simples.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Config des categories a scraper.
CATEGORIES = {
    "vetements-homme": {
        "label": "Vetements homme",
        "url": "https://sn.coinafrique.com/categorie/vetements-homme",
        "type": "habits",
    },
    "chaussures-homme": {
        "label": "Chaussures homme",
        "url": "https://sn.coinafrique.com/categorie/chaussures-homme",
        "type": "chaussures",
    },
    "vetements-enfants": {
        "label": "Vetements enfants",
        "url": "https://sn.coinafrique.com/categorie/vetements-enfants",
        "type": "habits",
    },
    "chaussures-enfants": {
        "label": "Chaussures enfants",
        "url": "https://sn.coinafrique.com/categorie/chaussures-enfants",
        "type": "chaussures",
    },
}


# Ajoute le numero de page dans l'URL.
def build_page_url(base_url: str, page: int) -> str:
    if page <= 1:
        return base_url
    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query))
    query["page"] = str(page)
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))


# Recupere le HTML d'une page.
def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


# Parse les cartes d'annonces.
def parse_listings(html: str, item_type: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.card.ad__card")
    records: List[Dict[str, str]] = []

    for card in cards:
        price_el = card.select_one("p.ad__card-price a")
        location_el = card.select_one("p.ad__card-location span")
        image_el = card.select_one("img.ad__card-img")

        price_text = price_el.get_text(strip=True) if price_el else ""
        location_text = location_el.get_text(strip=True) if location_el else ""
        image_src = image_el.get("src", "") if image_el else ""

        records.append(
            {
                "type": item_type,
                "prix": price_text,
                "adresse": location_text,
                "image_lien": image_src,
            }
        )

    return records


# Scrape plusieurs pages d'une categorie.
def scrape_category(
    base_url: str,
    item_type: str,
    pages: int = 1,
    delay_seconds: float = 0.6,
) -> List[Dict[str, str]]:
    pages = max(1, pages)
    results: List[Dict[str, str]] = []
    for page in range(1, pages + 1):
        url = build_page_url(base_url, page)
        html = fetch_html(url)
        results.extend(parse_listings(html, item_type))
        if page < pages:
            time.sleep(delay_seconds)
    return results


# Nettoie les espaces multiples.
def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


# Convertit un prix texte en entier.
def clean_price(price_text: str) -> Optional[int]:
    if not price_text:
        return None
    lowered = price_text.lower()
    if "prix sur demande" in lowered or "sur demande" in lowered:
        return None
    digits = re.sub(r"[^\d]", "", price_text)
    return int(digits) if digits else None


# Nettoie les enregistrements bruts.
def clean_records(records: Iterable[Dict[str, str]]) -> List[Dict[str, Optional[str]]]:
    cleaned: List[Dict[str, Optional[str]]] = []
    for row in records:
        raw_price = normalize_whitespace(str(row.get("prix", "")))
        categorie = normalize_whitespace(str(row.get("categorie", ""))) or None
        cleaned.append(
            {
                "type": normalize_whitespace(str(row.get("type", ""))).lower() or None,
                "prix_brut": raw_price or None,
                "prix": clean_price(raw_price),
                "adresse": normalize_whitespace(str(row.get("adresse", ""))) or None,
                "image_lien": normalize_whitespace(str(row.get("image_lien", "")))
                or None,
                "categorie": categorie,
            }
        )
    return cleaned


# Supprime les doublons simples.
def dedupe_records(records: Iterable[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    seen = set()
    unique: List[Dict[str, Optional[str]]] = []
    for row in records:
        key = (
            row.get("type"),
            row.get("prix_brut") or row.get("prix"),
            row.get("adresse"),
            row.get("image_lien"),
            row.get("categorie"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique
