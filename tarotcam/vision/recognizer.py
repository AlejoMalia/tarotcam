"""Recognition of every card in a frame, whole or partly hidden.

A Deck holds one or more reference images per card (several editions of the same system can be loaded at once).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

CARD_H = 410                       # alto canónico de cada plantilla (el ancho respeta la proporción de su baraja)


class Deck:
    """Plantillas de referencia: carpetas con NN.jpg (NN = id de carta)."""

    def __init__(self, folders):
        if isinstance(folders, (str, Path)):
            folders = [folders]
        if not folders:
            raise FileNotFoundError("No reference images. Run: python -m tarotcam.tools.download_deck")
        sift = cv2.SIFT_create(nfeatures=800, contrastThreshold=0.02)
        dense = cv2.SIFT_create(nfeatures=1600, contrastThreshold=0.008)
        self.card_ids: list[int] = []
        self.images: list[np.ndarray] = []
        self.refs_dense: list[tuple] = []
        self.refs_half: list[tuple] = []
        for folder in folders:
            for cid in range(78):
                path = Path(folder) / f"{cid:02d}.jpg"
                img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise FileNotFoundError(f"Missing {path}. Run: python -m tarotcam.tools.download_deck")
                width = round(CARD_H * img.shape[1] / img.shape[0])
                img = cv2.resize(img, (width, CARD_H), interpolation=cv2.INTER_AREA)
                self.card_ids.append(cid)
                self.images.append(img)
                kp, des = dense.detectAndCompute(img, None)        # cobertura densa: cualquier trozo tiene puntos
                self.refs_dense.append((np.float32([k.pt for k in kp]), des))
                # versión a media resolución: casa mejor con cartas pequeñas y borrosas
                half = cv2.resize(img, (width // 2, CARD_H // 2), interpolation=cv2.INTER_AREA)
                kp, des = sift.detectAndCompute(half, None)
                self.refs_half.append((np.float32([k.pt for k in kp]) * 2 if kp else np.zeros((0, 2), np.float32), des))


@dataclass
class Found:
    card_id: int
    reversed: bool
    inliers: int
    quad: np.ndarray               # 4x2 en la imagen original: esquinas (estimadas si la carta se ve en parte)
    visible: float = 1.0           # fracción aproximada de la carta que se ve
    score: float = 0.0

    @property
    def center(self):
        return self.quad.mean(axis=0)


BLOCK_W, BLOCK_H = 6, 10           # rejilla de verificación (60 bloques por carta)
NCC_MIN = 0.55                     # correlación mínima para dar un bloque por visible
MIN_BLOCKS_PARTIAL = 4             # ≈7 % de la carta como mínimo
NCC_STRONG = 0.62                  # calidad media exigida a los reconocimientos parciales


class GlobalScanner:
    """Busca TODAS las cartas a la vez en el fotograma, enteras o solo en parte.

    SIFT sobre el fotograma + índice FLANN con los descriptores de las 78 referencias (densos y a media
    resolución). Por cada carta candidata:
      1. homografía (carta bien visible); si no es plausible,
      2. semejanza (giro + escala + posición), estable aunque solo se vea un trozo;
      3. verificación fotométrica: la referencia se compara bloque a bloque con el fotograma en la pose
         estimada. Eso descarta falsos positivos y mide qué parte de la carta se ve.
    Una baraja no repite cartas, y dos cartas no pueden explicar los mismos píxeles.
    """

    def __init__(self, deck: Deck, upscale: float = 1.5, ratio: float = 0.78, min_inliers: int = 10,
                 min_partial: int = 6):
        self.deck, self.up, self.ratio = deck, upscale, ratio
        self.min_inliers, self.min_partial = min_inliers, min_partial
        self.qsift = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.012)
        des, owner, pts = [], [], []
        for refs in (deck.refs_dense, deck.refs_half):
            for tid, (p, d) in enumerate(refs):
                if d is None or len(d) == 0:
                    continue
                des.append(d)
                owner.append(np.full(len(d), tid, np.int32))
                pts.append(p)
        self.owner = np.concatenate(owner)
        self.ref_pts = np.concatenate(pts)
        self.flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=64))
        self.flann.add([np.concatenate(des).astype(np.float32)])
        self.flann.train()
        self.corners = [np.float32([[[0, 0]], [[i.shape[1], 0]], [[i.shape[1], CARD_H]], [[0, CARD_H]]])
                        for i in deck.images]
        self.card_of = np.int32(deck.card_ids)
        self.blurred = [cv2.GaussianBlur(i, (0, 0), 1.2).astype(np.float32) for i in deck.images]

    # ------------------------------------------------------------------ verificación
    def _verify_blocks(self, gray: np.ndarray, tid: int, H: np.ndarray):
        """-> (fracción visible, nº de bloques que coinciden, ncc media de esos bloques, centros en el fotograma)."""
        flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP                  # H: carta -> fotograma
        ref = self.blurred[tid]
        size = (ref.shape[1], CARD_H)
        seen = cv2.warpPerspective(gray, H, size, flags=flags)
        inside = cv2.warpPerspective(np.full(gray.shape, 255, np.uint8), H, size, flags=flags)
        seen = cv2.GaussianBlur(seen, (0, 0), 1.2).astype(np.float32)
        bw, bh = size[0] // BLOCK_W, CARD_H // BLOCK_H
        hits, scores, centres, textured = 0, [], [], 0
        for j in range(BLOCK_H):
            for i in range(BLOCK_W):
                sl = (slice(j * bh, (j + 1) * bh), slice(i * bw, (i + 1) * bw))
                r = ref[sl]
                rs = r.std()
                if rs < 9:                                    # cielo liso: no informa ni a favor ni en contra
                    continue
                textured += 1
                if inside[sl].mean() < 230:                   # fuera del encuadre
                    continue
                q = seen[sl]
                qs = q.std()
                if qs < 4:
                    continue
                ncc = float(((r - r.mean()) * (q - q.mean())).mean() / (rs * qs))
                if ncc >= NCC_MIN:
                    hits += 1
                    scores.append(ncc)
                    centres.append(((i + .5) * bw, (j + .5) * bh))
        frame_pts = (cv2.perspectiveTransform(np.float32(centres).reshape(-1, 1, 2), H).reshape(-1, 2)
                     if centres else np.zeros((0, 2), np.float32))
        return (hits / max(textured, 1), hits, float(np.mean(scores)) if scores else 0.0, frame_pts)

    # ------------------------------------------------------------------ pose
    def _pose(self, src, dst, w, h, corners):
        """-> (H 3x3, inliers, parcial?) o None."""
        if len(src) >= self.min_inliers:
            H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
            if H is not None and int(mask.sum()) >= self.min_inliers:
                quad = cv2.perspectiveTransform(corners, H).reshape(4, 2)
                if self._plausible(quad, H, w, h):
                    return H, int(mask.sum()), False
        A, mask = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0,
                                              maxIters=3000, confidence=0.995)
        if A is None or int(mask.sum()) < self.min_partial:
            return None
        # inliers en puntos distintos: varios emparejamientos sobre el mismo punto no son evidencia
        if len(np.unique(np.round(dst.reshape(-1, 2)[mask.ravel() > 0] / 3), axis=0)) < self.min_partial:
            return None
        scale = float(np.hypot(A[0, 0], A[1, 0]))
        if not (60 <= scale * CARD_H <= 1.8 * max(w, h)):
            return None
        return np.vstack([A, [0, 0, 1]]), int(mask.sum()), True

    def scan(self, frame_bgr: np.ndarray) -> list[Found]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        big = cv2.resize(gray, None, fx=self.up, fy=self.up, interpolation=cv2.INTER_CUBIC) if self.up != 1 else gray
        kp, des = self.qsift.detectAndCompute(big, None)
        if des is None or len(kp) < 6:
            return []
        q_pts = np.float32([k.pt for k in kp]) / self.up
        groups: dict[int, list[tuple[int, int]]] = {}
        for nb in self.flann.knnMatch(des, k=4):
            # test de proporción contra el mejor vecino de OTRA carta (los descriptores de la misma carta a
            # otra escala se parecen y no cuentan como competencia)
            first = nb[0]
            own = int(self.owner[first.trainIdx])
            card = self.card_of[own]
            rival = next((m for m in nb[1:] if self.card_of[self.owner[m.trainIdx]] != card), None)
            if rival is None or first.distance < self.ratio * rival.distance:
                groups.setdefault(own, []).append((first.queryIdx, first.trainIdx))
        candidates = []
        for tid, ms in groups.items():
            if len(ms) < self.min_partial:
                continue
            src = self.ref_pts[[t for _, t in ms]].reshape(-1, 1, 2)
            dst = q_pts[[q for q, _ in ms]].reshape(-1, 1, 2)
            pose = self._pose(src, dst, w, h, self.corners[tid])
            if pose is None:
                continue
            H, inliers, partial = pose
            visible, blocks, ncc, frame_pts = self._verify_blocks(gray, tid, H)
            if partial:
                if blocks < MIN_BLOCKS_PARTIAL or ncc < NCC_STRONG:
                    continue
            elif blocks < 3:
                continue
            quad = cv2.perspectiveTransform(self.corners[tid], H).reshape(4, 2)
            mid = self.deck.images[tid].shape[1] / 2
            top_y = cv2.perspectiveTransform(np.float32([[[mid, 0]]]), H)[0, 0, 1]
            bot_y = cv2.perspectiveTransform(np.float32([[[mid, CARD_H]]]), H)[0, 0, 1]
            cid = int(self.card_of[tid])
            score = inliers + 2.0 * blocks * ncc
            candidates.append((Found(cid, bool(top_y > bot_y), inliers, quad, min(visible, 1.0), score), frame_pts))
        # dos cartas no pueden explicar los mismos píxeles: gana la de más evidencia
        out, taken = [], np.zeros((0, 2), np.float32)
        for f, pts in sorted(candidates, key=lambda c: -c[0].score):
            if any(o.card_id == f.card_id for o in out):       # otra edición de la misma carta
                continue
            if len(pts) and len(taken):
                d = np.linalg.norm(pts[:, None, :] - taken[None, :, :], axis=2).min(axis=1)
                if (d < 12).mean() > 0.5:
                    continue
            out.append(f)
            taken = np.vstack([taken, pts])
        return sorted(out, key=lambda f: f.center[0])

    @staticmethod
    def _plausible(quad, H, w, h) -> bool:
        if np.linalg.det(H[:2, :2]) <= 0:                      # reflejo
            return False
        if not cv2.isContourConvex(quad.astype(np.float32)):
            return False
        area = cv2.contourArea(quad.astype(np.float32))
        if area < 1500 or area > 1.5 * w * h:
            return False
        s = [np.linalg.norm(quad[i] - quad[(i + 1) % 4]) for i in range(4)]
        if min(s) < 15 or max(s[0], s[2]) / max(min(s[0], s[2]), 1) > 1.8 \
                or max(s[1], s[3]) / max(min(s[1], s[3]), 1) > 1.8:
            return False
        ar = (s[0] + s[2]) / (s[1] + s[3])
        return 0.40 <= ar <= 0.85
