"""Prueba de recuperación: fotogramas sintéticos con el mismo tipo de degradación que la PS3 Eye
(VGA, ruido, desenfoque, perspectiva, giro de 180°) y medición de aciertos.

Limitación honesta: las cartas simuladas salen de las mismas imágenes de la baraja, así que
esto mide el pipeline (detección + SIFT + orientación), no el brillo, reflejos y papel de tu baraja real.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from tarotcam import paths

DECK_DIR = paths.RWS_DECK
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
