"""Acceso a la base de conocimiento (knowledge/kb.json, generada por build_knowledge.py).
Sin ella, todo funciona con los significados incluidos en cards.py."""
from __future__ import annotations

import json
from pathlib import Path
from tarotcam import paths

_KB_PATH = paths.KNOWLEDGE_FILE
try:
    KB: dict = json.loads(_KB_PATH.read_text())
except (OSError, ValueError):
    KB = {}


def available() -> bool:
    return bool(KB)


def keywords(card_id: int, reversed_: bool = False, lang: str = "es") -> list[str]:
    e = KB.get(str(card_id), {})
    return list(e.get(f"{lang}_{'rev' if reversed_ else 'up'}", []))


def symbol_names(card_id: int) -> list[str]:
    return [s["name"] for s in KB.get(str(card_id), {}).get("symbols", [])]
