"""Disposición de las cartas en la mesa -> rol de cada carta según su posición.

Mira solo la geometría (centros y tamaño de las cartas en la imagen; arriba = parte alta de la imagen):
  - 3 filas              -> fila superior Pasado, central Presente, inferior Futuro (varias cartas por fila valen)
  - 2 filas              -> Situación / Resultado
  - 1 fila               -> izquierda -> derecha (3 cartas: Pasado, Presente, Futuro)
  - Cruz (5)             -> centro + arriba/abajo/izquierda/derecha
  - Cruz celta (10)      -> cruz de 6 cartas + columna de 4
  - Herradura (7)        -> arco de 7 cartas
  - 'entry'              -> por orden de llegada (comportamiento anterior)
Si ninguna plantilla encaja, cae a filas/línea. `mode` permite forzar una: auto|entry|line|rows|cross|celtic|horseshoe.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from i18n import L

MODES = ["auto", "entry", "line", "rows", "cross", "celtic", "horseshoe"]


@dataclass
class Slot:
    track: object
    role: str
    weight: float = 1.0           # peso de posición (el centro y el resultado pesan más)
    group: int | None = None      # fila/grupo temporal (0=pasado, 1=presente, 2=futuro)
    key: str = ""                 # id interno del rol para la lectura (p.ej. 'centro', 'resultado')


@dataclass
class Layout:
    kind: str                     # empty|single|line|rows|cross|celtic|horseshoe|entry
    name: str
    slots: list[Slot] = field(default_factory=list)
    note: str = ""


# ---------------------------------------------------------------- geometría
def _card_size(tracks):
    hs, ws = [], []
    for t in tracks:
        q = np.asarray(t.quad, float)
        hs.append((np.linalg.norm(q[0] - q[3]) + np.linalg.norm(q[1] - q[2])) / 2)
        ws.append((np.linalg.norm(q[0] - q[1]) + np.linalg.norm(q[3] - q[2])) / 2)
    return float(np.median(hs)), float(np.median(ws))


def _centers(tracks):
    return np.array([np.asarray(t.quad, float).mean(axis=0) for t in tracks])


def _cluster_rows(ys, thr):
    """Agrupa índices por altura (arriba -> abajo)."""
    order = np.argsort(ys)
    rows, cur = [], [order[0]]
    for i in order[1:]:
        if ys[i] - np.mean(ys[cur]) > thr:
            rows.append(cur)
            cur = [i]
        else:
            cur.append(i)
    rows.append(cur)
    return rows


def _is_horizontal(track) -> bool:
    q = np.asarray(track.quad, float)
    v = q[3] - q[0]                       # lado izquierdo (largo) de la carta
    return abs(v[0]) > abs(v[1])


# ---------------------------------------------------------------- plantillas
# roles bilingües: (inglés, español); se resuelven al analizar, en el idioma actual
CELTIC = {1: ("1 · Present (the core)", "1 · Presente (el núcleo)"),
          2: ("2 · Challenge (what crosses)", "2 · Desafío (lo que cruza)"),
          3: ("3 · Base / root", "3 · Base / raíz"), 4: ("4 · Recent past", "4 · Pasado reciente"),
          5: ("5 · Crown / conscious", "5 · Corona / consciente"), 6: ("6 · Near future", "6 · Futuro próximo"),
          7: ("7 · Yourself", "7 · Tú mismo/a"), 8: ("8 · Environment", "8 · Entorno"),
          9: ("9 · Hopes and fears", "9 · Esperanzas y miedos"), 10: ("10 · Outcome", "10 · Resultado")}
CELTIC_W = {1: 1.3, 2: 1.2, 10: 1.3}
CROSS = {"centro": ("Core", "Núcleo"),
         "arriba": ("Above · what crowns it (conscious)", "Arriba · lo que corona (consciente)"),
         "abajo": ("Below · the root (unconscious)", "Abajo · la raíz (inconsciente)"),
         "izq": ("Left · what is leaving (past)", "Izquierda · lo que se va (pasado)"),
         "der": ("Right · what is coming (future)", "Derecha · lo que llega (futuro)")}
HORSE = [("Past", "Pasado"), ("Present", "Presente"), ("Near future", "Futuro inmediato"), ("Yourself", "Tú mismo/a"),
         ("Environment", "Entorno"), ("Obstacles", "Obstáculos"), ("Outcome", "Resultado")]
TIME_NAMES = [("Past", "Pasado"), ("Present", "Presente"), ("Future", "Futuro")]
PAIR_NAMES = [("Situation", "Situación"), ("Challenge / advice", "Desafío / consejo")]
ROW2_NAMES = [("Situation", "Situación"), ("Outcome", "Resultado")]
TIME_W = {0: 1.0, 1: 1.25, 2: 1.15}


def _direction(dx, dy):
    if abs(dx) >= abs(dy):
        return "der" if dx > 0 else "izq"
    return "abajo" if dy > 0 else "arriba"


def _celtic(tracks, C, Hc, Wc):
    n = len(tracks)
    order = np.argsort(C[:, 0])
    for col in (order[-4:], order[:4]):
        if np.ptp(C[col, 0]) > 0.9 * Wc:
            continue
        col = sorted(col, key=lambda i: -C[i, 1])                  # de abajo a arriba: 7,8,9,10
        rest = [i for i in range(n) if i not in col]
        cen = C[rest].mean(axis=0)
        two = sorted(rest, key=lambda i: np.linalg.norm(C[i] - cen))[:2]
        if np.linalg.norm(C[two[0]] - C[two[1]]) > 0.9 * Hc:
            continue
        horiz = [i for i in two if _is_horizontal(tracks[i])]       # la carta que cruza va girada 90°
        c2 = horiz[0] if len(horiz) == 1 else two[1]
        c1 = two[0] if c2 == two[1] else two[1]
        others = [i for i in rest if i not in (c1, c2)]
        dirs = {_direction(*(C[i] - C[c1])): i for i in others}
        if len(dirs) != 4:
            continue
        pos = {1: c1, 2: c2, 3: dirs["abajo"], 4: dirs["izq"], 5: dirs["arriba"], 6: dirs["der"],
               7: col[0], 8: col[1], 9: col[2], 10: col[3]}
        slots = [Slot(tracks[pos[k]], L(*CELTIC[k]), CELTIC_W.get(k, 1.0), key=f"c{k}") for k in range(1, 11)]
        return Layout("celtic", L("Celtic Cross", "Cruz celta"), slots)
    return None


def _cross(tracks, C, Hc, Wc):
    cen = C.mean(axis=0)
    c = int(np.argmin(np.linalg.norm(C - cen, axis=1)))
    others = [i for i in range(len(tracks)) if i != c]
    dirs = {_direction(*(C[i] - C[c])): i for i in others}
    if len(dirs) != 4:
        return None
    for d, i in dirs.items():                                        # alineadas con el eje, no en diagonal
        dx, dy = C[i] - C[c]
        if (d in ("arriba", "abajo") and abs(dx) > 0.8 * Wc) or (d in ("izq", "der") and abs(dy) > 0.8 * Hc):
            return None
    slots = [Slot(tracks[c], L(*CROSS["centro"]), 1.3, key="centro")]
    slots += [Slot(tracks[dirs[d]], L(*CROSS[d]), 1.0, key=d) for d in ("arriba", "izq", "der", "abajo")]
    return Layout("cross", L("Cross", "Cruz"), slots)


def _horseshoe(tracks, C, Hc, Wc):
    order = np.argsort(C[:, 0])
    y = C[order, 1]
    if abs(y[3] - (y[0] + y[6]) / 2) < 0.5 * Hc:
        return None
    slots = [Slot(tracks[i], f"{k + 1} · {L(*HORSE[k])}", 1.3 if k == 6 else 1.0, key=f"h{k + 1}")
             for k, i in enumerate(order)]
    return Layout("horseshoe", L("Horseshoe", "Herradura"), slots)


def _rows_or_line(tracks, C, Hc):
    n = len(tracks)
    rows = _cluster_rows(C[:, 1], 0.6 * Hc)
    if len(rows) == 1:
        order = np.argsort(C[:, 0])
        if n == 1:
            return Layout("single", L("Single card", "Carta única"),
                          [Slot(tracks[0], L("Message of the moment", "Mensaje del momento"), key="unica")])
        names = {2: PAIR_NAMES, 3: TIME_NAMES}.get(n)
        slots = []
        for k, i in enumerate(order):
            role = L(*names[k]) if names else L(f"Position {k + 1}", f"Posición {k + 1}")
            slots.append(Slot(tracks[i], role, TIME_W.get(k, 1.0) if n == 3 else 1.0,
                              group=k if n == 3 else None, key=f"l{k + 1}"))
        title = {2: L("Two cards", "Dos cartas"), 3: L("Three cards (left to right)", "Tres cartas (izquierda a derecha)")}
        return Layout("line", title.get(n, L(f"Line of {n}", f"Línea de {n}")), slots)
    nr = len(rows)
    names = {2: ROW2_NAMES, 3: TIME_NAMES}.get(nr)
    slots = []
    for r, idxs in enumerate(rows):
        role = L(*names[r]) if names else L(f"Level {r + 1}", f"Nivel {r + 1}")
        for i in sorted(idxs, key=lambda i: C[i, 0]):
            slots.append(Slot(tracks[i], role, TIME_W.get(r, 1.0) if nr == 3 else 1.0, group=r, key=f"r{r + 1}"))
    label = {2: L("2 rows (top: situation, bottom: outcome)", "2 filas (arriba: situación, abajo: resultado)"),
             3: L("3 rows (top past, middle present, bottom future)",
                  "3 filas (arriba pasado, centro presente, abajo futuro)")}.get(nr, L(f"{nr} rows", f"{nr} filas"))
    return Layout("rows", label, slots)


def _entry(tracks):
    from reading import position_names
    n = len(tracks)
    ts = sorted(tracks, key=lambda t: t.seq)
    names = position_names(n)
    return Layout("entry", L("Order of arrival", "Orden de llegada"),
                  [Slot(t, names[i] if names else L(f"Card {i + 1}", f"Carta {i + 1}"), key=f"e{i + 1}")
                   for i, t in enumerate(ts)])


def analyze(tracks, mode: str = "auto") -> Layout:
    tracks = list(tracks)
    n = len(tracks)
    if n == 0:
        return Layout("empty", "")
    if mode == "entry":
        return _entry(tracks)
    C = _centers(tracks)
    Hc, Wc = _card_size(tracks)
    lay = None
    if mode in ("auto", "celtic") and n == 10:
        lay = _celtic(tracks, C, Hc, Wc)
    elif mode in ("auto", "cross") and n == 5:
        lay = _cross(tracks, C, Hc, Wc)
    elif mode in ("auto", "horseshoe") and n == 7:
        lay = _horseshoe(tracks, C, Hc, Wc)
    if lay is None:
        lay = _rows_or_line(tracks, C, Hc)
        if mode in ("celtic", "cross", "horseshoe"):
            shape = {"celtic": ("Celtic Cross", "cruz celta"), "cross": ("cross", "cruz"),
                     "horseshoe": ("horseshoe", "herradura")}[mode]
            lay.note = L(f"The cards do not form a {shape[0]}; they are read by rows.",
                         f"Las cartas no forman una {shape[1]}; se leen por filas.")
    if mode == "line" and lay.kind == "rows":                      # forzar línea: izq->der ignorando alturas
        order = np.argsort(C[:, 0])
        lay = Layout("line", L(f"Line of {n}", f"Línea de {n}"),
                     [Slot(tracks[i], L(f"Position {k + 1}", f"Posición {k + 1}"), key=f"l{k + 1}")
                                              for k, i in enumerate(order)])
    return lay
