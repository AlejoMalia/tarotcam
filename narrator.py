"""Narrative writer: turns the engine's analysis into flowing prose instead of separate blocks.

Deterministic variation: phrasing is chosen from banks with a seed derived from the cards on the table, so the
same table always reads the same, different tables read differently, and no template or keyword repeats within
one reading. English and Spanish. An optional focus (love, career, money, spiritual) adds area texts from the
open datasets (English) or frames the keywords around that area.
"""
from __future__ import annotations

import hashlib
import random
import re

import chartlink
import correspondences
import datasets
import i18n
import reading
import synthesis
from cards import BY_ID, keywords
from i18n import L, card_name
from semantics import tension_text, theme_name, theme_text

FOCI = ("general", "love", "career", "money", "spiritual")
FOCUS_NAME = {"general": ("general", "general"), "love": ("love", "amor"), "career": ("work", "trabajo"),
              "money": ("money", "dinero"), "spiritual": ("inner life", "vida interior")}


class Voice:
    """Chooses phrasings without repeating one inside a reading, and keywords without echoing them."""

    def __init__(self, seed: str):
        self.rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:12], 16))
        self.used: dict[str, list[int]] = {}
        self.words: set[str] = set()

    def pick(self, bank: str, options: list[tuple[str, str]], **kw) -> str:
        used = self.used.setdefault(bank, [])
        free = [i for i in range(len(options)) if i not in used]
        if not free:                                      # banco agotado: reutilizar el menos reciente
            free = [used.pop(0)]
        i = self.rng.choice(free)
        used.append(i)
        return L(*options[i]).format(**kw)

    def ideas(self, cs, k: int = 2) -> str:
        """k palabras clave de la carta que aún no hayan salido en esta lectura."""
        pool = keywords(cs.card, cs.reversed, 6)
        fresh = [w for w in pool if w not in self.words] or pool
        chosen = fresh[:k]
        self.words.update(chosen)
        return and_list(chosen)


def and_list(words: list[str]) -> str:
    if len(words) <= 1:
        return "".join(words)
    last = words[-1]
    if i18n.lang() == "es":
        conj = "e" if re.match(r"^h?i(?![aeou])", last) else "y"
    else:
        conj = "and"
    return f"{', '.join(words[:-1])} {conj} {last}"


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def nm(cs) -> str:
    """Nombre dentro de una frase: en español 'la Torre', 'el Sol'; en inglés 'The Tower'."""
    name = card_name(cs.card)
    if i18n.lang() == "es":
        name = re.sub(r"^(El|La|Los|Las) ", lambda m: m.group(1).lower() + " ", name)
    return name


