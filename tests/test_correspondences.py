"""Completitud y coherencia de las correspondencias de las 78 cartas."""
from tarotcam import i18n
i18n.set_lang("es")  # estas comprobaciones están escritas sobre los textos en español

from collections import Counter
from tarotcam.carddata.cards import CARDS, BY_ID
from tarotcam.carddata import correspondences as K

# 1) las 78 tienen los 4 datos
for c in CARDS:
    r = c["corr"]
    assert r["numero"] and r["elemento"] and r["astro"] and r["extra"], c["es"]
print("OK  78 cartas con número, elemento, astrología y extra")

# 2) tu tabla: casos concretos
def corr(es): return next(c for c in CARDS if c["es"] == es)["corr"]
checks = [
    ("El Loco", "Aire", "Aire (moderno: Urano)", "Aleph"), ("El Mago", "Aire", "Mercurio", "Beth"),
    ("La Sacerdotisa", "Agua", "Luna", "Gimel"), ("El Emperador", "Fuego", "Aries", "Heh"),
    ("La Fuerza", "Fuego", "Leo", "Teth"), ("La Rueda de la Fortuna", "Fuego", "Júpiter", "Kaph"),
    ("El Colgado", "Agua", "Agua (moderno: Neptuno)", "Mem"), ("La Torre", "Fuego", "Marte", "Peh"),
    ("La Estrella", "Aire", "Acuario", "Tzaddi"), ("El Juicio", "Fuego", "Fuego (moderno: Plutón)", "Shin"),
    ("El Mundo", "Tierra", "Saturno", "Tav"),
    ("Dos de Bastos", "Fuego", "Marte en Aries", None), ("Tres de Bastos", "Fuego", "Sol en Aries", None),
    ("Cinco de Bastos", "Fuego", "Saturno en Leo", None), ("Diez de Bastos", "Fuego", "Saturno en Sagitario", None),
    ("Cuatro de Copas", "Agua", "Luna en Cáncer", None), ("Diez de Copas", "Agua", "Marte en Piscis", None),
    ("Siete de Espadas", "Aire", "Luna en Acuario", None), ("Diez de Espadas", "Aire", "Sol en Géminis", None),
    ("Cuatro de Oros", "Tierra", "Sol en Capricornio", None), ("Diez de Oros", "Tierra", "Mercurio en Virgo", None),
    ("Sota de Bastos", "Tierra de Fuego", None, None), ("Caballero de Copas", "Aire de Agua", None, None),
    ("Reina de Espadas", "Agua de Aire", None, None), ("Rey de Oros", "Fuego de Tierra", None, None),
    ("Rey de Bastos", "Fuego de Fuego", None, None), ("Sota de Oros", "Tierra de Tierra", None, None),
]
for es, elem, astro, extra in checks:
    r = corr(es)
    assert r["elemento"] == elem, (es, r["elemento"], elem)
    if astro: assert r["astro"] == astro, (es, r["astro"], astro)
    if extra: assert r["extra"] == extra, (es, r["extra"], extra)
print(f"OK  {len(checks)} casos de tu tabla coinciden")
assert corr("As de Copas")["astro"].startswith("Raíz de Agua")

# 3) 22 letras hebreas distintas y el mapeo a signos/planetas
letters = [c["corr"]["extra"] for c in CARDS if c["arcana"] == "mayor"]
assert len(set(letters)) == 22
print("OK  22 letras hebreas distintas")

# 4) validación independiente de los decanatos: cada signo aparece 3 veces y los regentes siguen el orden caldeo
pips = [c for c in CARDS if c["arcana"] == "menor" and 2 <= c["num"] <= 10]
assert len(pips) == 36
by_sign = Counter(c["corr"]["signs"][0] for c in pips)
assert set(by_sign.values()) == {3} and len(by_sign) == 12, by_sign
CHALDEAN = ["Saturno", "Júpiter", "Marte", "Sol", "Venus", "Mercurio", "Luna"]
ZODIAC = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]
# el 1.er decanato de Aries lo rige Marte y la secuencia continúa en orden caldeo a lo largo del zodiaco
idx = CHALDEAN.index("Marte")
expected = {}
for s in ZODIAC:
    expected[s] = []
    for _ in range(3):
        expected[s].append(CHALDEAN[idx % 7]); idx += 1
for s in ZODIAC:
    got = [c["corr"]["planets"][0] for c in sorted((c for c in pips if c["corr"]["signs"][0] == s), key=lambda c: c["num"])]
    assert got == expected[s], (s, got, expected[s])
print("OK  36 decanatos: 3 por signo y regentes en orden caldeo (validación independiente de tu tabla)")

# 5) los elementos del palo coinciden con el elemento del signo
SIGN_EL = {s: e for e, ss in K.TRIPLICITY.items() for s in ss}
for c in pips:
    assert SIGN_EL[c["corr"]["signs"][0]] == c["corr"]["elemento"], c["es"]
print("OK  el signo de cada pip pertenece al elemento de su palo")
print("\nOK: test_correspondences")
