"""Deck systems and their reference images.

A card keeps the same internal id in every system (Strength is 8 and Justice 11, as in Rider-Waite-Smith),
so the engine means the same thing by it; each system only changes the printed number, the names, the
meanings and which reference images are used to recognise it.
"""
from __future__ import annotations

from tarotcam import paths

SYSTEMS = ("rws", "marseille")
SYSTEM_NAMES = {"rws": ("Rider-Waite-Smith", "Rider-Waite-Smith"),
                "marseille": ("Tarot de Marseille", "Tarot de Marsella")}

# sistema -> carpetas con imágenes de referencia NN.jpg (NN = id interno)
FOLDERS = {
    "rws": [paths.RWS_DECK],
    "marseille": [paths.DECKS / "marseille-cbd", paths.DECKS / "marseille-dodal"],
}


def folders(system: str) -> list:
    """Carpetas disponibles (completas) del sistema."""
    return [f for f in FOLDERS[system] if len(list(f.glob("*.jpg"))) >= 78]


def reference_image(system: str, card_id: int):
    """Imagen para mostrar una carta (la de la primera carpeta disponible)."""
    available = folders(system) or FOLDERS[system]
    return available[0] / f"{card_id:02d}.jpg"


# ------------------------------------------------------------- Marsella: numeración y archivos de Commons
def marseille_number(card_id: int) -> int:
    """Número impreso en un arcano mayor de Marsella: la Justicia es VIII y la Fuerza XI."""
    return {11: 8, 8: 11}.get(card_id, card_id)


_SUIT_LETTER = {22: "B", 36: "C", 50: "E", 64: "D"}          # base del id interno -> letra en Commons


def commons_name(source: str, card_id: int) -> str:
    """Nombre de archivo en Wikimedia Commons. source: 'cbd' (Yoav Ben-Dov) o 'dodal' (Jean Dodal)."""
    prefix = {"cbd": "Ben-Dov", "dodal": "Jean_Dodal"}[source]
    if card_id < 22:
        major = "MA" if source == "cbd" else "M"
        return f"{prefix}_{major}{marseille_number(card_id):02d}.jpg"
    base = max(b for b in _SUIT_LETTER if b <= card_id)
    return f"{prefix}_{_SUIT_LETTER[base]}{card_id - base + 1:02d}.jpg"
