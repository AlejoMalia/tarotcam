"""Correspondencias de cada carta (sistema Golden Dawn / Rider-Waite-Smith).

Cada carta lleva 4 datos:
  número · elemento · correspondencia astrológica · extra
  extra = letra hebrea (mayores) | decanato (pips 2-10) | raíz del elemento (ases) | mezcla elemental (cortes)

Variantes: Thoth intercambia algunas letras (p. ej. Emperador/Estrella); aquí se sigue la atribución Waite/RWS.
Cortes: Sota = Tierra, Caballero = Aire, Reina = Agua, Rey = Fuego (+ elemento del palo). Los rangos zodiacales de
Rey, Reina y Caballero son los clásicos de la Golden Dawn (Rey = su 'Caballero', Caballero = su 'Príncipe').
"""
from __future__ import annotations

from tarotcam import i18n

# ---- arcanos mayores: (letra hebrea, glifo, correspondencia, planeta, signo) ---------------------------------
MAJOR = [
    ("Aleph", "א", "Aire (moderno: Urano)", "Urano", None),
    ("Beth", "ב", "Mercurio", "Mercurio", None),
    ("Gimel", "ג", "Luna", "Luna", None),
    ("Daleth", "ד", "Venus", "Venus", None),
    ("Heh", "ה", "Aries", None, "Aries"),
    ("Vav", "ו", "Tauro", None, "Tauro"),
    ("Zayin", "ז", "Géminis", None, "Géminis"),
    ("Cheth", "ח", "Cáncer", None, "Cáncer"),
    ("Teth", "ט", "Leo", None, "Leo"),
    ("Yod", "י", "Virgo", None, "Virgo"),
    ("Kaph", "כ", "Júpiter", "Júpiter", None),
    ("Lamed", "ל", "Libra", None, "Libra"),
    ("Mem", "מ", "Agua (moderno: Neptuno)", "Neptuno", None),
    ("Nun", "נ", "Escorpio", None, "Escorpio"),
    ("Samekh", "ס", "Sagitario", None, "Sagitario"),
    ("Ayin", "ע", "Capricornio", None, "Capricornio"),
    ("Peh", "פ", "Marte", "Marte", None),
    ("Tzaddi", "צ", "Acuario", None, "Acuario"),
    ("Qoph", "ק", "Piscis", None, "Piscis"),
    ("Resh", "ר", "Sol", "Sol", None),
    ("Shin", "ש", "Fuego (moderno: Plutón)", "Plutón", None),
    ("Tav", "ת", "Saturno", "Saturno", None),
]

# ---- pips 2-10: (planeta, signo) por palo; el decanato es el índice dentro del signo (3 por signo) ------------
PIPS = {
    "Bastos": [("Marte", "Aries"), ("Sol", "Aries"), ("Venus", "Aries"),
               ("Saturno", "Leo"), ("Júpiter", "Leo"), ("Marte", "Leo"),
               ("Mercurio", "Sagitario"), ("Luna", "Sagitario"), ("Saturno", "Sagitario")],
    "Copas": [("Venus", "Cáncer"), ("Mercurio", "Cáncer"), ("Luna", "Cáncer"),
              ("Marte", "Escorpio"), ("Sol", "Escorpio"), ("Venus", "Escorpio"),
              ("Saturno", "Piscis"), ("Júpiter", "Piscis"), ("Marte", "Piscis")],
    "Espadas": [("Luna", "Libra"), ("Saturno", "Libra"), ("Júpiter", "Libra"),
                ("Venus", "Acuario"), ("Mercurio", "Acuario"), ("Luna", "Acuario"),
                ("Júpiter", "Géminis"), ("Marte", "Géminis"), ("Sol", "Géminis")],
    "Oros": [("Júpiter", "Capricornio"), ("Marte", "Capricornio"), ("Sol", "Capricornio"),
             ("Mercurio", "Tauro"), ("Luna", "Tauro"), ("Saturno", "Tauro"),
             ("Sol", "Virgo"), ("Venus", "Virgo"), ("Mercurio", "Virgo")],
}
DECAN_RANGE = {1: "0°–10°", 2: "10°–20°", 3: "20°–30°"}

