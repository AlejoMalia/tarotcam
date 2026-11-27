"""De imagen simulada a lectura completa: 3 filas (pasado/presente/futuro) y cruz."""
from tarotcam import i18n
i18n.set_lang("es")  # estas comprobaciones están escritas sobre los textos en español

import sys
from pathlib import Path
import cv2, numpy as np
from tarotcam.vision.recognizer import Deck, GlobalScanner
from tarotcam.vision.tracker import Table
from tarotcam.engine.spreads import analyze
from tarotcam.interface.ui import render
from tests.sim import render as R, DECK_DIR

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
gs = GlobalScanner(Deck(DECK_DIR))

def run(name, cards, slots, h=150):
    table = Table(gs, threaded=False)
    f = R(cards, np.random.default_rng(4), card_h=(h, h), slots=slots, card_seed=900, rot=6)[0]
    for _ in range(3): table.update(f)
    lay = analyze(table.spread())
    print(f"{name}: {lay.name}")
    for s in lay.slots: print(f"   {s.role:42s} id={s.track.card_id} {'(revés)' if s.track.reversed else ''}")
    cv2.imwrite(str(out / f"e2e_{name}.png"), render(f, table, name))

# 3 filas: arriba=Torre(16), centro=Colgado(12)+Dos de Copas(37), abajo=Sol(19)
run("filas3", [(16, False), (12, False), (37, False), (19, False)], [(320, 70), (225, 240), (415, 240), (320, 410)], h=200)
# cruz: centro Emperatriz(3); arriba Estrella(17), abajo Luna(18), izq Muerte(13), der Sol(19)
run("cruz", [(10, False), (7, False), (16, True), (13, False), (19, False)], [(320, 240), (320, 78), (320, 402), (150, 240), (490, 240)], h=155)