# ----------------------------------------------------------------------------- bancos de frases
MOOD = {
    "up": ("a bright, supportive", "luminoso y favorable"),
    "down": ("a demanding", "exigente"),
    "mid": ("a balanced, mixed", "matizado, de luces y sombras"),
}
OPENING = [
    ("What these {n} cards put on the table, before anything else, is {theme}. The overall register is {mood} one.",
     "Lo que estas {n} cartas ponen sobre la mesa, antes que nada, es {theme}. El registro general es {mood}."),
    ("Taken together, the {n} cards speak chiefly of {theme}, in {mood} key.",
     "Vistas en conjunto, las {n} cartas hablan sobre todo de {theme}, en un tono {mood}."),
    ("The centre of gravity here is {theme}. Across {n} cards the atmosphere is {mood} one.",
     "El centro de gravedad aquí es {theme}. A lo largo de las {n} cartas el ambiente es {mood}."),
    ("{Theme} is the subject that organises this spread of {n} cards, and it arrives in {mood} mood.",
     "{Theme} es el asunto que ordena esta tirada de {n} cartas, y llega con un aire {mood}."),
]
SINGLE = [
    ("{card} stands alone, and that concentrates the message: it speaks of {ideas}.",
     "{Card} aparece en solitario, y eso concentra el mensaje: habla de {ideas}."),
    ("A single card, {card}, answers. Its word is {ideas}.",
     "Responde una sola carta, {card}. Su palabra es {ideas}."),
    ("The table offers just {card}, so everything turns on {ideas}.",
     "La mesa ofrece únicamente {card}, así que todo gira en torno a {ideas}."),
]
MAJORS = [
    ("With so many major arcana, this is not a passing matter: it touches something structural.",
     "Con tantos arcanos mayores, no es un asunto pasajero: toca algo estructural."),
    ("The weight of the major arcana suggests a chapter that matters more than it may seem.",
     "El peso de los arcanos mayores sugiere un capítulo más importante de lo que parece."),
]
MINORS = [
    ("Only minor arcana have appeared, which places the question firmly in everyday decisions.",
     "Solo han salido arcanos menores, lo que sitúa la cuestión en las decisiones de cada día."),
    ("There are no major arcana: this is practical ground, where small choices do the work.",
     "No hay arcanos mayores: es terreno práctico, donde cuentan las decisiones pequeñas."),
]
LEADS = {
    "past": [("Looking back,", "Mirando atrás,"), ("The story starts further back:", "La historia empieza antes:"),
             ("Where all this comes from,", "En el origen de todo esto,")],
    "present": [("Right now,", "Ahora mismo,"), ("In the present,", "En el presente,"),
                ("At the heart of the moment,", "En el centro del momento,")],
    "future": [("Further ahead,", "Más adelante,"), ("Looking forward,", "Hacia delante,"),
               ("As things continue,", "Si el curso se mantiene,")],
    "situation": [("The starting point is clear:", "El punto de partida es claro:"), ("As matters stand,", "Tal como están las cosas,")],
    "outcome": [("Where it leads,", "Hacia donde conduce,"), ("As for the outcome,", "En cuanto al desenlace,"),
                ("It all flows toward this:", "Todo desemboca aquí:")],
    "challenge": [("What stands in the way, or asks for work,", "Lo que se interpone, o pide trabajo,"),
                  ("The counterweight:", "El contrapeso:")],
    "centro": [("At the core,", "En el núcleo,"), ("In the middle of it all,", "En medio de todo,")],
    "arriba": [("In your conscious aims,", "En lo que persigues conscientemente,"), ("Above, in plain view,", "Arriba, a la vista,")],
    "abajo": [("Underneath, less acknowledged,", "Por debajo, menos reconocido,"), ("At the root,", "En la raíz,")],
    "izq": [("What is on its way out:", "Lo que se está yendo:"), ("Behind you,", "A tu espalda,")],
    "der": [("What is approaching:", "Lo que se acerca:"), ("On the way in,", "En camino,")],
    "c2": [("Crossing it,", "Cruzándose,"), ("The obstacle takes this shape:", "El obstáculo toma esta forma:")],
    "c7": [("As for you,", "En cuanto a ti,"), ("Your own stance:", "Tu propia posición:")],
    "c8": [("Around you,", "A tu alrededor,"), ("The surroundings:", "El entorno:")],
    "c9": [("Between hope and fear,", "Entre la esperanza y el miedo,")],
    "obstacle": [("The difficulty:", "La dificultad:")],
    "first": [("To begin,", "Para empezar,"), ("First,", "En primer lugar,"), ("Opening the line,", "Abriendo la tirada,")],
    "next": [("Next,", "A continuación,"), ("Alongside this,", "Junto a esto,"), ("Then,", "Después,"),
             ("Further along,", "Más allá,"), ("In addition,", "Además,"), ("Meanwhile,", "Mientras tanto,"),
             ("Close by,", "Muy cerca,")],
}
KEY_TO_LEAD = {"c1": "centro", "c3": "abajo", "c4": "past", "c5": "arriba", "c6": "future", "c10": "outcome",
               "h1": "past", "h2": "present", "h3": "future", "h4": "c7", "h5": "c8", "h6": "obstacle",
               "h7": "outcome", "unica": "present"}
