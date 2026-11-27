"""Síntesis: combina temas, símbolos y relaciones entre posiciones en frases de lectura.

Todo sale de los datos (palabras clave por carta y símbolos de los arcanos mayores):
  hilos       temas que se repiten en varias cartas
  tensiones   temas opuestos presentes a la vez (p. ej. cambio frente a estabilidad)
  relaciones  cómo evoluciona el tema entre posiciones enlazadas (pasado->presente->futuro, cruz, cruz celta...)
  símbolos    símbolos compartidos entre arcanos mayores
"""
from __future__ import annotations

from collections import Counter, defaultdict

from tarotcam.carddata import correspondences as corr
from tarotcam.carddata import symbolism
from tarotcam.carddata.cards import keywords
from tarotcam.i18n import L, join_and, term
from tarotcam.engine.semantics import OPPOSITE, keywords_profile, tension_text, theme_name, theme_text

STRONG = 0.5          # una carta "aporta con fuerza" un tema si está entre sus 3 primeras palabras clave

ADVICE = {
    "comienzo": "Da el primer paso aunque el plan no esté completo.",
    "cierre": "Cierra lo pendiente antes de abrir lo nuevo.",
    "cambio": "No te aferres: adaptarte cuesta menos que resistir.",
    "estabilidad": "Consolida lo que funciona antes de añadir más.",
    "accion": "Actúa, pero con un objetivo claro.",
    "pausa": "Detente a observar; no todo pide respuesta inmediata.",
    "vinculos": "Cuida y expresa el vínculo: es lo que sostiene este momento.",
    "aislamiento": "Acepta o pide compañía; el retiro prolongado pesa.",
    "conflicto": "Aborda la fricción de frente y con calma, sin escalar.",
    "armonia": "Sostén el equilibrio logrado sin descuidarlo.",
    "abundancia": "Disfruta y comparte lo que llega; agradécelo.",
    "perdida": "Reconoce la pérdida y busca apoyo; no la cargues solo.",
    "claridad": "Confía en lo que ves con claridad y decide en consecuencia.",
    "confusion": "No decidas con información incompleta: verifica antes.",
    "intuicion": "Escucha tu intuición, pero contrástala con hechos.",
    "creatividad": "Dale forma a la idea: empieza por algo pequeño.",
    "trabajo": "Organiza el esfuerzo y protege tus recursos.",
    "control": "Pon límites claros sin caer en la rigidez.",
    "libertad": "Suelta lo que te ata y elige con libertad.",
    "miedo": "Ponle nombre al miedo: así verás su tamaño real.",
    "exceso": "Modera: lo que sobra hoy pasa factura mañana.",
    "esperanza": "Mantén la fe, apoyada en pasos concretos.",
}

ADVICE_EN = {
    "comienzo": "Take the first step even if the plan is not complete.",
    "cierre": "Close what is pending before opening something new.",
    "cambio": "Do not cling: adapting costs less than resisting.",
    "estabilidad": "Consolidate what works before adding more.",
    "accion": "Act, with a clear goal.",
    "pausa": "Stop and observe; not everything needs an immediate answer.",
    "vinculos": "Care for the bond and voice it: it holds this moment up.",
    "aislamiento": "Accept or ask for company; long withdrawal weighs.",
    "conflicto": "Face the friction head-on and calmly, without escalating.",
    "armonia": "Sustain the balance you reached without neglecting it.",
    "abundancia": "Enjoy and share what arrives; be grateful for it.",
    "perdida": "Acknowledge the loss and seek support; do not carry it alone.",
    "claridad": "Trust what you see clearly and decide accordingly.",
    "confusion": "Do not decide on incomplete information: check first.",
    "intuicion": "Listen to your intuition, and test it against facts.",
    "creatividad": "Give the idea a shape: start with something small.",
    "trabajo": "Organise the effort and protect your resources.",
    "control": "Set clear limits without turning rigid.",
    "libertad": "Release what binds you and choose freely.",
    "miedo": "Name the fear: you will see its real size.",
    "exceso": "Moderate: today's surplus is paid for tomorrow.",
    "esperanza": "Keep faith, backed by concrete steps.",
}

