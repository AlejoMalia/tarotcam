"""Recognition with only part of the card visible (the rest covered by table), plus false-positive checks."""
import sys
import time

import cv2
import numpy as np

from tests import sim
from tarotcam.vision.recognizer import Deck, GlobalScanner

SHAPES = ("top", "bottom", "left", "right", "corner")


def render_partial(cid, rev, fraction, shape, rng, height=(280, 340)):
    """Compone solo una región de la carta (fraction de su área) sobre la mesa."""
    ref = cv2.imread(str(sim.DECK_DIR / f"{cid:02d}.jpg"))
    if rev:
        ref = cv2.rotate(ref, cv2.ROTATE_180)
    h0, w0 = ref.shape[:2]
    mask = np.zeros((h0, w0), np.float32)
    if shape in ("top", "bottom"):
        k = int(h0 * fraction)
        mask[:k] = 1
        if shape == "bottom":
            mask = mask[::-1].copy()
    elif shape in ("left", "right"):
        k = int(w0 * fraction)
        mask[:, :k] = 1
        if shape == "right":
            mask = mask[:, ::-1].copy()
    else:
        side = np.sqrt(fraction)
        mask[:int(h0 * side), :int(w0 * side)] = 1
        if rng.random() < .5:
            mask = mask[:, ::-1].copy()
        if rng.random() < .5:
            mask = mask[::-1].copy()
    s = rng.uniform(*height) / h0
    a = np.deg2rad(rng.uniform(-25, 25))
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]], np.float32) * s
    ys, xs = np.nonzero(mask)
    visible_centre = np.float32([xs.mean(), ys.mean()])
    t = np.float32([320, 240]) - R @ visible_centre                  # la parte visible queda en el encuadre
    M = np.float32(np.hstack([R, t[:, None]]))
    card = cv2.warpAffine(ref.astype(np.float32), M, (sim.W, sim.H), flags=cv2.INTER_AREA)
    m = cv2.GaussianBlur(cv2.warpAffine(mask, M, (sim.W, sim.H)), (0, 0), 0.7)[..., None]
    img = sim._table(rng) * (1 - m) + card * m
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.5, 0.9)) + rng.normal(0, rng.uniform(2, 6), img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def evaluate(scanner, fraction, trials, seed=1):
    rng = np.random.default_rng(seed + int(fraction * 100))
    ok = wrong = miss = 0
    elapsed = 0.0
    estimates = []
    for k in range(trials):
        cid, rev = int(rng.integers(78)), bool(rng.integers(2))
        frame = render_partial(cid, rev, fraction, SHAPES[k % len(SHAPES)], rng)
        t = time.time()
        found = scanner.scan(frame)
        elapsed += time.time() - t
        hit = any(f.card_id == cid and f.reversed == rev for f in found)
        estimates += [f.visible for f in found if f.card_id == cid]
        bad = sum(f.card_id != cid for f in found)
        ok += hit
        wrong += bad
        miss += not hit
    print(f"visible {fraction:4.0%}: {ok}/{trials} correct ({ok / trials:4.0%})  false cards={wrong}  "
          f"{1000 * elapsed / trials:.0f} ms/scan  (estimated visible: {np.mean(estimates or [0]):.0%})", flush=True)
    return ok / trials, wrong


def stacked(scanner, shown, trials=60, seed=5):
    """Dos cartas apiladas: la de abajo asoma solo una franja (shown) por debajo de la de arriba."""
    rng = np.random.default_rng(seed)
    both = bottom = wrong = 0
    for _ in range(trials):
        a, b = (int(x) for x in rng.choice(78, 2, replace=False))
        img = sim._table(rng)
        ch = rng.uniform(300, 340)
        cw = ch * 0.58
        x0 = 320 - cw * (1 + shown) / 2
        for cid, x in ((a, x0), (b, x0 + cw * shown)):
            ref = cv2.resize(cv2.imread(str(sim.DECK_DIR / f"{cid:02d}.jpg")), (int(cw), int(ch)),
                             interpolation=cv2.INTER_AREA)
            y = int(240 - ch / 2)
            img[y:y + ref.shape[0], int(x):int(x) + ref.shape[1]] = ref
        frame = np.clip(cv2.GaussianBlur(img, (0, 0), .7) + rng.normal(0, 4, img.shape), 0, 255).astype(np.uint8)
        ids = {f.card_id for f in scanner.scan(frame)}
        both += {a, b} <= ids
        bottom += a in ids
        wrong += len(ids - {a, b})
    print(f"stacked, lower card shows {shown:4.0%}: lower found {bottom}/{trials} ({bottom / trials:4.0%}), "
          f"both {both}/{trials}, false cards={wrong}", flush=True)
    return wrong


def false_positives(scanner, frames=60, seed=9):
    rng = np.random.default_rng(seed)
    fp = 0
    for k in range(frames):
        img = np.clip(sim._table(rng) + rng.normal(0, 8, (sim.H, sim.W, 3)), 0, 255).astype(np.uint8)
        for _ in range(int(rng.integers(0, 12))):                      # objetos: rectángulos, círculos, texto
            c = tuple(int(v) for v in rng.integers(0, 255, 3))
            x, y = int(rng.integers(0, 560)), int(rng.integers(0, 400))
            if rng.random() < .4:
                cv2.rectangle(img, (x, y), (x + int(rng.integers(20, 200)), y + int(rng.integers(20, 200))), c, -1)
            elif rng.random() < .5:
                cv2.circle(img, (x, y), int(rng.integers(10, 80)), c, int(rng.integers(1, 8)))
            else:
                cv2.putText(img, "THE TAROT 1909", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.1, c, 2)
        fp += len(scanner.scan(img))
    print(f"scenes without cards: {fp} false cards in {frames} frames", flush=True)
    return fp


if __name__ == "__main__":
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 78
    sc = GlobalScanner(Deck(sim.DECK_DIR))
    for fraction in (0.5, 0.3, 0.2, 0.15, 0.1):
        evaluate(sc, fraction, trials)
    for shown in (0.5, 0.3, 0.2):
        stacked(sc, shown)
    false_positives(sc, 200)
    print("\nOK: partial_test")
