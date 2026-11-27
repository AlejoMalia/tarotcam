"""Tarot de Marseille: names, printed numbers and meanings.

Meanings follow the usual Marseille approach: trumps and court cards read traditionally; pip cards, which show
no scene, read as the idea of their number applied to the domain of their suit. No astrological or Hebrew-letter
attributions are given: those belong to other traditions.
"""
from __future__ import annotations

from tarotcam import i18n
from tarotcam.carddata import decks

ROMAN = ["", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "VIIII", "X", "XI", "XII", "XIII", "XIIII", "XV",
         "XVI", "XVII", "XVIII", "XVIIII", "XX", "XXI"]
# id interno -> (francés, español, inglés)
MAJOR_NAMES = {
    0: ("Le Mat", "El Loco", "The Fool"), 1: ("Le Bateleur", "El Mago", "The Magician"),
    2: ("La Papesse", "La Papisa", "The Popess"), 3: ("L'Impératrice", "La Emperatriz", "The Empress"),
    4: ("L'Empereur", "El Emperador", "The Emperor"), 5: ("Le Pape", "El Papa", "The Pope"),
    6: ("L'Amoureux", "El Enamorado", "The Lover"), 7: ("Le Chariot", "El Carro", "The Chariot"),
    8: ("La Force", "La Fuerza", "Strength"), 9: ("L'Hermite", "El Ermitaño", "The Hermit"),
    10: ("La Roue de Fortune", "La Rueda de la Fortuna", "Wheel of Fortune"),
    11: ("La Justice", "La Justicia", "Justice"), 12: ("Le Pendu", "El Colgado", "The Hanged Man"),
    13: ("L'Arcane sans nom", "El Arcano sin nombre", "The Nameless Arcanum"),
    14: ("Tempérance", "La Templanza", "Temperance"), 15: ("Le Diable", "El Diablo", "The Devil"),
    16: ("La Maison Dieu", "La Casa de Dios", "The House of God"), 17: ("L'Étoile", "La Estrella", "The Star"),
    18: ("La Lune", "La Luna", "The Moon"), 19: ("Le Soleil", "El Sol", "The Sun"),
    20: ("Le Jugement", "El Juicio", "Judgement"), 21: ("Le Monde", "El Mundo", "The World"),
}
# palo -> (francés, dominio ES, dominio EN)
SUITS = {
    "Bastos": ("Bâton", "energía creativa", "creative energy"),
    "Copas": ("Coupe", "amor y emociones", "love and emotion"),
    "Espadas": ("Épée", "pensamiento y decisión", "thought and decision"),
    "Oros": ("Denier", "dinero, cuerpo y materia", "money, body and matter"),
}
# número -> (derecho ES, revés ES, derecho EN, revés EN)
NUMBERS = {
    1: ("Potencial, nuevo comienzo", "Potencial bloqueado, inicio aplazado", "Potential, new beginning", "Blocked potential, delayed start"),
    2: ("Gestación, paciencia, acumulación", "Estancamiento, indecisión", "Gestation, patience, accumulation", "Stagnation, indecision"),
    3: ("Impulso creador, expansión", "Dispersión, impulso sin dirección", "Creative burst, expansion", "Scattering, aimless drive"),
    4: ("Estabilidad, base firme", "Rigidez, encierro", "Stability, solid ground", "Rigidity, confinement"),
    5: ("Apertura, nuevo ideal", "Crisis de rumbo, duda", "Opening, new ideal", "Crisis of direction, doubt"),
    6: ("Armonía, disfrute, elección", "Complacencia, desarmonía", "Harmony, enjoyment, choice", "Complacency, disharmony"),
    7: ("Acción en el mundo, avance", "Precipitación, conflicto", "Action in the world, progress", "Haste, conflict"),
    8: ("Equilibrio, orden logrado", "Bloqueo, desequilibrio", "Balance, achieved order", "Block, imbalance"),
    9: ("Transición, soltar lo conocido", "Miedo al cambio, aislamiento", "Transition, leaving the known", "Fear of change, isolation"),
    10: ("Totalidad, cierre de un ciclo", "Saturación, final aplazado", "Wholeness, end of a cycle", "Overload, postponed ending"),
}
# ajustes de los triunfos que en Marsella se leen de forma propia (derecho ES, revés ES, derecho EN, revés EN)
MAJOR_MEANINGS = {
    2: ("Estudio, reserva, saber en gestación.", "Secretos, frialdad, saber retenido.",
        "Study, reserve, knowledge in gestation.", "Secrets, coldness, withheld knowledge."),
    5: ("Consejo, guía, puente entre ideas.", "Dogma, mala guía, incomunicación.",
        "Counsel, guidance, bridge between ideas.", "Dogma, poor guidance, lack of communication."),
    6: ("Elección del corazón, vínculo, deseo.", "Indecisión, conflicto de afectos.",
        "Choice of the heart, bond, desire.", "Indecision, conflicting affections."),
    13: ("Corte, transformación profunda, limpieza.", "Resistencia al cambio, rabia contenida.",
         "Cut, deep transformation, clearing out.", "Resistance to change, held anger."),
    16: ("Liberación súbita, salir del encierro, celebración.", "Derrumbe temido, encierro, golpe de orgullo.",
         "Sudden release, breaking out, celebration.", "Feared collapse, confinement, blow to pride."),
}
COURT_FR = {11: "Valet", 12: "Cavalier", 13: "Reine", 14: "Roi"}
PIP_FR = {1: "As", 2: "Deux", 3: "Trois", 4: "Quatre", 5: "Cinq", 6: "Six", 7: "Sept", 8: "Huit", 9: "Neuf", 10: "Dix"}