UPRIGHT = [
    ("{card} brings {ideas}.", "{card} trae {ideas}."),
    ("{card} speaks of {ideas}.", "{card} habla de {ideas}."),
    ("{card} points to {ideas}.", "{card} apunta a {ideas}."),
    ("{card} puts {ideas} in play.", "{card} pone en juego {ideas}."),
    ("{card} appears, carrying {ideas}.", "aparece {card}, que carga con {ideas}."),
    ("it is {card}, with its sense of {ideas}.", "está {card}, con su sentido de {ideas}."),
    ("{card} opens the door to {ideas}.", "{card} abre la puerta a {ideas}."),
]
REVERSED = [
    ("{card} turns up reversed, which suggests {ideas}.", "{card} sale al revés, lo que sugiere {ideas}."),
    ("{card}, upside down, warns of {ideas}.", "{card}, del revés, advierte de {ideas}."),
    ("an inverted {card} hints at {ideas}.", "{card} invertida o invertido deja ver {ideas}."),
    ("{card} is blocked or turned inward, pointing to {ideas}.", "{card} aparece bloqueado o vuelto hacia dentro, señal de {ideas}."),
]
REVERSED_ES_SAFE = [
    ("", "{card} sale al revés, lo que sugiere {ideas}."),
    ("", "{card}, del revés, advierte de {ideas}."),
    ("", "con {card} boca abajo asoman {ideas}."),
    ("", "{card}, en posición invertida, deja ver {ideas}."),
]
COMPANION = [
    ("Beside it, {card} adds {ideas}.", "A su lado, {card} añade {ideas}."),
    ("{card} deepens this with {ideas}.", "{card} lo ahonda con {ideas}."),
    ("There is also {card}, which contributes {ideas}.", "Está además {card}, que aporta {ideas}."),
    ("{card} widens the picture towards {ideas}.", "{card} amplía el cuadro hacia {ideas}."),
]
COMPANION_REV = [
    ("In contrast, a reversed {card} brings {ideas}.", "En cambio, {card} al revés introduce {ideas}."),
    ("{card}, reversed, complicates it with {ideas}.", "{card}, invertida su posición, lo complica con {ideas}."),
]
AREA = {      # (inglés: texto del dataset) (español: idea clave de la carta llevada al área)
    "love": [("In matters of the heart, think of {t}.", "Llevado al amor, el foco está en {t}."),
             ("For love, that can look like {t}.", "En lo afectivo, esto invita a mirar {t}."),
             ("Where relationships are concerned: {t}.", "En la relación, la palabra a tener presente es {t}.")],
    "career": [("At work, think of {t}.", "Llevado al trabajo, el foco está en {t}."),
               ("Professionally, that can look like {t}.", "En lo profesional, esto invita a mirar {t}."),
               ("In your working life: {t}.", "En tu actividad, la palabra a tener presente es {t}.")],
    "money": [("With money, think of {t}.", "Llevado al dinero, el foco está en {t}."),
              ("Materially, that can look like {t}.", "En lo material, esto invita a mirar {t}."),
              ("In your finances: {t}.", "En tus cuentas, la palabra a tener presente es {t}.")],
    "spiritual": [("Inwardly, think of {t}.", "Llevado a lo interior, el foco está en {t}."),
                  ("On the inner path, that can look like {t}.", "En el camino interior, esto invita a mirar {t}."),
                  ("For your inner life: {t}.", "Por dentro, la palabra a tener presente es {t}.")],
}
TENSION = [
    ("The real knot lies between {a} and {b}: {ca} pulls one way while {cb} pulls the other. {Why}.",
     "El verdadero nudo está entre {a} y {b}: {ca} tira hacia un lado y {cb} hacia el otro. {Why}."),
    ("There is a tug-of-war here. {Ca} stands for {a}; {cb}, for {b}. {Why}.",
     "Hay un tira y afloja. {Ca} representa {a}; {cb}, {b}. {Why}."),
    ("Not everything points the same way: {a}, through {ca}, meets {b}, through {cb}. {Why}.",
     "No todo apunta en la misma dirección: {a}, por medio de {ca}, se topa con {b}, que llega con {cb}. {Why}."),
]
THREAD = [
    ("{Theme} keeps coming back, through {cards}, which makes it hard to ignore.",
     "{Theme} vuelve una y otra vez, a través de {cards}, y cuesta pasarlo por alto."),
    ("A second thread runs underneath: {theme}, carried by {cards}.",
     "Por debajo corre un segundo hilo: {theme}, que sostienen {cards}."),
    ("Notice how {cards} agree on one thing, {theme}.", "Fíjate en que {cards} coinciden en algo: {theme}."),
]
ELEMENT = [
    ("{el} sets the temperature, so {sense} come to the fore.", "El elemento {el} marca la temperatura: pasan a primer plano {sense}."),
    ("The dominant element is {el}; expect {sense} to lead.", "Domina el elemento {el}; es previsible que manden {sense}."),
]
ASTRO = [
    ("{tag} links {cards}, adding a note of {sense}.", "{tag} enlaza {cards} y añade un matiz de {sense}."),
    ("Astrologically, {cards} share {tag}: {sense}.", "En clave astrológica, {cards} comparten {tag}: {sense}."),
]
TREND = {
    "up": [("From past to future the current clearly improves.", "Del pasado al futuro la corriente mejora con claridad."),
           ("The movement is upward: what comes is kinder than what was.", "El movimiento es ascendente: lo que viene es más amable que lo que fue.")],
    "down": [("The road ahead asks for more than the one behind.", "El camino que viene pide más que el recorrido.")],
}
OUTCOME = [
    ("If a single card sums up where this is heading, it is {card}: {ideas}.",
     "Si una carta resume hacia dónde va esto, es {card}: {ideas}."),
    ("The thread ends at {card}, with {ideas} as its promise or warning.",
     "El hilo termina en {card}, con {ideas} como promesa o advertencia."),
    ("Watch {card} closely; the outcome is coloured by {ideas}.",
     "Conviene mirar de cerca {card}: el desenlace se tiñe de {ideas}."),
]
COUNSEL = [
    ("If you take one thing away, let it be this. {Advice}", "Si te llevas una sola idea, que sea esta. {Advice}"),
    ("Here is the practical side. {Advice}", "Vamos a lo práctico. {Advice}"),
    ("What to do with all this? {Advice}", "¿Qué hacer con todo esto? {Advice}"),
]
QUINT = [
    ("Underlying it all, the numbers reduce to {card}, a quiet reminder of {ideas}.",
     "En el fondo de todo, los números se reducen a {card}, un recordatorio discreto de {ideas}."),
    ("Added together, the cards resolve into {card}: {ideas}.",
     "Sumadas, las cartas se resuelven en {card}: {ideas}."),
]


