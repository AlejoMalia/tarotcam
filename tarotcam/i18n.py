"""Bilingual support (English by default, Spanish optional).

The engine always reasons over canonical Spanish identifiers (elements, suits, themes, planets, signs), so a
reading is identical in both languages; only the displayed text changes. Switch at runtime with set_lang().
"""
from __future__ import annotations

LANGS = ("en", "es")
_lang = "en"

TERMS = {
    # elements
    "Fuego": "Fire", "Agua": "Water", "Aire": "Air", "Tierra": "Earth",
    # suits
    "Bastos": "Wands", "Copas": "Cups", "Espadas": "Swords", "Oros": "Pentacles",
    # court ranks
    "Sota": "Page", "Caballero": "Knight", "Reina": "Queen", "Rey": "King",
    # planets
    "Sol": "Sun", "Luna": "Moon", "Mercurio": "Mercury", "Venus": "Venus", "Marte": "Mars", "Júpiter": "Jupiter",
    "Saturno": "Saturn", "Urano": "Uranus", "Neptuno": "Neptune", "Plutón": "Pluto",
    # zodiac
    "Aries": "Aries", "Tauro": "Taurus", "Géminis": "Gemini", "Cáncer": "Cancer", "Leo": "Leo", "Virgo": "Virgo",
    "Libra": "Libra", "Escorpio": "Scorpio", "Sagitario": "Sagittarius", "Capricornio": "Capricorn",
    "Acuario": "Aquarius", "Piscis": "Pisces",
}


def set_lang(lang: str) -> None:
    global _lang
    if lang not in LANGS:
        raise ValueError(f"lang must be one of {LANGS}")
    _lang = lang


def lang() -> str:
    return _lang


def toggle() -> str:
    set_lang("es" if _lang == "en" else "en")
    return _lang


def L(en: str, es: str) -> str:
    """Pick the string for the current language."""
    return en if _lang == "en" else es


def term(es: str) -> str:
    """Translate a canonical (Spanish) identifier for display."""
    return es if _lang == "es" else TERMS.get(es, es)


def card_name(card: dict) -> str:
    return card[_lang]


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def join_and(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + L(" and ", " y ") + parts[-1]
