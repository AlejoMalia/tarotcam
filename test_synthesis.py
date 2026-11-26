"""Escenarios con sentido: ¿el motor combina bien y usa los datos de simbología?"""
import i18n
i18n.set_lang("es")  # estas comprobaciones están escritas sobre los textos en español

import numpy as np
from tracker import Track
from spreads import analyze
import reading, synthesis, knowledge

def tr(i, cx, cy, rev=False, w=70, h=120):
    c = np.float32([[-w/2, -h/2], [w/2, -h/2], [w/2, h/2], [-w/2, h/2]])
    return Track(i, c + np.float32([cx, cy]), rev, seq=int(cx + cy))

def show(titulo, cards, geom=None):
    geom = geom or [(100 + 150 * k, 240) for k in range(len(cards))]
    ts = [tr(cid, x, y, rev) for (cid, rev), (x, y) in zip(cards, geom)]
    for k, t in enumerate(ts): t.seq = k + 1
    lay = analyze(ts)
    items, secs = reading.compose(lay)
    print(f"\n=== {titulo}  [{lay.name}]")
    for title, text in secs:
        if title in ("Resumen", "Según su posición", "Hilos y tensiones", "Símbolos en común", "Correspondencias en común", "Consejo"):
            print(f"  [{title}] {text}")
    return dict(secs)

# 1) 3 filas: Torre (pasado), Mago+Dos de Copas (presente), Sol (futuro)
s = show("3 filas: Torre / Mago+Dos Copas / Sol", [(16, False), (1, False), (37, False), (19, False)],
         [(320, 80), (250, 240), (390, 240), (320, 400)])
assert "pasado al presente" in s["Hilos y tensiones"].lower() and "presente al futuro" in s["Hilos y tensiones"].lower()
# 2) tensión cambio/estabilidad: Torre + Cuatro de Oros (id 64+3=67) + Emperador
s = show("Tensión esperada: Torre, Cuatro de Oros, Emperador", [(16, False), (67, False), (4, False)])
assert "Tensión:" in s["Hilos y tensiones"]
# 3) símbolos compartidos: Sacerdotisa + Luna ; Enamorados + Templanza + Juicio
# (los símbolos compartidos solo existen con la base de conocimiento opcional)
if knowledge.available():
    s = show("Símbolos: Sacerdotisa + Luna", [(2, False), (18, False)])
    assert "luna" in s["Símbolos en común"].lower()
    s = show("Símbolos: Enamorados + Templanza + Juicio", [(6, False), (14, False), (20, False)])
    assert "ángel" in s["Símbolos en común"].lower()
else:
    print("(sin knowledge/: se omiten las comprobaciones de símbolos)")
# 4) una carta invertida usa su significado invertido
s = show("Invertida: La Torre al revés", [(16, True)])
expected = "evitar desastre" if knowledge.available() else "evitar el desastre"
assert expected in reading.compose(analyze([tr(16, 300, 240, True)]))[0][0]["meaning"].lower()
# 5) cruz con 5 cartas
show("Cruz", [(10, False), (7, False), (16, True), (13, False), (19, False)],
     [(320, 240), (320, 100), (320, 380), (190, 240), (450, 240)])

# 6) correspondencias compartidas: La Torre (Marte) + Dos de Bastos (Marte en Aries) + Tres de Bastos (Sol en Aries)
s = show("Correspondencias: Torre, 2 y 3 de Bastos", [(16, False), (23, False), (24, False)])
assert "Marte" in s["Correspondencias en común"] and "Aries" in s["Correspondencias en común"]

# 7) sin base de conocimiento el motor sigue funcionando (respaldo cards.py)
saved = dict(knowledge.KB); knowledge.KB.clear()
items, secs = reading.compose(analyze([tr(16, 200, 240), tr(17, 350, 240), tr(19, 500, 240)]))
assert items and secs
print("\nSin knowledge/kb.json: OK (", len(secs), "secciones )")
knowledge.KB.update(saved)
print("\nOK: test_synthesis")
