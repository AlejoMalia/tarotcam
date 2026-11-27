#!/usr/bin/env python3
"""Descarga la baraja Rider-Waite-Smith (1909, dominio público) de Wikimedia Commons
a deck/, en miniaturas de 400 px de ancho. Idempotente: salta lo ya descargado."""
import sys
import time
import urllib.request
from pathlib import Path

from tarotcam import paths
from tarotcam.carddata.cards import CARDS

DECK = paths.RWS_DECK
URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=400"


def main():
    DECK.mkdir(parents=True, exist_ok=True)
    fails = []
    for c in CARDS:
        dest = DECK / f"{c['id']:02d}.jpg"
        if dest.exists() and dest.stat().st_size > 10_000:
            continue
        req = urllib.request.Request(URL.format(c["commons"]),
                                     headers={"User-Agent": "tarot-reader/0.1"})
        for intento in range(6):
            try:
                dest.write_bytes(urllib.request.urlopen(req, timeout=30).read())
                print("ok ", dest.name, c["commons"])
                break
            except Exception as e:
                if intento == 5:
                    fails.append((c["commons"], str(e)))
                    print("FAILED", c["commons"], e)
                else:
                    time.sleep(8 * (intento + 1))  # espera creciente ante 429
        time.sleep(2)
    print(f"{len(list(DECK.glob('*.jpg')))}/78 in {DECK}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
