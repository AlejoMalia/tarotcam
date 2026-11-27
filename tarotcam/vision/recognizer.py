"""Detección de cartas en un fotograma e identificación contra la baraja de referencia.

1. find_cards():  contornos cuadriláteros con proporción de carta -> 4 esquinas.
2. warp:          perspectiva -> carta enderezada (CARD_W x CARD_H), borde superior = arriba de la imagen.
3. identify():    SIFT + ratio test contra las 78 referencias, verificación con homografía (RANSAC).
                  La orientación (derecho / al revés) sale de la homografía, no de un clasificador.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from tarotcam.carddata.cards import CARDS

CARD_W, CARD_H = 240, 410          # tamaño canónico (proporción ~0.585 de una carta real)
MIN_INLIERS = 11                   # inliers RANSAC mínimos para aceptar una carta
MARGIN = 1.4                       # el mejor debe superar al segundo en este factor
ASPECT = (0.45, 0.78)              # ancho/alto aceptado para el cuadrilátero


@dataclass
class Detection:
    quad: np.ndarray               # 4x2 en imagen, orden tl,tr,br,bl (tl = arriba de la imagen)
    warped: np.ndarray             # gris CARD_H x CARD_W
    M: np.ndarray                  # imagen -> canónico

    @property
    def center(self):
        return self.quad.mean(axis=0)


@dataclass
class Match:
    card_id: int
    reversed: bool
    inliers: int
    second: int


def order_quad(pts) -> np.ndarray:
    """Ordena 4 puntos en tl,tr,br,bl con el lado izquierdo largo y la parte alta arriba."""
    p = np.asarray(pts, np.float32).reshape(4, 2)
    c = p.mean(axis=0)
    ang = np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0])
    p = p[np.argsort(ang)]                      # sentido horario en coordenadas de imagen
    e0 = np.linalg.norm(p[0] - p[1])
    e1 = np.linalg.norm(p[1] - p[2])
    if e0 > e1:                                  # lado izquierdo (p3->p0) corto: rotar 90°
        p = np.roll(p, -1, axis=0)
    if p[0][1] + p[1][1] > p[2][1] + p[3][1]:    # lo "alto" debe estar arriba en la imagen
        p = np.roll(p, 2, axis=0)
    return p


def _candidates(gray: np.ndarray):
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    masks = []
    edges = cv2.Canny(blur, 40, 120)
    masks.append(cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    masks.append(otsu)
    masks.append(255 - otsu)
    for m in masks:
        cnts, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        yield from cnts


def find_cards(frame_bgr: np.ndarray, min_frac=0.03, max_frac=0.85) -> list[Detection]:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    quads = []
    for c in _candidates(gray):
        area = cv2.contourArea(c)
        if area < min_frac * h * w or area > max_frac * h * w:
            continue
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        ap = cv2.approxPolyDP(hull, 0.03 * peri, True)
        if len(ap) != 4:
            continue
        q = order_quad(ap)
        wid = (np.linalg.norm(q[0] - q[1]) + np.linalg.norm(q[3] - q[2])) / 2
        hei = (np.linalg.norm(q[0] - q[3]) + np.linalg.norm(q[1] - q[2])) / 2
        if hei < 1 or not (ASPECT[0] <= wid / hei <= ASPECT[1]):
            continue
        # el cuadrilátero debe rellenar bien su casco (descarta formas raras)
        if cv2.contourArea(q) < 0.85 * area:
            continue
        quads.append((cv2.contourArea(q), q))
    # NMS: los marcos interiores de la ilustración duplican la carta -> quedarse con el mayor
    quads.sort(key=lambda t: -t[0])
    kept: list[np.ndarray] = []
    for a, q in quads:
        ctr = q.mean(axis=0)
        if all(np.linalg.norm(ctr - k.mean(axis=0)) > 0.35 * math.sqrt(a) for k in kept):
            kept.append(q)
    dets = []
    dst = np.float32([[0, 0], [CARD_W, 0], [CARD_W, CARD_H], [0, CARD_H]])
    for q in kept:
        M = cv2.getPerspectiveTransform(q, dst)
        warped = cv2.warpPerspective(gray, M, (CARD_W, CARD_H), flags=cv2.INTER_CUBIC)
        dets.append(Detection(q, warped, M))
    return dets


class Deck:
    def __init__(self, deck_dir: str | Path):
        deck_dir = Path(deck_dir)
        self.sift = cv2.SIFT_create(nfeatures=800, contrastThreshold=0.02)
        self.bf = cv2.BFMatcher(cv2.NORM_L2)
        self.refs = []
        self.refs_half = []
        self.refs_dense = []
        self.images = []
        dense = cv2.SIFT_create(nfeatures=1600, contrastThreshold=0.008)
        for c in CARDS:
            path = deck_dir / f"{c['id']:02d}.jpg"
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(f"Missing {path}. Run: python -m tarotcam.tools.download_deck")
            img = cv2.resize(img, (CARD_W, CARD_H), interpolation=cv2.INTER_AREA)
            kp, des = self.sift.detectAndCompute(img, None)
            self.refs.append((np.float32([k.pt for k in kp]), des))
            self.images.append(img)
            kp3, des3 = dense.detectAndCompute(img, None)      # cobertura densa: cualquier trozo tiene puntos
            self.refs_dense.append((np.float32([k.pt for k in kp3]), des3))
            # versión a media resolución: casa mejor con cartas pequeñas y borrosas (puntos x2 al sistema canónico)
            half = cv2.resize(img, (CARD_W // 2, CARD_H // 2), interpolation=cv2.INTER_AREA)
            kp2, des2 = self.sift.detectAndCompute(half, None)
            self.refs_half.append((np.float32([k.pt for k in kp2]) * 2 if kp2 else np.zeros((0, 2), np.float32), des2))

    def _good(self, des, ref_des):
        if des is None or ref_des is None or len(des) < 2 or len(ref_des) < 2:
            return []
        out = []
        for pair in self.bf.knnMatch(des, ref_des, k=2):
            if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance:
                out.append(pair[0])
        return out

    def _verify(self, card_id, kp_pts, good):
        if len(good) < 8:
            return 0, None
        ref_pts = self.refs[card_id][0]
        src = np.float32([ref_pts[m.trainIdx] for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp_pts[m.queryIdx] for m in good]).reshape(-1, 1, 2)
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 6.0)
        if H is None or np.linalg.det(H[:2, :2]) <= 0:      # det<=0: reflejo o degenerada
            return 0, None
        return int(mask.sum()), H

    def _orientation(self, H, det: Detection) -> bool:
        pts = np.float32([[[CARD_W / 2, 0]], [[CARD_W / 2, CARD_H]]])
        canon = cv2.perspectiveTransform(pts, H)
        img = cv2.perspectiveTransform(canon, np.linalg.inv(det.M))
        return bool(img[0, 0, 1] > img[1, 0, 1])             # arriba de la carta cae abajo -> al revés

    def identify(self, det: Detection, only: int | None = None) -> Match | None:
        kp, des = self.sift.detectAndCompute(det.warped, None)
        if des is None or len(kp) < 8:
            return None
        kp_pts = np.float32([k.pt for k in kp])
        ids = [only] if only is not None else range(len(self.refs))
        goods = {i: self._good(des, self.refs[i][1]) for i in ids}
        top = sorted(goods, key=lambda i: -len(goods[i]))[:4]
        res = []
        for i in top:
            inl, H = self._verify(i, kp_pts, goods[i])
            res.append((inl, i, H))
        res.sort(key=lambda t: -t[0])
        best, bid, H = res[0]
        second = res[1][0] if len(res) > 1 else 0
        if best < MIN_INLIERS or (only is None and best < MARGIN * max(second, 1)):
            return None
        return Match(bid, self._orientation(H, det), best, second)


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
            for cid, (p, d) in enumerate(refs):
                if d is None or len(d) == 0:
                    continue
                des.append(d)
                owner.append(np.full(len(d), cid, np.int32))
                pts.append(p)
        self.owner = np.concatenate(owner)
        self.ref_pts = np.concatenate(pts)
        self.flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=64))
        self.flann.add([np.concatenate(des).astype(np.float32)])
        self.flann.train()
        self.corners = np.float32([[[0, 0]], [[CARD_W, 0]], [[CARD_W, CARD_H]], [[0, CARD_H]]])
        self.blurred = [cv2.GaussianBlur(i, (0, 0), 1.2).astype(np.float32) for i in deck.images]

    # ------------------------------------------------------------------ verificación
    def _verify_blocks(self, gray: np.ndarray, cid: int, H: np.ndarray):
        """-> (fracción visible, nº de bloques que coinciden, ncc media de esos bloques, centros en el fotograma)."""
        flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP                  # H: carta -> fotograma
        seen = cv2.warpPerspective(gray, H, (CARD_W, CARD_H), flags=flags)
        inside = cv2.warpPerspective(np.full(gray.shape, 255, np.uint8), H, (CARD_W, CARD_H), flags=flags)
        seen = cv2.GaussianBlur(seen, (0, 0), 1.2).astype(np.float32)
        ref = self.blurred[cid]
        bw, bh = CARD_W // BLOCK_W, CARD_H // BLOCK_H
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
    def _pose(self, src, dst, w, h):
        """-> (H 3x3, inliers, parcial?) o None."""
        if len(src) >= self.min_inliers:
            H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
            if H is not None and int(mask.sum()) >= self.min_inliers:
                quad = cv2.perspectiveTransform(self.corners, H).reshape(4, 2)
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
            rival = next((m for m in nb[1:] if int(self.owner[m.trainIdx]) != own), None)
            if rival is None or first.distance < self.ratio * rival.distance:
                groups.setdefault(own, []).append((first.queryIdx, first.trainIdx))
        candidates = []
        for cid, ms in groups.items():
            if len(ms) < self.min_partial:
                continue
            src = self.ref_pts[[t for _, t in ms]].reshape(-1, 1, 2)
            dst = q_pts[[q for q, _ in ms]].reshape(-1, 1, 2)
            pose = self._pose(src, dst, w, h)
            if pose is None:
                continue
            H, inliers, partial = pose
            visible, blocks, ncc, frame_pts = self._verify_blocks(gray, cid, H)
            if partial:
                if blocks < MIN_BLOCKS_PARTIAL or ncc < NCC_STRONG:
                    continue
            elif blocks < 3:
                continue
            quad = cv2.perspectiveTransform(self.corners, H).reshape(4, 2)
            top_y = cv2.perspectiveTransform(np.float32([[[CARD_W / 2, 0]]]), H)[0, 0, 1]
            bot_y = cv2.perspectiveTransform(np.float32([[[CARD_W / 2, CARD_H]]]), H)[0, 0, 1]
            score = inliers + 2.0 * blocks * ncc
            candidates.append((Found(cid, bool(top_y > bot_y), inliers, quad, min(visible, 1.0), score), frame_pts))
        # dos cartas no pueden explicar los mismos píxeles: gana la de más evidencia
        out, taken = [], np.zeros((0, 2), np.float32)
        for f, pts in sorted(candidates, key=lambda c: -c[0].score):
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
