"""Unified access to the three open datasets fetched by fetch_datasets.py. Everything is optional:
without datasets/ the app works with its built-in data. Their texts are English only."""
from __future__ import annotations

import json
import re
from pathlib import Path

from tarotcam import paths
from tarotcam.carddata.cards import CARDS

ROOT = paths.DATASETS
AREAS = ("love", "career", "money", "spiritual")


def _norm(name: str) -> str:
    n = name.lower().replace("judgment", "judgement").replace("coins", "pentacles").replace("disks", "pentacles")
    n = re.sub(r"^the ", "", n.strip())
    return re.sub(r"[^a-z ]", "", n)


_IDS = {_norm(c["en"]): c["id"] for c in CARDS}


def _read(path: Path):
    try:
        text = path.read_text()
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        return json.loads(text)
    except (OSError, ValueError):
        return []


def _load() -> dict[int, dict]:
    out: dict[int, dict] = {}

    def entries(data):
        if isinstance(data, dict):
            data = data.get("cards", data)
        return list(data.values()) if isinstance(data, dict) else data

    for source, filename in (("tarotoo", "cards.json"), ("smallcat", "cards.json"), ("startarot", "cards.jsonl")):
        for e in entries(_read(ROOT / source / filename)):
            cid = _IDS.get(_norm(str(e.get("name", ""))))
            if cid is not None:
                out.setdefault(cid, {})[source] = e
    return out


DATA = _load()


def available() -> bool:
    return bool(DATA)


def area_text(card_id: int, area: str, reversed_: bool = False) -> str:
    """Best English sentence/phrase list for an area of life ('love', 'career', 'money', 'spiritual')."""
    e = DATA.get(card_id, {})
    side = "reversed" if reversed_ else "upright"
    small = e.get("smallcat", {}).get(side, {})
    value = small.get({"money": "finance"}.get(area, area))           # full sentences first
    if not value:
        value = e.get("tarotoo", {}).get(area + ("_reversed" if reversed_ else ""))
    return str(value or "").strip()


def yes_no(card_id: int, reversed_: bool = False) -> str:
    v = DATA.get(card_id, {}).get("tarotoo", {}).get("yes_no" + ("_reversed" if reversed_ else ""), "")
    return str(v).lower()


def golden_dawn_title(card_id: int) -> str:
    return DATA.get(card_id, {}).get("startarot", {}).get("correspondence", {}).get("title", "") or ""


def waite(card_id: int, reversed_: bool = False) -> str:
    return DATA.get(card_id, {}).get("startarot", {}).get("divinatory_meanings", {}).get(
        "reversed" if reversed_ else "upright", "") or ""


def correspondence(card_id: int) -> dict:
    return DATA.get(card_id, {}).get("startarot", {}).get("correspondence", {})
