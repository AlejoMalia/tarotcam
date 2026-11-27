#!/usr/bin/env python3
"""Download reference card images from Wikimedia Commons (330 px wide) into data/decks/. Skips existing files.

  python -m tarotcam.tools.download_deck                     Rider-Waite-Smith (1909, public domain), ~16 MB
  python -m tarotcam.tools.download_deck --deck marseille    two Marseille decks, ~16 MB:
        CBD Tarot de Marseille by Yoav Ben-Dov (CC BY 3.0) and Jean Dodal, c. 1701-1715 (public domain, BnF)
  python -m tarotcam.tools.download_deck --deck all
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

from tarotcam import paths
from tarotcam.carddata import decks
from tarotcam.carddata.cards import CARDS

API = "https://commons.wikimedia.org/w/api.php?"
WIDTH = 330                                        # tamaño estándar de miniatura: servido desde caché
UA = {"User-Agent": "tarotcam/0.1"}


def jobs(system: str):
    if system == "rws":
        for c in CARDS:
            yield paths.RWS_DECK / f"{c['id']:02d}.jpg", c["commons"]
    else:
        for source, folder in zip(("cbd", "dodal"), decks.FOLDERS["marseille"]):
            for c in CARDS:
                yield folder / f"{c['id']:02d}.jpg", decks.commons_name(source, c["id"])


def _get(url, attempts=5) -> bytes:
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
        except Exception:                              # 429 o red: esperar y reintentar
            if attempt == attempts - 1:
                raise
            time.sleep(3 * (attempt + 1))


def thumb_urls(names: list[str]) -> dict[str, str]:
    """Nombre de archivo -> URL de la miniatura (consultas de 50 en 50)."""
    out = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        query = urllib.parse.urlencode(dict(action="query", format="json", prop="imageinfo", iiprop="url",
                                            iiurlwidth=WIDTH, titles="|".join("File:" + n for n in batch)))
        data = json.loads(_get(API + query))["query"]
        renamed = {n["to"]: n["from"] for n in data.get("normalized", [])}
        for page in data["pages"].values():
            title = renamed.get(page["title"], page["title"])[len("File:"):]
            if "imageinfo" in page:
                out[title] = page["imageinfo"][0]["thumburl"]
    return out


def fetch(dest, url) -> bool:
    try:
        data = _get(url)
        if not data.startswith((b"\xff\xd8", b"\x89PNG")):
            raise ValueError("not an image")
        dest.write_bytes(data)
        return True
    except Exception as e:
        print("FAILED", dest.name, e, flush=True)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deck", choices=[*decks.SYSTEMS, "all"], default="rws")
    a = ap.parse_args()
    systems = decks.SYSTEMS if a.deck == "all" else [a.deck]
    failed = 0
    for system in systems:
        todo = [(d, n) for d, n in jobs(system) if not (d.exists() and d.stat().st_size > 8_000)]
        urls = thumb_urls([n for _, n in todo])
        for folder in {d.parent for d, _ in todo}:
            folder.mkdir(parents=True, exist_ok=True)
        for dest, name in todo:                        # de una en una, con pausa: Commons limita las ráfagas
            if name in urls and fetch(dest, urls[name]):
                print("ok ", dest.parent.name, dest.name, flush=True)
            else:
                failed += 1
            time.sleep(0.3)
        for folder in decks.FOLDERS[system]:
            print(f"{len(list(folder.glob('*.jpg')))}/78 in {folder}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