# enlaces entre posiciones por disposición: (clave A, clave B, descripción)
LINKS = {
    "cross": [("izq", "der", ("From what is leaving to what is coming", "De lo que se va a lo que llega")),
              ("arriba", "abajo", ("From the conscious to the root", "De lo consciente a la raíz"))],
    "celtic": [("c1", "c2", ("The matter against what crosses it", "El asunto frente a lo que lo cruza")),
               ("c4", "c6", ("From the recent past to the near future", "Del pasado reciente al futuro próximo")),
               ("c5", "c3", ("From the crown to the base", "De la corona a la base")),
               ("c9", "c10", ("From hopes and fears to the outcome", "De esperanzas y miedos al resultado"))],
    "horseshoe": [("h1", "h2", ("From past to present", "Del pasado al presente")),
                  ("h2", "h3", ("From present to near future", "Del presente al futuro inmediato")),
                  ("h6", "h7", ("From obstacles to the outcome", "De los obstáculos al resultado"))],
}
TEMPORAL = [(0, 1, ("From past to present", "Del pasado al presente")),
            (1, 2, ("From present to future", "Del presente al futuro"))]


def profile(cs) -> Counter:
    return keywords_profile(keywords(cs.card, cs.reversed, 6, lang="es"))      # análisis: siempre canónico


def _top(profiles, members):
    """Tema dominante de un grupo de cartas (ponderado por peso) y sus nombres."""
    agg = Counter()
    for c in members:
        for t, sc in profiles[id(c)].items():
            agg[t] += sc * c.weight
    if not agg:
        return None, []
    t = agg.most_common(1)[0][0]
    return t, [c.label() for c in members if profiles[id(c)].get(t, 0) >= STRONG] or [c.label() for c in members]


def _relation(a, b, na, nb) -> str:
    A, B = theme_text(a), theme_text(b)
    ca, cb = ", ".join(na), ", ".join(nb)
    if a == b:
        return L(f"continuity, {A} is still present ({join_and(na + nb)})",
                 f"continuidad, sigue presente {A} ({join_and(na + nb)})")
    if OPPOSITE.get(a) == b:
        return L(f"a turn, from {A} ({ca}) to {B} ({cb})", f"giro, de {A} ({ca}) a {B} ({cb})")
    return L(f"from {A} ({ca}) to {B} ({cb})", f"de {A} ({ca}) a {B} ({cb})")


