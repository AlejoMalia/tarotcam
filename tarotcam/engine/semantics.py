"""Capa semántica: convierte las palabras clave de cada carta en TEMAS comparables.

Con los temas el motor puede encontrar hilos comunes, tensiones entre temas opuestos y cómo cambia el
asunto de una posición a otra, a partir de los datos de simbología y no de una tabla de parejas escrita a mano.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

from tarotcam import i18n

# tema -> (raíces de palabra sin tildes, explicación corta)
THEMES: dict[str, tuple[list[str], str]] = {
    "comienzo": (["comienz", "inicio", "inici", "nuev", "arranque", "renacimiento", "despertar", "potencial",
                  "oportunidad", "salto", "semilla", "primer", "exploracion", "regalos", "inocencia", "mejora", "regeneracion", "deseo de aprender"], "un comienzo, algo que empieza"),
    "cierre": (["final", "cierre", "culmin", "completitud", "conclus", "plenitud", "logro", "fin ", "acabad",
                "ultim", "terminar", "ciclo complet", "fracaso"], "un cierre o una culminación"),
    "cambio": (["cambi", "transform", "transici", "ciclo", "inflexion", "giro", "caos", "disrup", "cataclismo",
                "revelacion", "renovacion", "movimiento", "progreso", "avance", "expansion", "viaje", "caida",
                "inestabil", "colapso", "sorpresa", "punto de"], "cambio y movimiento"),
    "estabilidad": (["estabilidad", "seguridad", "estructura", "rutina", "fiabilidad", "persistencia",
                     "resistencia", "solidez", "proteccion", "legado", "constancia", "perseverancia",
                     "cimientos", "orden", "disciplina", "tradicion", "institucion", "conformidad", "convencion", "ley", "honor", "alineacion", "tradicional", "ahorro", "conservadurismo", "pies en la tierra", "practica", "supervivencia", "autoproteccion"], "estabilidad y base firme"),
    "accion": (["accion", "voluntad", "determinacion", "impulso", "energia", "entusiasmo", "motivacion",
                "victoria", "valentia", "valor", "audaz", "pasion", "ambicion", "iniciativa", "rapid", "aventura",
                "triunfo", "fuerza", "emprendedor", "impulsiv", "competencia", "manifestacion", "motivado", "ambicioso", "valiente"],
                "acción e impulso"),
    "pausa": (["introspeccion", "contemplacion", "retraimiento", "descanso", "espera", "paciencia", "reflexion",
               "suspension", "rendicion", "pausa", "retirada", "cautela", "prudencia", "reevaluacion",
               "quietud", "meditacion", "recuperacion", "sacrificio", "rendirse", "ceder", "relajacion", "punto muerto"], "pausa y recogimiento"),
    "vinculos": (["amor", "relacion", "asociacion", "atraccion", "union", "conexion", "amistad", "romance",
                  "compromiso", "familia", "hogar", "comunidad", "compasion", "empatia", "afecto", "reunion",
                  "celebracion", "generosidad", "caridad", "apoyo", "equipo", "pareja", "matrimonio",
                  "cariño", "nutric", "sociable", "calidez", "diplomacia", "correspondido", "sensibilidad", "encanto", "seguir el corazon", "opciones", "colaboracion", "dar y recibir"],
                  "vínculos y relaciones"),
    "aislamiento": (["aislamiento", "soledad", "desconexion", "introversion", "frialdad", "abandono", "rechazo",
                     "retiro", "exclusion", "separacion", "distancia", "rota", "chisme", "bloquead", "retraimiento"], "aislamiento o distancia"),
    "conflicto": (["conflicto", "tension", "oposicion", "agresion", "desacuerdo", "traicion", "crueldad",
                   "brutalidad", "desafio", "defensiv", "discusion", "pelea", "celos", "tirania", "dominacion",
                   "desarmonia", "bando", "dispers", "desequilibrio", "egoismo", "frustracion", "vengativ", "intimidacion", "injusticia", "impaciencia", "ganar a toda costa"], "conflicto o fricción"),
    "armonia": (["armonia", "paz", "calma", "serenidad", "equilibrio", "moderacion", "resolucion",
                 "reconciliacion", "perdon", "sanacion", "curacion", "integracion", "fluir", "balance",
                 "bienestar", "humor", "absolucion"], "armonía y reconciliación"),
    "abundancia": (["abundancia", "prosperidad", "riqueza", "exito", "fertilidad", "felicidad", "alegria",
                    "satisfaccion", "contentamiento", "reconocimiento", "recompensa", "lujo", "placer",
                    "suerte", "optimismo", "vitalidad", "generos", "plenitud", "deseos cumplidos"],
                    "abundancia y éxito"),
    "perdida": (["perdida", "duelo", "pena", "decepcion", "arrepentimiento", "tristeza", "dolor", "desastre",
                 "desgracia", "escasez", "pobreza", "agotamiento", "depresion", "desanimo", "desesperacion",
                 "sufrimiento", "fracas", "carencia", "insatisfaccion", "vacio", "apatia", "pesimismo",
                 "estancamiento", "retraso", "contratiempo", "fallid", "nublad", "incompletitud", "carga", "agotado", "frustracion", "nostalgia", "atascado", "incapacidad", "bloqueo", "derrota", "ruina", "crisis", "deuda", "corrupcion", "amargura", "deshonra", "pereza", "aburrimiento", "burnout", "dificultad", "mediocre", "resultados mediocres", "restriccion"], "pérdida y dificultad"),
    "claridad": (["claridad", "verdad", "justicia", "honestidad", "razon", "logica", "comunicacion", "ideas",
                  "vision", "juicio", "pensamiento", "decision", "enfoque", "conciencia", "claro",
                  "objetividad", "planificacion", "prevision", "mental", "proposito", "causa y efecto", "noticias", "realidad", "juicio", "estrategia", "honesta", "directa", "perceptiva", "vigilancia", "etica", "confesion"], "claridad y verdad"),
    "confusion": (["confusion", "engaño", "ilusion", "mentira", "manipulacion", "secretos", "ocultas",
                   "fantasia", "indecision", "duda", "atajos", "deshonestidad", "sesgo", "paranoia",
                   "desalineacion", "escapismo", "irreales", "ingenuidad", "mal juicio", "inconstancia",
                   "falsos", "traicion", "negacion", "evitacion", "inmadurez", "idealismo", "distraido", "desorganizado", "picardia"], "confusión o engaño"),
    "intuicion": (["intuicion", "espiritual", "misterio", "inconsciente", "subconsciente", "sabiduria",
                   "destino", "divino", "sombra", "sueño", "imaginacion", "guia", "interior", "mistic",
                   "esoteric", "llamado"], "intuición y mundo interior"),
    "creatividad": (["creatividad", "creativ", "inspiracion", "expresion", "arte", "habilidad", "talento",
                     "ingenio", "originalidad", "curiosidad"], "creatividad"),
    "trabajo": (["trabajo", "esfuerzo", "carrera", "inversion", "financier", "dinero", "material", "aprendizaje",
                 "diligencia", "perfeccionismo", "responsabilidad", "deber", "recursos", "maestria", "oficio",
                 "negocio", "calidad", "duro", "eficiencia"], "trabajo y recursos"),
    "control": (["control", "autoridad", "liderazgo", "poder", "dominacion", "limites", "lider", "rigidez",
                 "terquedad", "inflexib", "estructura", "influencia", "dominio", "posesiv", "esclavitud", "adiccion", "dependencia", "codependencia", "ataduras", "apego", "tentacion", "obsesion", "martirio", "dogma", "exigente", "posesion"],
                 "control y autoridad"),
    "libertad": (["libertad", "independencia", "liberacion", "romper", "desapego", "espontaneidad", "rebelion",
                  "autonomia", "recuperar el poder", "libre", "autosuficiencia", "dejar ir", "liberarse", "escapar", "independiente"], "libertad y liberación"),
    "miedo": (["miedo", "ansiedad", "preocupacion", "inseguridad", "autoduda", "cobardia", "pesadilla",
               "inquietud", "abrumad", "nervios", "impotencia", "debilidad", "timidez", "temor"],
               "miedo e inseguridad"),
    "exceso": (["imprudencia", "exceso", "extremos", "indulgencia", "codicia", "demasiado", "excesiv",
                "glotoner", "desmesura", "avaricia", "negligencia", "dependencia", "sobreproteccion"], "exceso o desmesura"),
    "esperanza": (["esperanza", "fe", "optimismo", "sanacion", "renovacion", "inspiracion", "curacion",
                   "perdon", "renacimiento", "recuperacion", "seguir adelante", "alivio", "resiliencia", "confianza", "autoconfianza", "absolucion"],
                   "esperanza y recuperación"),
}

OPPOSITE = {
    "comienzo": "cierre", "estabilidad": "cambio", "accion": "pausa", "abundancia": "perdida",
    "armonia": "conflicto", "claridad": "confusion", "control": "libertad", "esperanza": "miedo",
    "vinculos": "aislamiento",
}
OPPOSITE.update({v: k for k, v in list(OPPOSITE.items())})

TENSION_TEXT = {
    frozenset({"comienzo", "cierre"}): "algo termina mientras algo nuevo empieza: es una etapa de relevo",
    frozenset({"estabilidad", "cambio"}): "se busca seguridad en medio del movimiento: decide qué conservar y qué soltar",
    frozenset({"accion", "pausa"}): "el impulso choca con la necesidad de detenerse: calibra cuándo avanzar",
    frozenset({"abundancia", "perdida"}): "ganancia y pérdida conviven: no confundas este momento con el balance final",
    frozenset({"armonia", "conflicto"}): "la paz convive con el choque: algo pide resolverse para sostenerla",
    frozenset({"claridad", "confusion"}): "hay luz y niebla a la vez: verifica los hechos antes de decidir",
    frozenset({"control", "libertad"}): "la necesidad de orden se enfrenta al deseo de soltar",
    frozenset({"esperanza", "miedo"}): "la confianza pelea con la duda: apóyate en lo que sí está comprobado",
    frozenset({"vinculos", "aislamiento"}): "el deseo de conexión convive con el retraimiento",
}


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


_STEMS = {t: [_strip(s) for s in stems] for t, (stems, _) in THEMES.items()}


_NAME = {"accion": "acción", "armonia": "armonía", "perdida": "pérdida", "confusion": "confusión",
         "intuicion": "intuición", "vinculos": "vínculos"}

# tema -> (nombre corto EN, explicación EN)
THEMES_EN = {
    "comienzo": ("beginnings", "a beginning, something starting"),
    "cierre": ("endings", "an ending or a culmination"),
    "cambio": ("change", "change and movement"),
    "estabilidad": ("stability", "stability and solid ground"),
    "accion": ("action", "action and drive"),
    "pausa": ("pause", "pause and reflection"),
    "vinculos": ("bonds", "bonds and relationships"),
    "aislamiento": ("isolation", "isolation or distance"),
    "conflicto": ("conflict", "conflict or friction"),
    "armonia": ("harmony", "harmony and reconciliation"),
    "abundancia": ("abundance", "abundance and success"),
    "perdida": ("loss", "loss and hardship"),
    "claridad": ("clarity", "clarity and truth"),
    "confusion": ("confusion", "confusion or deception"),
    "intuicion": ("intuition", "intuition and the inner world"),
    "creatividad": ("creativity", "creativity"),
    "trabajo": ("work", "work and resources"),
    "control": ("control", "control and authority"),
    "libertad": ("freedom", "freedom and release"),
    "miedo": ("fear", "fear and insecurity"),
    "exceso": ("excess", "excess"),
    "esperanza": ("hope", "hope and recovery"),
}
TENSION_TEXT_EN = {
    frozenset({"comienzo", "cierre"}): "something ends while something new begins: this is a handover",
    frozenset({"estabilidad", "cambio"}): "you seek security in the middle of movement: decide what to keep and what to release",
    frozenset({"accion", "pausa"}): "drive clashes with the need to stop: judge when to move",
    frozenset({"abundancia", "perdida"}): "gain and loss coexist: do not take this moment for the final balance",
    frozenset({"armonia", "conflicto"}): "peace lives alongside friction: something needs resolving to keep it",
    frozenset({"claridad", "confusion"}): "there is light and fog at once: check the facts before deciding",
    frozenset({"control", "libertad"}): "the need for order confronts the wish to let go",
    frozenset({"esperanza", "miedo"}): "trust wrestles with doubt: lean on what is already proven",
    frozenset({"vinculos", "aislamiento"}): "the wish to connect lives alongside withdrawal",
}


def theme_name(theme: str) -> str:
    """Nombre corto del tema (para frases comparativas)."""
    return THEMES_EN[theme][0] if i18n.lang() == "en" else _NAME.get(theme, theme)


def theme_text(theme: str) -> str:
    return THEMES_EN[theme][1] if i18n.lang() == "en" else THEMES[theme][1]


def tension_text(pair: frozenset) -> str:
    return (TENSION_TEXT_EN if i18n.lang() == "en" else TENSION_TEXT).get(pair, "")


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


_STEMS = {t: [_strip(s) for s in stems] for t, (stems, _) in THEMES.items()}


def phrase_themes(phrase: str) -> set[str]:
    """Temas de una frase clave. Una frase que empieza por 'falta de/sin/mal...' invierte su tema."""
    p = _strip(phrase)
    neg = bool(re.match(r"^(falta|ausencia|sin|poca|poco|mala|malas|mal|no)\b", p))
    found = set()
    for theme, stems in _STEMS.items():
        for s in stems:
            if s.endswith(" ") and (" " + s) in (" " + p + " "):
                found.add(theme)
                break
            if not s.endswith(" ") and re.search(r"\b" + re.escape(s), p):
                found.add(theme)
                break
    if neg:
        found = {OPPOSITE[t] for t in found if t in OPPOSITE} | ({"perdida"} if not found else set())
    return found


DECAY = [1.0, 0.85, 0.7, 0.55, 0.45, 0.35]


def keywords_profile(kws: list[str]) -> Counter:
    """Perfil de temas de una lista de palabras clave: las primeras pesan más."""
    prof = Counter()
    for i, kw in enumerate(kws):
        w = DECAY[min(i, len(DECAY) - 1)]
        for t in phrase_themes(kw):
            prof[t] += w
    return prof


def coverage(phrases: list[str]) -> float:
    return sum(1 for p in phrases if phrase_themes(p)) / max(len(phrases), 1)