SUIT_ELEMENT = {"Bastos": "Fuego", "Copas": "Agua", "Espadas": "Aire", "Oros": "Tierra"}
TRIPLICITY = {"Fuego": ("Aries", "Leo", "Sagitario"), "Agua": ("Cáncer", "Escorpio", "Piscis"),
              "Aire": ("Libra", "Acuario", "Géminis"), "Tierra": ("Capricornio", "Tauro", "Virgo")}

# ---- cortes -----------------------------------------------------------------------------------------------
COURT_NAME = {11: "Sota", 12: "Caballero", 13: "Reina", 14: "Rey"}
COURT_ELEMENT = {11: "Tierra", 12: "Aire", 13: "Agua", 14: "Fuego"}
# rangos zodiacales Golden Dawn (los tres cortes con rango; la Sota no tiene signo propio)
COURT_SPAN = {
    ("Bastos", 14): ("20° Escorpio", "20° Sagitario", ("Escorpio", "Sagitario")),
    ("Bastos", 13): ("20° Piscis", "20° Aries", ("Piscis", "Aries")),
    ("Bastos", 12): ("20° Cáncer", "20° Leo", ("Cáncer", "Leo")),
    ("Copas", 14): ("20° Acuario", "20° Piscis", ("Acuario", "Piscis")),
    ("Copas", 13): ("20° Géminis", "20° Cáncer", ("Géminis", "Cáncer")),
    ("Copas", 12): ("20° Libra", "20° Escorpio", ("Libra", "Escorpio")),
    ("Espadas", 14): ("20° Tauro", "20° Géminis", ("Tauro", "Géminis")),
    ("Espadas", 13): ("20° Virgo", "20° Libra", ("Virgo", "Libra")),
    ("Espadas", 12): ("20° Capricornio", "20° Acuario", ("Capricornio", "Acuario")),
    ("Oros", 14): ("20° Leo", "20° Virgo", ("Leo", "Virgo")),
    ("Oros", 13): ("20° Sagitario", "20° Capricornio", ("Sagitario", "Capricornio")),
    ("Oros", 12): ("20° Aries", "20° Tauro", ("Aries", "Tauro")),
}

# ---- significado breve de planetas y signos (para la lectura) ----------------------------------------------
PLANET_MEANING = {
    "Sol": "vitalidad e identidad", "Luna": "emociones e instinto", "Mercurio": "mente y comunicación",
    "Venus": "amor y valores", "Marte": "energía y conflicto", "Júpiter": "expansión y fortuna",
    "Saturno": "estructura y límites", "Urano": "ruptura e independencia", "Neptuno": "sueño y disolución",
    "Plutón": "transformación profunda",
}
SIGN_MEANING = {
    "Aries": "iniciativa", "Tauro": "constancia y materia", "Géminis": "dualidad y curiosidad",
    "Cáncer": "hogar y emoción", "Leo": "orgullo y creatividad", "Virgo": "análisis y servicio",
    "Libra": "equilibrio y vínculo", "Escorpio": "intensidad y transformación", "Sagitario": "búsqueda y expansión",
    "Capricornio": "ambición y estructura", "Acuario": "ideas e independencia", "Piscis": "sensibilidad y disolución",
}


PLANET_MEANING_EN = {
    "Sol": "vitality and identity", "Luna": "emotion and instinct", "Mercurio": "mind and communication",
    "Venus": "love and values", "Marte": "drive and conflict", "Júpiter": "expansion and fortune",
    "Saturno": "structure and limits", "Urano": "rupture and independence", "Neptuno": "dream and dissolution",
    "Plutón": "deep transformation",
}
SIGN_MEANING_EN = {
    "Aries": "initiative", "Tauro": "constancy and matter", "Géminis": "duality and curiosity",
    "Cáncer": "home and emotion", "Leo": "pride and creativity", "Virgo": "analysis and service",
    "Libra": "balance and bonds", "Escorpio": "intensity and transformation", "Sagitario": "quest and expansion",
    "Capricornio": "ambition and structure", "Acuario": "ideas and independence", "Piscis": "sensitivity and dissolution",
}


