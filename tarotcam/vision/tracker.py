"""Mesa de cartas: estado de la lectura a partir de escaneos globales.

La identidad de una carta ES su id (una baraja no repite cartas), así que una carta no puede
aparecer dos veces ni "teletransportarse": cada id tiene como mucho una pista.

- Se confirma tras verse en CONFIRM escaneos seguidos; entra en la lectura por orden de llegada.
- Se retira tras MISS_MAX escaneos seguidos sin verse (tapada o fuera de la mesa).
- Si se gira 180°, se actualiza la orientación tras FLIP_AFTER escaneos coherentes.
El escaneo (caro) corre en un hilo aparte para que el vídeo no se congele.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

import numpy as np

from tarotcam.vision.recognizer import Found, GlobalScanner

CONFIRM = 2        # escaneos seguidos para confirmar
CONFIRM_PARTIAL = 3  # más exigente si se ve muy poco de la carta
LITTLE_VISIBLE = 0.2
MISS_MAX = 6       # escaneos seguidos sin verla antes de retirarla
FLIP_AFTER = 2     # escaneos coherentes para aceptar un giro de 180°


@dataclass
class Track:
    card_id: int
    quad: np.ndarray
    reversed: bool
    visible: float = 1.0            # fracción aproximada de la carta que se ve
    inliers: int = 0
    hits: int = 0
    missing: int = 0
    seq: int | None = None
    flips: int = 0

    @property
    def confirmed(self) -> bool:
        return self.seq is not None

    @property
    def center(self):
        return self.quad.mean(axis=0)


class Table:
    def __init__(self, scanner: GlobalScanner, spread_mode: str = "auto", threaded: bool = True):
        self.scanner = scanner
        self.detail = False                     # False: narración · True: análisis por secciones
        self.focus = "general"                  # ver narrator.FOCI
        self.writer = None                      # llm.LocalWriter opcional
        self.use_writer = False
        self.chart = None                       # natal.Chart opcional
        self.use_chart = False
        self.spread_mode = spread_mode           # ver spreads.MODES
        self.threaded = threaded
        self.tracks: dict[int, Track] = {}
        self._seq = 0
        self.scans = 0
        self.scan_ms = 0.0
        self._lock = threading.Lock()
        self._frame = None
        self._results: list[list[Found]] = []
        self._stop = threading.Event()
        self._wake = threading.Event()
        if threaded:
            threading.Thread(target=self._worker, daemon=True).start()

    # --- escaneo en segundo plano -------------------------------------------------
    def _worker(self):
        import time
        while not self._stop.is_set():
            self._wake.wait(0.5)
            self._wake.clear()
            with self._lock:
                frame, self._frame = self._frame, None
            if frame is None:
                continue
            t = time.time()
            found = self.scanner.scan(frame)
            with self._lock:
                self.scan_ms = 1000 * (time.time() - t)
                self._results.append(found)

    def close(self):
        self._stop.set()
        self._wake.set()

    def update(self, frame_bgr: np.ndarray) -> None:
        """Ofrece un fotograma e integra los escaneos terminados."""
        if self.threaded:
            with self._lock:
                self._frame = frame_bgr
                results, self._results = self._results, []
            self._wake.set()
        else:
            results = [self.scanner.scan(frame_bgr)]
        for found in results:
            self._integrate(found)

    def reset(self):
        self.tracks.clear()
        self._seq = 0

    # --- estado ---------------------------------------------------------------------
    def _integrate(self, found: list[Found]) -> None:
        self.scans += 1
        seen = set()
        for f in found:
            if f.card_id in seen:                      # nunca dos veces la misma carta
                continue
            seen.add(f.card_id)
            t = self.tracks.get(f.card_id)
            if t is None:
                t = self.tracks[f.card_id] = Track(f.card_id, f.quad, f.reversed)
            t.quad, t.inliers, t.missing = f.quad, f.inliers, 0
            t.visible = f.visible
            t.hits += 1
            if t.confirmed:
                if f.reversed != t.reversed:
                    t.flips += 1
                    if t.flips >= FLIP_AFTER:
                        t.reversed, t.flips = f.reversed, 0
                else:
                    t.flips = 0
            else:
                t.reversed = f.reversed
                if t.hits >= (CONFIRM_PARTIAL if t.visible < LITTLE_VISIBLE else CONFIRM):
                    self._seq += 1
                    t.seq = self._seq
        for cid in list(self.tracks):
            if cid in seen:
                continue
            t = self.tracks[cid]
            t.missing += 1
            if not t.confirmed:
                t.hits = 0
                if t.missing >= 2:
                    del self.tracks[cid]
            elif t.missing > MISS_MAX:
                del self.tracks[cid]

    def spread(self) -> list[Track]:
        """Cartas confirmadas y presentes, por orden de llegada (la disposición la decide spreads.analyze)."""
        return sorted((t for t in self.tracks.values() if t.confirmed), key=lambda t: t.seq)