def analyze(layout, cs):
    """-> dict con hilos, tensiones, relaciones, símbolos y tema dominante."""
    profiles = {id(c): profile(c) for c in cs}
    contrib = defaultdict(list)                       # tema -> [(carta, puntuación)]
    for c in cs:
        for t, sc in profiles[id(c)].items():
            contrib[t].append((c, sc))
    agg = {t: sum(sc * c.weight for c, sc in v) for t, v in contrib.items()}
    strong = {t: [(c, sc) for c, sc in v if sc >= STRONG] for t, v in contrib.items()}

    threads = sorted(((t, agg[t], [c for c, _ in v]) for t, v in strong.items() if len(v) >= 2),
                     key=lambda x: -x[1])[:2 if len(cs) < 5 else 3]

    tensions, seen = [], set()
    for t, v in strong.items():
        o = OPPOSITE.get(t)
        if not o or o not in strong or frozenset({t, o}) in seen or not v or not strong[o]:
            continue
        seen.add(frozenset({t, o}))
        ca, cb = [c for c, _ in v], [c for c, _ in strong[o]]
        if {id(c) for c in ca} == {id(c) for c in cb} and len(ca) == 1:
            continue                                  # una sola carta que contiene ambos: no es tensión entre cartas
        tensions.append((t, o, ca, cb, min(agg[t], agg[o])))
    tensions.sort(key=lambda x: -x[4])

    relations = []
    if layout.kind in ("rows", "line") and len({c.group for c in cs if c.group is not None}) >= 2:
        for ga, gb, label in TEMPORAL:
            A = [c for c in cs if c.group == ga]
            B = [c for c in cs if c.group == gb]
            if A and B:
                (ta, na), (tb, nb) = _top(profiles, A), _top(profiles, B)
                if ta and tb:
                    relations.append(f"{L(*label)}: {_relation(ta, tb, na, nb)}.")
    else:
        by = {c.key: c for c in cs}
        for ka, kb_, label in LINKS.get(layout.kind, []):
            if ka in by and kb_ in by:
                (ta, na), (tb, nb) = _top(profiles, [by[ka]]), _top(profiles, [by[kb_]])
                if ta and tb:
                    relations.append(f"{L(*label)}: {_relation(ta, tb, na, nb)}.")

    sym = defaultdict(list)
    for c in cs:
        if c.card["arcana"] == "mayor" and c.card.get("system") != "marseille":   # símbolos de la imagen RWS
            for k in symbolism.categories(c.card["id"]):
                sym[k].append(c.name)
    symbols = sorted(((k, v) for k, v in sym.items() if len(v) >= 2), key=lambda kv: -len(kv[1]))[:3]

    astro = defaultdict(list)                         # planeta / signo -> cartas que lo comparten
    for c in cs:
        r = c.card["corr"]
        for tag in set(r["planets"]) | set(r["signs"]):
            astro[tag].append(c.name)
    shared_astro = sorted(((k, v) for k, v in astro.items() if len(v) >= 2), key=lambda kv: -len(kv[1]))[:3]

    top = max(agg, key=agg.get) if agg else None
    return dict(threads=threads, tensions=tensions, relations=relations, symbols=symbols, top=top, agg=agg,
                astro=shared_astro)


def sections_from(layout, cs):
    """Secciones de texto: hilos y tensiones, símbolos y correspondencias; devuelve además el análisis."""
    a = analyze(layout, cs)

    def names(cards):
        return ", ".join(c.label() for c in cards)

    parts = []
    for t, _, cards in a["threads"]:
        parts.append(L(f"Recurring theme: {theme_text(t)} ({names(cards)}).",
                       f"Se repite {theme_text(t)} ({names(cards)})."))
    for t, o, ca, cb, _ in a["tensions"][:2]:
        why = tension_text(frozenset({t, o}))
        parts.append(L(f"Tension: {theme_text(t)} ({names(ca)}) against {theme_text(o)} ({names(cb)}). ",
                       f"Tensión: {theme_text(t)} ({names(ca)}) frente a {theme_text(o)} ({names(cb)}). ")
                     + f"{why[:1].upper() + why[1:]}.")
    parts += a["relations"]
    secs = []
    if parts:
        secs.append((L("Threads and tensions", "Hilos y tensiones"), " ".join(parts)))
    if a["symbols"]:
        out = []
        for k, v in a["symbols"]:
            name, what = symbolism.explain(k)
            out.append(f"{name[:1].upper() + name[1:]} ({', '.join(v)}): {what}.")
        secs.append((L("Shared symbols", "Símbolos en común"), " ".join(out)))
    if a["astro"]:
        secs.append((L("Shared correspondences", "Correspondencias en común"), " ".join(
            f"{term(tag)} ({', '.join(v)}): {corr.meaning_of(tag)}." for tag, v in a["astro"])))
    return secs, a


def advice(a) -> str:
    if not a["top"]:
        return ""
    s = (ADVICE_EN if L("en", "es") == "en" else ADVICE)[a["top"]]
    if a["tensions"]:
        t, o, *_ = a["tensions"][0]
        s += L(f" Watch the tension between {theme_name(t)} and {theme_name(o)}.",
               f" Presta atención a la tensión entre {theme_name(t)} y {theme_name(o)}.")
    return s