def build(card: dict, lang: str = "es") -> dict:
    """Correspondencias de una carta. Claves: numero, elemento, astro, extra_label, extra, glyph, planets, signs,
    short_astro, short_extra. planets/signs son SIEMPRE identificadores canónicos (ES) para el motor."""
    en = lang == "en"

    def L(e, s):
        return e if en else s

    def T(x):
        return i18n.TERMS.get(x, x) if en else x

    cid, arcana, suit, num = card["id"], card["arcana"], card.get("suit"), card["num"]
    if arcana == "mayor":
        name, glyph, astro, planet, sign = MAJOR[cid]
        if en:
            base, _, modern = astro.partition(" (moderno: ")
            astro = T(base) + (f" (modern: {T(modern.rstrip(')'))})" if modern else "")
        return dict(numero=str(cid), elemento=T(card["element"]), astro=astro,
                    extra_label=L("Hebrew letter", "Letra hebrea"), extra=name, glyph=glyph,
                    planets=[planet] if planet else [], signs=[sign] if sign else [],
                    short_astro=astro.split(" (")[0], short_extra=name)
    elem = SUIT_ELEMENT[suit]
    if num == 1:
        signs = ", ".join(T(x) for x in TRIPLICITY[elem])
        return dict(numero="1", elemento=T(elem),
                    astro=L(f"Root of {T(elem)} (no decan)", f"Raíz de {elem} (sin decanato)"),
                    extra_label=L("Element signs", "Signos del elemento"), extra=signs, glyph="",
                    planets=[], signs=[], short_astro=L(f"Root of {T(elem)}", f"Raíz de {elem}"),
                    short_extra=L(f"Pure {T(elem)}", f"{elem} puro"))
    if 2 <= num <= 10:
        planet, sign = PIPS[suit][num - 2]
        dec = (num - 2) % 3 + 1
        ordinal = L({1: "1st", 2: "2nd", 3: "3rd"}[dec], f"{dec}.º")
        astro = L(f"{T(planet)} in {T(sign)}", f"{planet} en {sign}")
        return dict(numero=str(num), elemento=T(elem), astro=astro,
                    extra_label=L("Decan", "Decanato"),
                    extra=L(f"{ordinal} · {DECAN_RANGE[dec]} of {T(sign)} · ruler {T(planet)}",
                            f"{ordinal} · {DECAN_RANGE[dec]} de {sign} · regente {planet}"),
                    glyph="", planets=[planet], signs=[sign], short_astro=astro,
                    short_extra=L(f"{ordinal} decan {DECAN_RANGE[dec]}", f"Dec. {ordinal} {DECAN_RANGE[dec]}"))
    rank = COURT_NAME[num]
    blend = L(f"{T(COURT_ELEMENT[num])} of {T(elem)}", f"{COURT_ELEMENT[num]} de {elem}")
    if num == 11:
        astro, signs = L("No sign of its own (element quadrant)", "Sin signo propio (cuadrante del elemento)"), []
        short = L("Quadrant", "Cuadrante")
    else:
        d1, d2, signs = COURT_SPAN[(suit, num)]
        astro = " – ".join(f"20° {T(x)}" for x in signs)
        short = " – ".join(T(x) for x in signs)
    return dict(numero=f"{num} · {T(rank)}", elemento=blend, astro=astro,
                extra_label=L("Elemental blend", "Mezcla elemental"),
                extra=L(f"{T(COURT_ELEMENT[num])} (rank) + {T(elem)} (suit)",
                        f"{COURT_ELEMENT[num]} (rango) + {elem} (palo)"),
                glyph="", planets=[], signs=list(signs), short_astro=short, short_extra=blend)


def localized(card: dict) -> dict:
    return build(card, i18n.lang())


def meaning_of(tag: str) -> str:
    """Significado breve de un planeta o signo en el idioma actual."""
    if i18n.lang() == "en":
        return PLANET_MEANING_EN.get(tag) or SIGN_MEANING_EN.get(tag, "")
    return PLANET_MEANING.get(tag) or SIGN_MEANING.get(tag, "")


def annotate(cards: list[dict]) -> None:
    for c in cards:
        c["corr"] = build(c)