def _lead_key(c, layout) -> str:
    if c.key in LEADS:
        return c.key
    if c.key in KEY_TO_LEAD:
        return KEY_TO_LEAD[c.key]
    if c.group is not None:
        groups = len({s.group for s in layout.slots if s.group is not None})
        if groups == 3:
            return ("past", "present", "future")[c.group]
        if groups == 2 and layout.kind == "rows":
            return ("situation", "outcome")[c.group]
    if c.key in ("l1", "e1") and len(layout.slots) == 2:
        return "situation"
    if c.key in ("l2", "e2") and len(layout.slots) == 2:
        return "challenge"
    return "next"


def _card_sentence(v: Voice, c, focus: str) -> str:
    if c.reversed:
        bank = REVERSED_ES_SAFE if i18n.lang() == "es" else REVERSED
        return v.pick("reversed", bank, card=nm(c), ideas=v.ideas(c))
    return v.pick("upright", UPRIGHT, card=nm(c), ideas=v.ideas(c))


def _area_sentence(v: Voice, c, focus: str) -> str:
    if focus == "general":
        return ""
    if i18n.lang() == "en":
        text = datasets.area_text(c.card["id"], focus, c.reversed)
        if not text:
            return ""
        text = re.split(r"(?<=[.!?])\s+", text)[0].rstrip(".!?")     # una sola idea, no un párrafo
        if "," in text and ". " not in text and len(text.split(",")) > 2:      # listas: dos ideas
            text = and_list([p.strip() for p in text.split(",")][:2])
        return v.pick("area", AREA[focus], t=text[:1].lower() + text[1:])
    return v.pick("area", AREA[focus], t=v.ideas(c, 1))


