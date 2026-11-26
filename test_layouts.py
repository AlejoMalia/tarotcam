"""Geometría -> disposición y roles (sin cámara ni reconocimiento)."""
import i18n
i18n.set_lang("es")  # estas comprobaciones están escritas sobre los textos en español

import numpy as np
from tracker import Track
from spreads import analyze

def tr(i, cx, cy, ang=0.0, w=70, h=120):
    c = np.float32([[-w/2, -h/2], [w/2, -h/2], [w/2, h/2], [-w/2, h/2]])
    a = np.deg2rad(ang); R = np.float32([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return Track(i, c @ R.T + np.float32([cx, cy]), False, seq=i + 1)

def show(name, tracks, mode="auto", expect_kind=None, expect=None):
    lay = analyze(tracks, mode)
    roles = {s.track.card_id: s.role for s in lay.slots}
    ok = (expect_kind is None or lay.kind == expect_kind) and (expect is None or all(roles.get(k) == v for k, v in expect.items()))
    print(f"{'OK ' if ok else 'MAL'} {name:34s} -> {lay.kind:9s} {lay.name}")
    if not ok: print("     ", roles)
    return lay

# 3 filas con 1,2,1 cartas
show("3 filas (1,2,1)", [tr(0, 320, 90), tr(1, 250, 240), tr(2, 390, 240), tr(3, 320, 390)], expect_kind="rows",
     expect={0: "Pasado", 1: "Presente", 2: "Presente", 3: "Futuro"})
# columna de 3 cartas
show("3 cartas en columna", [tr(0, 320, 80), tr(1, 320, 240), tr(2, 320, 400)], expect_kind="rows",
     expect={0: "Pasado", 1: "Presente", 2: "Futuro"})
# línea de 3 (orden distinto al de entrada)
show("3 cartas en línea", [tr(0, 450, 240), tr(1, 150, 240), tr(2, 300, 240)], expect_kind="line",
     expect={1: "Pasado", 2: "Presente", 0: "Futuro"})
show("2 filas", [tr(0, 200, 120), tr(1, 400, 120), tr(2, 300, 360)], expect_kind="rows", expect={0: "Situación", 2: "Resultado"})
# cruz de 5
show("cruz de 5", [tr(0, 320, 240), tr(1, 320, 100), tr(2, 320, 380), tr(3, 190, 240), tr(4, 450, 240)], expect_kind="cross",
     expect={0: "Núcleo", 1: "Arriba · lo que corona (consciente)", 2: "Abajo · la raíz (inconsciente)",
             3: "Izquierda · lo que se va (pasado)", 4: "Derecha · lo que llega (futuro)"})
# cruz celta de 10 (la que cruza va girada 90°)
cel = [tr(0, 250, 240), tr(1, 250, 240, ang=90), tr(2, 250, 370), tr(3, 140, 240), tr(4, 250, 110), tr(5, 360, 240),
       tr(6, 500, 370), tr(7, 500, 270), tr(8, 500, 170), tr(9, 500, 70)]
show("cruz celta", cel, expect_kind="celtic", expect={0: "1 · Presente (el núcleo)", 1: "2 · Desafío (lo que cruza)",
     2: "3 · Base / raíz", 3: "4 · Pasado reciente", 4: "5 · Corona / consciente", 5: "6 · Futuro próximo",
     6: "7 · Tú mismo/a", 9: "10 · Resultado"})
# herradura de 7 (U)
hs = [tr(i, 70 + 85 * i, [120, 220, 310, 340, 310, 220, 120][i]) for i in range(7)]
show("herradura", hs, expect_kind="horseshoe", expect={0: "1 · Pasado", 6: "7 · Resultado"})
# negativos: 5 cartas que no forman cruz -> filas; 7 en línea recta -> línea
show("5 en línea (no cruz)", [tr(i, 80 + 110 * i, 240) for i in range(5)], expect_kind="line")
show("7 en línea (no herradura)", [tr(i, 60 + 85 * i, 240) for i in range(7)], expect_kind="line")
# forzar modos
show("forzar entry", [tr(0, 450, 240), tr(1, 150, 240), tr(2, 300, 240)], "entry", expect_kind="entry", expect={0: "Pasado"})
show("forzar cruz sin encajar", [tr(i, 80 + 110 * i, 240) for i in range(5)], "cross", expect_kind="line")

# --- humo: la lectura se genera sin errores en todas las disposiciones, con cartas aleatorias --------
import random, reading
random.seed(1)
def tracks_from(geom):
    ids = random.sample(range(78), len(geom))
    ts = [tr(ids[k], x, y, ang) for k, (x, y, ang) in enumerate(geom)]
    for t in ts: t.reversed = random.random() < .3
    return ts
G = {
 "1": [(320, 240, 0)],
 "2 línea": [(200, 240, 0), (440, 240, 0)],
 "3 filas": [(320, 80, 0), (320, 240, 0), (320, 400, 0)],
 "4 en 2 filas": [(200, 120, 0), (400, 120, 0), (200, 360, 0), (400, 360, 0)],
 "cruz": [(320, 240, 0), (320, 100, 0), (320, 380, 0), (190, 240, 0), (450, 240, 0)],
 "celta": [(250, 240, 0), (250, 240, 90), (250, 370, 0), (140, 240, 0), (250, 110, 0), (360, 240, 0), (500, 370, 0), (500, 270, 0), (500, 170, 0), (500, 70, 0)],
 "herradura": [(70 + 85 * i, [120, 220, 310, 340, 310, 220, 120][i], 0) for i in range(7)],
 "14 libres": [(40 + 45 * (i % 14), 100 + 60 * (i % 4), 0) for i in range(14)],
}
for name, geom in G.items():
    lay = analyze(tracks_from(geom))
    items, secs = reading.compose(lay)
    assert len(items) == len(geom) and secs
    cons = dict(secs)["Consejo"]
    print(f"humo OK  {name:14s} -> {lay.kind:9s} secciones={len(secs)}  | {cons[-70:]}")
