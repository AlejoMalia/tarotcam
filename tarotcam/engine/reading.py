"""Motor de lectura global (determinista, sin IA): pesos + dignidades elementales + polaridad +
numerología + combinaciones + roles de posición. Se recalcula entero cada vez que cambia la mesa.

Modelo por carta: peso base (arcano mayor x1.8, corte x1.4, invertida x0.65) x peso de posición del rol,
elemento, número, polaridad (-1..+1; invertida = -0.5 x polaridad, es decir "bloqueada o en superación")
y palabras clave. Las interacciones se calculan entre cartas vecinas en la mesa (las 2 más cercanas de cada una).
Los textos salen en el idioma actual (i18n); los cálculos son idénticos en ambos.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt

import numpy as np

from tarotcam.astro import chartlink
from tarotcam.carddata import correspondences
from tarotcam.engine import synthesis
from tarotcam.carddata.cards import BY_ID, keywords, meaning
from tarotcam.i18n import L, card_name, join_and, plural, term
from tarotcam.engine.semantics import theme_text

POSITION_NAMES = {
    1: [("Message of the moment", "Mensaje del momento")],
    2: [("Situation", "Situación"), ("Challenge / advice", "Desafío / consejo")],
    3: [("Past", "Pasado"), ("Present", "Presente"), ("Future", "Futuro")],
}

# --- dignidades elementales: refuerza / amistoso / neutro / enemigo -------------------------
DIGNITY = {
    ("Fuego", "Fuego"): 1.6, ("Agua", "Agua"): 1.6, ("Aire", "Aire"): 1.6, ("Tierra", "Tierra"): 1.6,
    ("Fuego", "Aire"): 1.2, ("Aire", "Fuego"): 1.2, ("Agua", "Tierra"): 1.2, ("Tierra", "Agua"): 1.2,
    ("Fuego", "Tierra"): 0.3, ("Tierra", "Fuego"): 0.3, ("Aire", "Agua"): 0.3, ("Agua", "Aire"): 0.3,
    ("Fuego", "Agua"): -1.0, ("Agua", "Fuego"): -1.0, ("Aire", "Tierra"): -1.0, ("Tierra", "Aire"): -1.0,
}
ELEMENTS = ("Fuego", "Agua", "Aire", "Tierra")
ELEMENT_TEXT = {
    "Fuego": ("action, desire and initiative", "acción, deseo e iniciativa"),
    "Agua": ("emotion, bonds and intuition", "emociones, vínculos e intuición"),
    "Aire": ("thought, words and decisions", "pensamientos, palabras y decisiones"),
    "Tierra": ("money, work, body and the concrete", "dinero, trabajo, cuerpo y lo concreto"),
}
EXCESS = {
    "Fuego": ("excess of action: risk of burning out or acting without thinking.",
              "exceso de acción: riesgo de quemarse o de actuar sin pensar."),
    "Agua": ("excess of emotion: risk of drowning in feelings or avoiding reality.",
             "exceso de emoción: riesgo de ahogarse en los sentimientos o evitar la realidad."),
    "Aire": ("excess of mind: risk of overthinking, conflict or scattering.",
             "exceso de mente: riesgo de darle demasiadas vueltas, conflicto o dispersión."),
    "Tierra": ("excess of matter: risk of rigidity, attachment or getting stuck.",
               "exceso de materia: riesgo de rigidez, apego o de quedarse estancado."),
}
MISSING = {
    "Fuego": ("No Fire: initiative may be lacking.", "Falta Fuego: puede faltar iniciativa."),
    "Agua": ("No Water: emotions stay in the background.", "Falta Agua: las emociones quedan en segundo plano."),
    "Aire": ("No Air: it helps to clarify ideas and talk things through.",
             "Falta Aire: conviene aclarar ideas y hablar las cosas."),
    "Tierra": ("No Earth: practical matters (money, routine, body) need attention.",
               "Falta Tierra: lo práctico (dinero, rutina, cuerpo) pide atención."),
}
ADVICE = {
    "Fuego": ("Channel the energy into one concrete step before it scatters.",
              "Canaliza la energía en un paso concreto antes de que se disperse."),
    "Agua": ("Listen to what you feel before deciding; bonds are the key.",
             "Escucha lo que sientes antes de decidir; los vínculos son la clave."),
    "Aire": ("Order your ideas and say clearly what you think; clarity clears the rest.",
             "Ordena las ideas y di claramente lo que piensas; la claridad despeja el resto."),
    "Tierra": ("Lean on the tangible: a realistic plan and consistency pay off.",
               "Apóyate en lo tangible: un plan realista y constancia dan fruto."),
}
RANK_THEME = {
    1: ("a beginning", "un comienzo"), 2: ("a choice or duality", "una elección o dualidad"),
    3: ("growth and collaboration", "crecimiento y colaboración"),
    4: ("stability (or stagnation)", "estabilidad (o estancamiento)"),
    5: ("conflict or loss", "conflicto o pérdida"), 6: ("harmony and transition", "armonía y transición"),
    7: ("a test or assessment", "una prueba o evaluación"),
    8: ("movement and mastery of the craft", "movimiento y dominio del oficio"),
    9: ("something nearly complete", "algo casi culminado"), 10: ("a cycle closing", "un ciclo que se cierra"),
}
COURT = {
    11: ("a Page (a message, an apprentice or a young person)", "una Sota (mensaje, aprendiz o persona joven)"),
    12: ("a Knight (someone who acts and moves forward)", "un Caballero (alguien que actúa y avanza)"),
    13: ("a Queen (inner maturity and care)", "una Reina (madurez interior y cuidado)"),
    14: ("a King (mastery and outward authority)", "un Rey (dominio y autoridad exterior)"),
}
SUIT_THEME = {
    "Bastos": ("fire: action, energy, ambition", "fuego: acción, energía, ambición"),
    "Copas": ("water: emotion, bonds, intuition", "agua: emociones, vínculos, intuición"),
    "Espadas": ("air: mind, truth, conflict", "aire: mente, verdad, conflicto"),
    "Oros": ("earth: money, work, body", "tierra: dinero, trabajo, cuerpo"),
}
PAIRS = {
    (16, 17): ("The Tower and The Star: after the rupture comes hope.",
               "La Torre y La Estrella: tras la ruptura llega la esperanza."),
    (13, 16): ("Death and The Tower: deep changes in a chain.", "La Muerte y La Torre: cambios profundos encadenados."),
    (6, 15): ("The Lovers and The Devil: love and attachment blend; tell choice apart from dependence.",
              "Los Enamorados y El Diablo: amor y apego se mezclan; distingue elección de dependencia."),
    (18, 19): ("The Moon and The Sun: from uncertainty to clarity.", "La Luna y El Sol: de la incertidumbre a la claridad."),
    (0, 21): ("The Fool and The World: an ending and a beginning touch again.",
              "El Loco y El Mundo: un cierre y un comienzo vuelven a tocarse."),
    (2, 9): ("The High Priestess and The Hermit: the answers are within; silence and retreat.",
             "La Sacerdotisa y El Ermitaño: las respuestas están dentro; silencio y recogimiento."),
    (10, 11): ("The Wheel and Justice: fate answers your actions.", "La Rueda y La Justicia: el destino responde a tus actos."),
    (3, 4): ("The Empress and The Emperor: creativity and structure seek balance.",
             "La Emperatriz y El Emperador: creatividad y estructura buscan equilibrio."),
    (1, 2): ("The Magician and The High Priestess: will and intuition; act from what you know inside.",
             "El Mago y La Sacerdotisa: voluntad e intuición; actúa desde lo que sabes por dentro."),
    (7, 8): ("The Chariot and Strength: progress with calm control.", "El Carro y La Fuerza: avance con control sereno."),
    (20, 21): ("Judgement and The World: rebirth and culmination.", "El Juicio y El Mundo: renacer y culminación."),
    (12, 14): ("The Hanged Man and Temperance: patience and pause bring balance.",
               "El Colgado y La Templanza: la paciencia y la pausa traen equilibrio."),
    (15, 16): ("The Devil and The Tower: the chains break suddenly.", "El Diablo y La Torre: las cadenas se rompen de golpe."),
    (13, 17): ("Death and The Star: after the ending, hope.", "La Muerte y La Estrella: después del final, la esperanza."),
    (19, 21): ("The Sun and The World: success and fulfilment.", "El Sol y El Mundo: éxito y plenitud."),
    (12, 13): ("The Hanged Man and Death: letting go is the lesson before transforming.",
               "El Colgado y La Muerte: soltar es la lección antes de transformarse."),
    (2, 18): ("The High Priestess and The Moon: very strong intuition, with a risk of mistaking illusion for signal.",
              "La Sacerdotisa y La Luna: intuición muy fuerte, con riesgo de confundir ilusión y señal."),
    (5, 6): ("The Hierophant and The Lovers: commitment and shared values.",
             "El Hierofante y Los Enamorados: compromiso y valores compartidos."),
    (9, 12): ("The Hermit and The Hanged Man: a season of retreat and reflection; do not force progress.",
              "El Ermitaño y El Colgado: etapa de retiro y reflexión; no fuerces el avance."),
    (1, 4): ("The Magician and The Emperor: the skill and power to build a project.",
             "El Mago y El Emperador: capacidad y poder para materializar un proyecto."),
}


@dataclass
class CS:
    """Carta en la mesa con todo lo que necesita el motor."""
    card: dict
    reversed: bool
    role: str
    key: str
    group: int | None
    pos_w: float
    center: np.ndarray

    @property
    def weight(self) -> float:
        w = 1.0
        if self.card["arcana"] == "mayor":
            w *= 1.8
        elif self.card.get("court"):
            w *= 1.4
        if self.reversed:
            w *= 0.65
        return w * self.pos_w

    @property
    def polarity(self) -> float:
        return self.card["polarity"] * (-0.5 if self.reversed else 1.0)

    @property
    def element(self) -> str:
        return self.card["element"]

    @property
    def name(self) -> str:
        return card_name(self.card)

    def kw(self, k=1) -> str:
        return ", ".join(keywords(self.card, self.reversed, k))

    def label(self) -> str:
        return self.name + (L(" (reversed)", " (al revés)") if self.reversed else "")


def position_names(n: int):
    """Nombres de posición para n cartas en el idioma actual, o None."""
    names = POSITION_NAMES.get(n)
    return [L(*p) for p in names] if names else None


def dignity(a: str, b: str) -> float:
    return DIGNITY.get((a, b), 0.0)


def _states(layout) -> list[CS]:
    return [CS(BY_ID[s.track.card_id], s.track.reversed, s.role, s.key, s.group, s.weight,
               np.asarray(s.track.quad, float).mean(axis=0)) for s in layout.slots]


def _neighbors(cs: list[CS]):
    """Pares de cartas vecinas: las 2 más cercanas de cada una (sin repetir)."""
    pairs = set()
    for i, a in enumerate(cs):
        d = sorted((float(np.linalg.norm(a.center - b.center)), j) for j, b in enumerate(cs) if j != i)
        for _, j in d[:2]:
            pairs.add((min(i, j), max(i, j)))
    return sorted(pairs)


def _quintessence(cs: list[CS]):
    total = sum(c.card["num"] for c in cs)
    while total > 21:
        total = sum(int(d) for d in str(total))
    return total, BY_ID[total]                      # id 0..21 = arcanos mayores


def _pol_word(p: float) -> str:
    if p > 0.25:
        return L("favourable", "favorable")
    if p < -0.25:
        return L("demanding", "exigente")
    return L("neutral", "neutra")


# ----------------------------------------------------------------------- API
def compose(layout, chart=None):
    """layout: spreads.Layout. Devuelve (fichas en orden de lectura, secciones[(título, texto)])."""
    cs = _states(layout)
    items = [dict(pos=c.role, id=c.card["id"], name=c.name, reversed=c.reversed,
                  meaning=meaning(c.card, c.reversed), corr=correspondences.localized(c.card)) for c in cs]
    return items, sections(layout, cs, chart)


def headline_key() -> str:
    return L("Summary", "Resumen")


def sections(layout, cs: list[CS], chart=None):
    n = len(cs)
    if n == 0:
        return [(L("Global reading", "Lectura global"),
                 L("Place cards in front of the camera. The reading builds up with each one.",
                   "Coloca cartas frente a la cámara. La lectura se irá construyendo con cada una."))]
    out = []
    W = sum(c.weight for c in cs)
    pol = sum(c.polarity * c.weight for c in cs) / W
    majors = sum(c.card["arcana"] == "mayor" for c in cs)
    minors = n - majors
    rev = sum(c.reversed for c in cs)
    cards_n = L(plural(n, "card", "cards"), plural(n, "carta", "cartas"))

    # 1. Panorama
    head = L(f"{cards_n} · {layout.name}. {plural(majors, 'major arcanum', 'major arcana')}, "
             f"{plural(minors, 'minor card', 'minor cards')}, {rev} reversed. Average polarity {pol:+.2f}: {_pol_word(pol)} energy.",
             f"{cards_n} · {layout.name}. {plural(majors, 'arcano mayor', 'arcanos mayores')}, "
             f"{plural(minors, 'menor', 'menores')}, {rev} al revés. Polaridad media {pol:+.2f}: energía {_pol_word(pol)}.")
    tone = []
    if n >= 2 and majors * 2 > n:
        tone.append(L("The major arcana weigh in: deep matters, lessons or fate.",
                      "Pesan los arcanos mayores: asuntos de fondo, lecciones o destino."))
    elif n >= 2 and majors == 0:
        tone.append(L("Only minor arcana: this is about daily life and practical decisions.",
                      "Solo arcanos menores: se habla del día a día y de decisiones prácticas."))
    if n >= 2 and rev * 2 > n:
        tone.append(L("Reversed cards dominate: energy blocked, turned inward or changing.",
                      "Dominan las invertidas: energía bloqueada, interiorizada o en proceso de cambio."))
    if layout.note:
        tone.append(layout.note)
    out.append((L("Overview", "Panorama"), " ".join([head] + tone)))

    # 2. Lectura según la posición
    disp = _layout_reading(layout, cs)
    if disp:
        out.append((L("By position", "Según su posición"), disp))

    # 2b. Síntesis a partir de los datos: hilos, tensiones, relaciones entre posiciones y símbolos
    syn_secs, syn = synthesis.sections_from(layout, cs)
    out.extend(syn_secs)

    # 3. Dinámica: elementos, dignidades, tensión
    el = Counter()
    for c in cs:
        el[c.element] += c.weight
    tot = sum(el.values())
    bal = {e: el.get(e, 0) / tot for e in ELEMENTS}
    top = max(bal, key=bal.get)
    shares = ", ".join(f"{term(e)} {round(100 * v)}%" for e, v in sorted(bal.items(), key=lambda t: -t[1]) if v)
    dyn = [L(f"Balance: {shares}. {term(top)} dominates ({ELEMENT_TEXT[top][0]}).",
             f"Balance: {shares}. Domina {top} ({ELEMENT_TEXT[top][1]}).")]
    if n >= 3 and bal[top] >= 0.7:
        dyn.append(L("Imbalance: ", "Desequilibrio: ") + L(*EXCESS[top]))
    if n >= 4:
        dyn += [L(*MISSING[e]) for e in ELEMENTS if bal[e] == 0]
    pairs = _neighbors(cs)
    if pairs:
        num = den = 0.0
        best = worst = None
        for i, j in pairs:
            d, w = dignity(cs[i].element, cs[j].element), sqrt(cs[i].weight * cs[j].weight)
            num, den = num + d * w, den + w
            if best is None or d * w > best[0]:
                best = (d * w, i, j)
            if worst is None or d * w < worst[0]:
                worst = (d * w, i, j)
        inter = num / den
        tension = (L("high tension", "alta tensión") if inter < -0.4 else
                   L("harmony", "armonía") if inter > 0.6 else L("mixed dynamics", "dinámica mixta"))
        dyn.append(L(f"Between neighbouring cards: {tension} (interaction {inter:+.2f}).",
                     f"Entre cartas vecinas: {tension} (interacción {inter:+.2f})."))
        if worst[0] < 0:
            a, b = cs[worst[1]], cs[worst[2]]
            dyn.append(L(f"Strongest friction: {a.label()} and {b.label()} ({term(a.element)} against {term(b.element)}).",
                         f"Mayor fricción: {a.label()} y {b.label()} ({a.element} contra {b.element})."))
        if best[0] > 0.9:
            a, b = cs[best[1]], cs[best[2]]
            dyn.append(L(f"Strongest support: {a.label()} and {b.label()}.",
                         f"Mayor refuerzo: {a.label()} y {b.label()}."))
    out.append((L("Dynamics", "Dinámica"), " ".join(dyn)))

    # 4. Tema: la carta de mayor peso manda, las demás la matizan
    kwc = Counter()
    for c in cs:
        for k in keywords(c.card, c.reversed):
            kwc[k] += c.weight
    heavy = max(cs, key=lambda c: c.weight)
    role = heavy.role.split(" · ")[-1].split(" (")[0]
    th = L(f"The heaviest card is {heavy.label()} ({role}): it sets the theme; the others shade it.",
           f"La carta de mayor peso es {heavy.label()} ({role}): marca el tema; las demás lo matizan.")
    if n >= 2:
        th += L(" Weightiest ideas: ", " Conceptos que más pesan: ") + "; ".join(k for k, _ in kwc.most_common(5)) + "."
    out.append((L("Theme", "Tema"), th))

    # 5. Combinaciones, números y cortes
    extra = [L(*txt) for (a, b), txt in PAIRS.items()
             if any(c.card["id"] == a for c in cs) and any(c.card["id"] == b for c in cs)]
    for c in cs:
        if c.card.get("court"):
            extra.append(L(f"{c.name} suggests {COURT[c.card['num']][0]}.",
                           f"{c.name} sugiere {COURT[c.card['num']][1]}."))
    ranks = Counter(c.card["num"] for c in cs if c.card["arcana"] == "menor" and not c.card.get("court"))
    extra += [L(f"The {r} repeats ({k} cards): {RANK_THEME[r][0]} is a common thread.",
                f"Se repite el {r} ({k} cartas): {RANK_THEME[r][1]} es un hilo común.")
              for r, k in sorted(ranks.items()) if k >= 2]
    suits = Counter(c.card["suit"] for c in cs if c.card["suit"])
    for s, k in suits.items():
        if k >= 3:
            extra.append(L(f"{k} cards of {term(s)}: the core matter is {SUIT_THEME[s][0]}.",
                           f"{k} cartas de {s}: el asunto central es {SUIT_THEME[s][1]}."))
    if extra:
        out.append((L("Combinations", "Combinaciones"), " ".join(extra)))

    # 6. Quintaesencia
    if n >= 2:
        q, qc = _quintessence(cs)
        words = ", ".join(keywords(qc))
        out.append((L("Quintessence", "Quintaesencia"),
                    L(f"All the cards add up and reduce to {q}: {card_name(qc)} ({words}). "
                      "It is the thread that ties the reading together.",
                      f"La suma de todas las cartas se reduce a {q}: {card_name(qc)} ({words}). "
                      "Es el hilo que une la lectura.")))

    # 7. Consejo
    adv = synthesis.advice(syn) or L(*ADVICE[top])
    end = _outcome(layout, cs)
    if n >= 3 and end is not None:
        adv += L(f" The outcome the table points to is {end.label()}: {end.kw(2)}.",
                 f" El desenlace que marca la mesa apunta a {end.label()}: {end.kw(2)}.")
    out.append((L("Advice", "Consejo"), adv))
    if chart is not None:                               # carta natal (opcional): justo después del panorama
        notes = [t for _, _, t in chartlink.resonances(chart, cs, 5)]
        text = " ".join([f"{chart.name}: {chartlink.summary(chart)}."] + notes + [chartlink.elements(chart, top)])
        out.insert(1, (L("Your chart", "Tu carta astral"), text))
    if syn["top"]:
        theme = L(f"core theme: {theme_text(syn['top'])}", f"tema central: {theme_text(syn['top'])}")
    else:
        theme = L(f"{term(top)} dominates", f"domina {top.lower()}")
    out.insert(0, (headline_key(), f"{cards_n} · {layout.name} — {theme}; "
                   + L(f"{_pol_word(pol)} energy", f"energía {_pol_word(pol)}")))
    return out


# ------------------------------------------------- lectura específica por disposición
def _outcome(layout, cs):
    """La carta que representa el desenlace según la disposición."""
    by = {c.key: c for c in cs}
    k = layout.kind
    if k == "celtic":
        return by.get("c10")
    if k == "horseshoe":
        return by.get("h7")
    if k == "cross":
        return by.get("der")                           # lo que llega
    if k in ("rows", "line") and any(c.group is not None for c in cs):
        last = max(c.group for c in cs if c.group is not None)
        g = [c for c in cs if c.group == last]
        return max(g, key=lambda c: c.weight)          # la de más peso del último nivel (futuro / resultado)
    return cs[-1] if cs else None


def _grp_pol(cs, group):
    g = [c for c in cs if c.group == group]
    return (sum(c.polarity * c.weight for c in g) / sum(c.weight for c in g)) if g else None


def _fmt(cards):
    return join_and([f"{c.label()} ({c.kw(2)})" for c in cards])


def _layout_reading(layout, cs):
    k, n = layout.kind, len(cs)
    by = {c.key: c for c in cs}
    if k == "single":
        return f"{cs[0].label()}: {cs[0].kw(3)}."
    temporal = (k == "rows" and len({c.group for c in cs}) == 3) or (k == "line" and n == 3)
    if temporal:
        parts = []
        for g, nm in enumerate(position_names(3)):
            cards = [c for c in cs if c.group == g]
            if cards:
                parts.append(f"{nm}: {_fmt(cards)}.")
        p0, p2 = _grp_pol(cs, 0), _grp_pol(cs, 2)
        trend = ""
        if p0 is not None and p2 is not None:
            d = p2 - p0
            trend = (L(" Trend: the energy improves toward the future.",
                       " Tendencia: la energía mejora hacia el futuro.") if d > 0.25 else
                     L(" Trend: the energy grows more demanding toward the future.",
                       " Tendencia: la energía se vuelve más exigente hacia el futuro.") if d < -0.25 else
                     L(" Trend: the energy holds steady over time.",
                       " Tendencia: la energía se mantiene estable en el tiempo."))
        return " ".join(parts) + trend
    if k == "rows" and len({c.group for c in cs}) == 2:
        top = [c for c in cs if c.group == 0]
        bot = [c for c in cs if c.group == 1]
        return L(f"Situation: {_fmt(top)}. Outcome: {_fmt(bot)}.", f"Situación: {_fmt(top)}. Resultado: {_fmt(bot)}.")
    if k == "cross":
        core, up, down, left, right = (by[x] for x in ("centro", "arriba", "abajo", "izq", "der"))
        s = L(f"Core: {core.label()} ({core.kw(2)}). Above, the conscious: {up.label()}; below, the root: "
              f"{down.label()}. Leaving: {left.label()}; coming: {right.label()}.",
              f"Núcleo: {core.label()} ({core.kw(2)}). Arriba, lo consciente: {up.label()}; abajo, la raíz: "
              f"{down.label()}. Lo que se va: {left.label()}; lo que llega: {right.label()}.")
        if dignity(up.element, down.element) < 0:
            s += L(" The conscious and the unconscious clash: something is not being admitted.",
                   " Lo consciente y lo inconsciente chocan: hay algo que no se está admitiendo.")
        d = right.polarity - left.polarity
        if d > 0.25:
            s += L(" The path improves.", " El camino mejora.")
        elif d < -0.25:
            s += L(" The path grows more demanding.", " El camino se vuelve más exigente.")
        return s
    if k == "celtic":
        c = {i: by[f"c{i}"] for i in range(1, 11)}
        s = L(f"The matter (1): {c[1].label()}, crossed by {c[2].label()}. Root: {c[3].label()}; past: "
              f"{c[4].label()}; crown: {c[5].label()}; near future: {c[6].label()}. You: {c[7].label()}; "
              f"environment: {c[8].label()}; hopes and fears: {c[9].label()}. Outcome (10): {c[10].label()} "
              f"({c[10].kw(2)}).",
              f"El asunto (1): {c[1].label()}, cruzado por {c[2].label()}. Raíz: {c[3].label()}; pasado: "
              f"{c[4].label()}; corona: {c[5].label()}; futuro próximo: {c[6].label()}. Tú: {c[7].label()}; "
              f"entorno: {c[8].label()}; esperanzas y miedos: {c[9].label()}. Resultado (10): {c[10].label()} "
              f"({c[10].kw(2)}).")
        d = c[10].polarity - sum(c[i].polarity for i in range(1, 7)) / 6
        if d > 0.3:
            s += L(" The outcome is more favourable than the starting point.",
                   " El resultado es más favorable que la situación de partida.")
        elif d < -0.3:
            s += L(" The outcome is more demanding than the starting point.",
                   " El resultado es más exigente que la situación de partida.")
        return s
    if k == "horseshoe":
        return " ".join(f"{x.role.split(' · ')[1]}: {x.label()}." for x in cs)
    if k in ("line", "rows", "entry"):
        return L("Thread: ", "Hilo: ") + " · ".join(f"{x.role}: {x.label()} ({x.kw(1)})" for x in cs) + "."
    return ""
