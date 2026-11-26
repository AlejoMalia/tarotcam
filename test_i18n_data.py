"""Shared fixtures for the language and narrative tests."""
import re

import numpy as np

from tracker import Track

SPANISH = re.compile(r"[áéíóúñ¿¡]|\b(el|la|los|las|un|una|de|del|y|con|que|por|para|su|se|al|carta|cartas|revés|derecho)\b", re.I)


def tr(cid, cx, cy, ang, rev, seq):
    c = np.float32([[-35, -60], [35, -60], [35, 60], [-35, 60]])
    a = np.deg2rad(ang)
    R = np.float32([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return Track(cid, c @ R.T + np.float32([cx, cy]), rev, seq=seq)


GEOMETRY = [
    [(320, 240, 0)], [(200, 240, 0), (440, 240, 0)], [(320, 80, 0), (320, 240, 0), (320, 400, 0)],
    [(150, 240, 0), (300, 240, 0), (450, 240, 0)], [(200, 120, 0), (400, 120, 0), (200, 360, 0), (400, 360, 0)],
    [(320, 240, 0), (320, 100, 0), (320, 380, 0), (190, 240, 0), (450, 240, 0)],
    [(250, 240, 0), (250, 240, 90), (250, 370, 0), (140, 240, 0), (250, 110, 0), (360, 240, 0),
     (500, 370, 0), (500, 270, 0), (500, 170, 0), (500, 70, 0)],
    [(70 + 85 * i, [120, 220, 310, 340, 310, 220, 120][i], 0) for i in range(7)],
    [(40 + 45 * i, 100 + 60 * (i % 4), 0) for i in range(14)],
]
