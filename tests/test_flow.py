"""Entran y salen cartas (una carta duplicada incluida) y se comprueba la lectura en cada paso."""
from tarotcam import i18n
i18n.set_lang("es")  # estas comprobaciones están escritas sobre los textos en español

import sys
from pathlib import Path
import cv2, numpy as np
from tarotcam.vision.recognizer import Deck, GlobalScanner
from tarotcam.vision.tracker import Table
from tarotcam.interface.ui import render
from tests import sim
from tests.sim import render as R, _table, DECK_DIR, W, H

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
rng = np.random.default_rng(7)
table = Table(GlobalScanner(Deck(DECK_DIR)), threaded=False)
cards = {"Colgado": (12, False), "Dos Copas": (37, False), "Ermitano": (9, False), "Torre": (16, True),
         "Estrella": (17, False), "Sol": (19, False)}
slots = [(110, 130), (320, 130), (530, 130), (110, 350), (320, 350), (530, 350)]
slot = dict(zip(cards, slots))
steps = [("vacia", []), ("1", ["Colgado"]), ("2", ["Colgado", "Dos Copas"]), ("3", ["Colgado", "Dos Copas", "Ermitano"]),
         ("5", ["Colgado", "Dos Copas", "Ermitano", "Torre", "Estrella"]),
         ("6", list(cards)), ("sale_colgado", [k for k in cards if k != "Colgado"])]
for name, names in steps:
    cl = [cards[k] for k in names]
    base = R(cl, np.random.default_rng(11), card_h=(190, 190), slots=[slot[k] for k in names], card_seed=500, rot=10)[0] if cl else None
    for _ in range(9 if name.startswith('sale') else 3):
        f = base if base is not None else np.clip(_table(rng), 0, 255).astype(np.uint8)
        f = np.clip(f.astype(np.float32) + rng.normal(0, 3, f.shape), 0, 255).astype(np.uint8)
        table.update(f)
    got = [(t.card_id, t.reversed) for t in table.spread()]
    want = sorted(cards[k] for k in names)
    print(f"{name:13s} {'OK ' if sorted(got) == want and len(got) == len(set(c for c, _ in got)) else 'MAL'} -> {got}")
    cv2.imwrite(str(out / f"flow_{name}.png"), render(f, table, name))

# duplicado: la misma carta dos veces en la mesa => una sola lectura
dup = R([(12, False), (12, False)], np.random.default_rng(3), card_h=(190, 190), slots=[(160, 240), (480, 240)], card_seed=500)[0]
table.reset(); table.update(dup); table.update(dup)
print("duplicada x2  ->", [(t.card_id) for t in table.spread()], "(debe haber una sola)")