def _story(v: Voice, layout, cs, focus: str) -> list[str]:
    """Párrafos que recorren las posiciones."""
    groups: list[list] = []
    for c in cs:
        if groups and c.group is not None and groups[-1][0].group == c.group:
            groups[-1].append(c)
        else:
            groups.append([c])
    detail_budget = 3 if i18n.lang() == "en" else 2      # frases de área: pocas, para no saturar
    sentences = []
    for g in groups:
        lead_card = max(g, key=lambda c: c.weight)
        ordered = [lead_card] + [c for c in g if c is not lead_card]
        key = _lead_key(lead_card, layout)
        if key == "next" and not sentences:
            key = "first"
        lead = v.pick("lead-" + key, LEADS[key])
        first = _card_sentence(v, lead_card, focus)
        part = [f"{lead} {first}"]
        for k, c in enumerate(ordered[1:]):
            if k < 3:
                bank, key = (COMPANION_REV, "companion-rev") if c.reversed else (COMPANION, "companion")
                part.append(v.pick(key, bank, card=nm(c), ideas=v.ideas(c, 2 if len(cs) <= 6 else 1)))
        rest = ordered[4:]
        if rest:
            names = and_list([nm(c) for c in rest])
            part.append(L(f"{names} complete this part of the picture.", f"Completan esta parte {names}."))
        if detail_budget > 0:
            area = _area_sentence(v, lead_card, focus)
            if area:
                part.append(area)
                detail_budget -= 1
        sentences.append(" ".join(cap(p) for p in part))
    # agrupar en uno o dos párrafos legibles
    if len(sentences) <= 3:
        return [" ".join(sentences)]
    mid = (len(sentences) + 1) // 2
    return [" ".join(sentences[:mid]), " ".join(sentences[mid:])]


