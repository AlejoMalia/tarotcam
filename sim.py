"""Prueba de recuperación: fotogramas sintéticos con el mismo tipo de degradación que la PS3 Eye
(VGA, ruido, desenfoque, perspectiva, giro de 180°) y medición de aciertos.

Limitación honesta: las cartas simuladas salen de las mismas imágenes de la baraja, así que
esto mide el pipeline (detección + SIFT + orientación), no el brillo, reflejos y papel de tu baraja real.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from recognizer import Deck, find_cards

DECK_DIR = Path(__file__).parent / "deck"
W, H = 640, 480


def _table(rng):
    base = np.array(rng.choice([[40, 70, 40], [30, 30, 90], [60, 60, 60], [20, 40, 70], [90, 80, 70]]),
                    np.float32)
    img = np.ones((H, W, 3), np.float32) * base
    img += rng.normal(0, 6, (H, W, 3))
    img = cv2.GaussianBlur(img, (0, 0), 3)
    return img


def render(cards, rng, card_h=(210, 290), rot=30, tilt=0.08, blur=(0.6, 1.4), noise=(4, 12),
           slots=None, card_seed=None):
    """cards: lista de (card_id, reversed). Devuelve frame BGR uint8 y centros verdaderos."""
    img = _table(rng)
    n = len(cards)
    custom = slots is not None
    slots = slots or {1: [(W / 2, H / 2)], 2: [(W * .3, H / 2), (W * .7, H / 2)],
             3: [(W * .2, H / 2), (W * .5, H / 2), (W * .8, H / 2)]}.get(
        n, [((i % 4 + .5) * W / 4, (i // 4 + .5) * H / 2) for i in range(n)])
    truth = []
    for (cid, rev), (cx, cy) in zip(cards, slots):
        crng = np.random.default_rng(card_seed + cid) if card_seed is not None else rng
        ref = cv2.imread(str(DECK_DIR / f"{cid:02d}.jpg"))
        h0, w0 = ref.shape[:2]
        if rev:
            ref = cv2.rotate(ref, cv2.ROTATE_180)
        ch = crng.uniform(*card_h) * (1 if (n == 1 or custom) else 0.75 if n == 3 else 0.9)
        s = ch / h0
        cw = w0 * s
        a = np.deg2rad(crng.uniform(-rot, rot))
        corners = np.float32([[-cw / 2, -ch / 2], [cw / 2, -ch / 2], [cw / 2, ch / 2], [-cw / 2, ch / 2]])
        corners *= 1 + crng.uniform(-tilt, tilt, (4, 2)) * 0.5     # perspectiva leve
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]], np.float32)
        dst = corners @ R.T + np.float32([cx, cy])
        src = np.float32([[0, 0], [w0, 0], [w0, h0], [0, h0]])
        M = cv2.getPerspectiveTransform(src, dst)
        card = ref.astype(np.float32)
        warped = cv2.warpPerspective(card, M, (W, H), flags=cv2.INTER_AREA)
        mask = cv2.warpPerspective(np.ones((h0, w0), np.float32), M, (W, H))[..., None]
        mask = cv2.GaussianBlur(mask, (0, 0), 0.8)[..., None] if mask.ndim == 2 else mask
        img = img * (1 - mask) + warped * mask
        truth.append((cid, rev, (cx, cy)))
    # iluminación desigual, tinte naranja de la PS3 Eye, desenfoque y ruido de sensor
    gx = np.linspace(rng.uniform(.8, 1.0), rng.uniform(.9, 1.1), W)[None, :, None]
    img = img * gx * np.float32([rng.uniform(.85, .95), 1.0, rng.uniform(1.0, 1.12)])
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(*blur))
    img += rng.normal(0, rng.uniform(*noise), img.shape)
    return np.clip(img, 0, 255).astype(np.uint8), truth


def evaluate(deck, trials_per_card=2, seed=1, verbose=False):
    rng = np.random.default_rng(seed)
    ok = wrong = missed = ori_bad = 0
    wrongs = []
    for cid in range(78):
        for _ in range(trials_per_card):
            rev = bool(rng.integers(2))
            frame, _ = render([(cid, rev)], rng)
            dets = find_cards(frame)
            res = None
            for d in dets:
                m = deck.identify(d)
                if m:
                    res = m
                    break
            if res is None:
                missed += 1
                if verbose:
                    print(f"  sin lectura: carta {cid} (dets={len(dets)})")
            elif res.card_id != cid:
                wrong += 1
                wrongs.append((cid, res.card_id))
            else:
                ok += 1
                ori_bad += res.reversed != rev
    total = ok + wrong + missed
    print(f"Una carta: {ok}/{total} correctas, {wrong} erróneas, {missed} sin lectura; "
          f"orientación fallida en {ori_bad} de {ok} acertadas")
    if wrongs:
        print("  confusiones (real->leída):", wrongs[:10])
    return ok, wrong, missed


def evaluate_multi(deck, n_frames=30, seed=2):
    rng = np.random.default_rng(seed)
    hits = tot = false_pos = 0
    for _ in range(n_frames):
        k = int(rng.integers(2, 4))
        ids = [int(x) for x in rng.choice(78, k, replace=False)]
        cards = [(i, bool(rng.integers(2))) for i in ids]
        frame, _ = render(cards, rng)
        found = {}
        for d in find_cards(frame):
            m = deck.identify(d)
            if m:
                found[m.card_id] = m.reversed
        for cid, rev in cards:
            tot += 1
            hits += found.get(cid) == rev
        false_pos += sum(1 for c in found if c not in ids)
    print(f"Varias cartas (2-3): {hits}/{tot} con carta y orientación correctas; "
          f"{false_pos} lecturas de cartas que no estaban")


def evaluate_empty(deck, n=40, seed=3):
    rng = np.random.default_rng(seed)
    fp = 0
    for _ in range(n):
        frame = np.clip(_table(rng) + rng.normal(0, 8, (H, W, 3)), 0, 255).astype(np.uint8)
        # objetos que no son cartas: rectángulos de colores y una mano/ruido
        if rng.random() < .5:
            x, y = int(rng.integers(50, 300)), int(rng.integers(50, 200))
            cv2.rectangle(frame, (x, y), (x + int(rng.integers(80, 250)), y + int(rng.integers(80, 250))),
                          tuple(int(v) for v in rng.integers(0, 255, 3)), -1)
        for d in find_cards(frame):
            fp += deck.identify(d) is not None
    print(f"Mesa sin cartas: {fp} falsos positivos en {n} fotogramas")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2)
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    deck = Deck(DECK_DIR)
    evaluate(deck, a.trials, verbose=a.v)
    evaluate_multi(deck)
    evaluate_empty(deck)