def build(rws_cards: list[dict]) -> list[dict]:
    out = []
    for base in rws_cards:
        c = dict(base, system="marseille")
        cid = c["id"]
        en_up, en_rev = i18n_base(cid)
        if c["arcana"] == "mayor":
            c["fr"], c["es"], c["en"] = MAJOR_NAMES[cid]
            c["num"] = decks.marseille_number(cid)
            if cid in MAJOR_MEANINGS:
                c["upright"], c["reversed"], en_up, en_rev = MAJOR_MEANINGS[cid]
        else:
            suit_fr, dom_es, dom_en = SUITS[c["suit"]]
            joiner = "d'" if suit_fr[0] in "ÉAEIOU" else "de "
            rank = COURT_FR.get(c["num"]) or PIP_FR[c["num"]]
            c["fr"] = f"{rank} {joiner}{suit_fr}"
            if not c.get("court"):
                up, rev, up_en, rev_en = NUMBERS[c["num"]]
                c["upright"], c["reversed"] = f"{up}, {dom_es}.", f"{rev}, {dom_es}."
                en_up, en_rev = f"{up_en}, {dom_en}.", f"{rev_en}, {dom_en}."
        c["en_up"], c["en_rev"] = en_up, en_rev
        c["corr"] = corr(c, "es")
        out.append(c)
    return out


def i18n_base(card_id: int):
    from tarotcam.carddata import cards_en
    return cards_en.meanings(card_id)


def corr(card: dict, lang: str) -> dict:
    """Datos de la ficha: número, elemento, nombre francés y tradición. Sin planetas ni signos."""
    en = lang == "en"
    element = i18n.TERMS.get(card["element"], card["element"]) if en else card["element"]
    if card["arcana"] == "mayor":
        number = ROMAN[card["num"]] or ("unnumbered" if en else "sin número")
        extra = "Trump" if en else "Triunfo"
    elif card.get("court"):
        number = card["fr"].split()[0]
        extra = "Court card" if en else "Figura"
    else:
        number = str(card["num"])
        extra = NUMBERS[card["num"]][2 if en else 0].split(",")[0]
    return dict(numero=number, elemento=element, astro_label="FRENCH NAME" if en else "EN FRANCÉS", astro=card["fr"],
                extra_label="Tradition" if en else "Tradición", extra=extra, glyph="", planets=[], signs=[],
                short_astro=card["fr"], short_extra=extra)