def compose(layout, focus: str = "general", chart=None) -> list[str]:
    """-> lista de párrafos en el idioma actual. chart: carta natal opcional (natal.Chart)."""
    cs = reading._states(layout)
    if not cs:
        return [L("Place cards in front of the camera and the reading will begin to take shape.",
                  "Coloca cartas frente a la cámara y la lectura empezará a tomar forma.")]
    n = len(cs)
    seed = layout.kind + "|" + "|".join(f"{c.card['id']}{'r' if c.reversed else 'u'}{c.key}" for c in cs) + "|" + focus
    v = Voice(seed)
    a = synthesis.analyze(layout, cs)
    total = sum(c.weight for c in cs)
    pol = sum(c.polarity * c.weight for c in cs) / total
    mood = L(*MOOD["up" if pol > 0.25 else "down" if pol < -0.25 else "mid"])

    opening = []
    if focus != "general":
        area = L(*FOCUS_NAME[focus])
        opening.append(L(f"Read through the lens of {area}.", f"Leída desde el ángulo del {area}." if focus != "spiritual"
                         else "Leída desde la vida interior."))
    if n == 1:
        c = cs[0]
        opening.append(v.pick("single", SINGLE, card=nm(c), Card=cap(nm(c)), ideas=v.ideas(c, 3)))
        if c.reversed:
            opening.append(L("Reversed, it asks you to look at what is blocked or held inside.",
                             "Al estar al revés, invita a mirar lo que está bloqueado o contenido."))
        area = _area_sentence(v, c, focus)
        if area:
            opening.append(area)
        closing = [v.pick("counsel", COUNSEL, advice=synthesis.advice(a), Advice=synthesis.advice(a))]
        out = [cap(" ".join(opening))]
        if chart is not None:
            out = [f"{chart.name}, {_lower_first(out[0])}", _chart_paragraph(chart, cs)]
        return [_polish(p) for p in out + [" ".join(closing)]]

    theme = theme_text(a["top"]) if a["top"] else L("a transition", "una transición")
    opening.append(v.pick("opening", OPENING, n=n, theme=theme, Theme=cap(theme), mood=mood))
    majors = sum(c.card["arcana"] == "mayor" for c in cs)
    if majors * 2 > n:
        opening.append(v.pick("majors", MAJORS))
    elif majors == 0:
        opening.append(v.pick("minors", MINORS))
    paragraphs = [" ".join(opening)]
    paragraphs += _story(v, layout, cs, focus)

    weave = []
    if a["tensions"]:
        t, o, ca, cb, _ = a["tensions"][0]
        first = ca[0]
        second = next((c for c in cb if c is not first), cb[0])
        why = tension_text(frozenset({t, o}))
        weave.append(v.pick("tension", TENSION, a=theme_name(t), b=theme_name(o), ca=nm(first), Ca=cap(nm(first)),
                            cb=nm(second), Why=cap(why)))
    extra = [th for th in a["threads"] if th[0] != a["top"]]
    if extra:
        t, _, cards = extra[0]
        names = and_list([nm(c) for c in cards[:3]])
        weave.append(cap(v.pick("thread", THREAD, theme=theme_text(t), Theme=cap(theme_text(t)), cards=names)))
    weights: dict[str, float] = {}
    for c in cs:
        weights[c.element] = weights.get(c.element, 0) + c.weight
    top = max(weights, key=weights.get)
    if weights[top] / total >= 0.45:
        sense = L(*reading.ELEMENT_TEXT[top])
        weave.append(v.pick("element", ELEMENT, el=i18n.term(top), sense=sense))
    if a["astro"]:
        tag, names = a["astro"][0]
        linked = [nm(c) for c in cs if card_name(c.card) in names][:3]
        weave.append(cap(v.pick("astro", ASTRO, tag=i18n.term(tag), cards=and_list(linked),
                                sense=correspondences.meaning_of(tag))))
    if weave:
        paragraphs.append(" ".join(weave))
    if chart is not None:
        paragraphs[0] = f"{chart.name}, {_lower_first(paragraphs[0])}"
        paragraphs.append(_chart_paragraph(chart, cs))

    closing = []
    groups = sorted({c.group for c in cs if c.group is not None})
    if len(groups) == 3:
        d = reading._grp_pol(cs, 2) - reading._grp_pol(cs, 0)
        if abs(d) > 0.25:
            closing.append(v.pick("trend", TREND["up" if d > 0 else "down"]))
    end = reading._outcome(layout, cs)
    if n >= 3 and end is not None:
        closing.append(v.pick("outcome", OUTCOME, card=nm(end), ideas=v.ideas(end)))
    q, qc = reading._quintessence(cs)
    if n >= 3 and all(c.card["id"] != qc["id"] for c in cs):
        state = reading.CS(BY_ID[qc["id"]], False, "", "q", None, 1.0, cs[0].center)
        closing.append(v.pick("quint", QUINT, card=nm(state), ideas=v.ideas(state)))
    advice = synthesis.advice(a)
    if advice:
        closing.append(v.pick("counsel", COUNSEL, advice=advice[:1].lower() + advice[1:], Advice=advice))
    paragraphs.append(" ".join(closing))
    return [_polish(cap(p.strip())) for p in paragraphs if p.strip()]


def _lower_first(text: str) -> str:
    """Minúscula inicial al anteponer el nombre, salvo que empiece por un nombre de carta."""
    first = text.split(" ", 1)[0]
    if i18n.lang() == "en" and (first == "I" or text.startswith(tuple(c["en"] for c in BY_ID.values()))):
        return text
    return text[:1].lower() + text[1:]


def _chart_paragraph(chart, cs) -> str:
    weights: dict[str, float] = {}
    for c in cs:
        weights[c.element] = weights.get(c.element, 0) + c.weight
    top = max(weights, key=weights.get)
    notes = [t for _, _, t in chartlink.resonances(chart, cs, 3)]
    intro = L(f"Set against your chart ({chartlink.summary(chart)}):", f"Puesto frente a tu carta ({chartlink.summary(chart)}):")
    if not notes:
        intro = L(f"Your chart ({chartlink.summary(chart)}) has no direct contact with these cards.",
                  f"Tu carta ({chartlink.summary(chart)}) no tiene contacto directo con estas cartas.")
    return " ".join([intro] + notes + [chartlink.elements(chart, top)])


def _polish(text: str) -> str:
    """Contracciones del español con nombres de carta ('de el Sol' -> 'del Sol')."""
    if i18n.lang() == "es":
        text = re.sub(r"\bde el\b", "del", text)
        text = re.sub(r"\ba el\b", "al", text)
    return text
