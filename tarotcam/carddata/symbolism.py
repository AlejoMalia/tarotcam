"""Símbolos que se repiten entre arcanos mayores (los 22 con símbolos nombrados en la base de conocimiento).
Las categorías agrupan símbolos del documento original (en inglés) y se explican en español."""
from __future__ import annotations

import re

from tarotcam import i18n
from tarotcam.carddata import knowledge

# clave: (regex sobre el nombre del símbolo en inglés, nombre ES, significado ES)
CATEGORIES = {
    "infinito": (r"infinit", "el infinito", "poder ilimitado y continuidad"),
    "flores": (r"rose|flower|wreath|laurel|wheat|field", "las flores y la cosecha", "pureza, vida y fertilidad"),
    "granada": (r"pomegranate", "las granadas", "fertilidad y semillas ocultas de sabiduría"),
    "luna": (r"moon", "la luna", "intuición, inconsciente y ciclos"),
    "sol": (r"\bsun\b|sunset", "el sol", "vitalidad, conciencia y ciclos de día y noche"),
    "estrellas": (r"\bstars?\b", "las estrellas", "guía, esperanza y conexión cósmica"),
    "agua": (r"water|cups?\b|crab", "el agua", "emociones, flujo e inconsciente"),
    "elementos": (r"element", "los cuatro elementos", "dominio de las fuerzas fundamentales"),
    "angel": (r"angel|trumpet", "el ángel", "mensaje y guía superior"),
    "esfinge": (r"sphinx|anubis|typhon", "la esfinge", "enigma y fuerzas opuestas en equilibrio"),
    "corona": (r"crown", "la corona", "autoridad y conciencia superior"),
    "animales": (r"\bdog|wolves|lion|horned|\bram", "los animales", "instinto y naturaleza animal"),
    "montana": (r"mountain|cliff|landscape", "la montaña", "ascenso, umbral y perspectiva"),
    "circulo": (r"ouroboros|wheel|cosmic|circle", "el círculo", "ciclos y totalidad"),
    "balanza": (r"sword|scales", "la espada y la balanza", "discernimiento y consecuencia"),
    "conocimiento": (r"veil|torah|keys|lantern|tree of knowledge", "el conocimiento oculto",
                     "lo que solo se revela con búsqueda interior"),
    "halo": (r"halo|ankh|suspension", "el halo y la suspensión", "iluminación a través de la entrega"),
    "ruptura": (r"lightning|falling|chains|pentagram", "las cadenas y la caída", "ataduras y su ruptura"),
}


def categories(card_id: int) -> set[str]:
    cats = set()
    for name in knowledge.symbol_names(card_id):
        for key, (rx, _, _) in CATEGORIES.items():
            if re.search(rx, name, re.I):
                cats.add(key)
    return cats


CATEGORIES_EN = {
    "infinito": ("infinity", "unlimited power and continuity"),
    "flores": ("flowers and harvest", "purity, life and fertility"),
    "granada": ("pomegranates", "fertility and hidden seeds of wisdom"),
    "luna": ("the moon", "intuition, the unconscious and cycles"),
    "sol": ("the sun", "vitality, awareness and the cycle of day and night"),
    "estrellas": ("stars", "guidance, hope and cosmic connection"),
    "agua": ("water", "emotion, flow and the unconscious"),
    "elementos": ("the four elements", "mastery of the fundamental forces"),
    "angel": ("the angel", "message and higher guidance"),
    "esfinge": ("the sphinx", "riddle and opposing forces held in balance"),
    "corona": ("the crown", "authority and higher awareness"),
    "animales": ("animals", "instinct and animal nature"),
    "montana": ("the mountain", "ascent, threshold and perspective"),
    "circulo": ("the circle", "cycles and wholeness"),
    "balanza": ("sword and scales", "discernment and consequence"),
    "conocimiento": ("hidden knowledge", "what is only revealed through inner search"),
    "halo": ("halo and suspension", "illumination through surrender"),
    "ruptura": ("chains and falling", "bonds and their breaking"),
}


def explain(key: str) -> tuple[str, str]:
    if i18n.lang() == "en":
        return CATEGORIES_EN[key]
    return CATEGORIES[key][1], CATEGORIES[key][2]
