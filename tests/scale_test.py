"""Recuperación con 1..N cartas a la vez (separadas, pegadas y solapadas)."""
import sys, time
import numpy as np, cv2
from tests import sim
from tarotcam.vision.recognizer import Deck, GlobalScanner

def layout(n, rng, overlap):
    cols = int(np.ceil(np.sqrt(n * sim.W / sim.H))); rows = int(np.ceil(n / cols))
    cw, chh = sim.W / cols, sim.H / rows
    slots = [((i % cols + .5) * cw + rng.uniform(-6, 6), (i // cols + .5) * chh + rng.uniform(-6, 6)) for i in range(n)]
    h = chh * (1.12 if overlap else 0.92)          # >1 de la celda = se solapan
    return slots, h

def run(scan, n, overlap, frames=8, seed=0):
    rng = np.random.default_rng(seed + n)
    hit = tot = fp = 0; t = 0
    for _ in range(frames):
        ids = [int(x) for x in rng.choice(78, n, replace=False)]
        cards = [(i, bool(rng.integers(2))) for i in ids]
        slots, h = layout(n, rng, overlap)
        f, _ = sim.render(cards, rng, card_h=(h * .95, h), slots=slots, rot=12)
        t0 = time.time(); found = {x.card_id: x.reversed for x in scan(f)}; t += time.time() - t0
        for cid, rev in cards:
            tot += 1; hit += found.get(cid) == rev
        fp += sum(1 for c in found if c not in ids)
    print(f"n={n:2d} {'solapadas' if overlap else 'separadas'}: {hit}/{tot} ({100*hit/tot:.0f}%)  falsos={fp}  {1000*t/frames:.0f} ms/escaneo", flush=True)

if __name__ == "__main__":
    deck = Deck(sim.DECK_DIR); gs = GlobalScanner(deck)
    for n in (1, 2, 3, 4, 6, 8, 10, 12):
        run(gs.scan, n, False)
    for n in (3, 6, 8):
        run(gs.scan, n, True)
