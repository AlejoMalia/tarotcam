"""Base de conocimiento: las 78 cartas del tarot (Rider-Waite-Smith).

id 0-21 arcanos mayores; 22-35 bastos; 36-49 copas; 50-63 espadas; 64-77 oros.
Cada carta: nombre ES/EN, archivo en Wikimedia Commons, significado al derecho y al revés.
"""

from tarotcam.carddata import cards_en
from tarotcam import i18n

MAJOR = [
    ("El Loco", "The Fool", "Fool", "Nuevos comienzos, espontaneidad, salto de fe.",
     "Imprudencia, ingenuidad, miedo a arriesgar."),
    ("El Mago", "The Magician", "Magician", "Voluntad, habilidad, recursos para manifestar.",
     "Manipulación, talento sin usar, engaño."),
    ("La Sacerdotisa", "The High Priestess", "High_Priestess", "Intuición, misterio, saber interior.",
     "Secretos, intuición ignorada, desconexión."),
    ("La Emperatriz", "The Empress", "Empress", "Abundancia, creatividad, cuidado, naturaleza.",
     "Dependencia, bloqueo creativo, descuido propio."),
    ("El Emperador", "The Emperor", "Emperor", "Estructura, autoridad, estabilidad, liderazgo.",
     "Rigidez, tiranía, falta de disciplina."),
    ("El Hierofante", "The Hierophant", "Hierophant", "Tradición, enseñanza, creencias compartidas.",
     "Rebeldía, dogmatismo, romper con lo establecido."),
    ("Los Enamorados", "The Lovers", "Lovers", "Unión, elección alineada con los valores, amor.",
     "Desarmonía, decisión difícil, valores en conflicto."),
    ("El Carro", "The Chariot", "Chariot", "Determinación, avance, control de fuerzas opuestas.",
     "Pérdida de rumbo, agresividad, falta de control."),
    ("La Fuerza", "Strength", "Strength", "Coraje sereno, compasión, dominio de los impulsos.",
     "Duda de sí, impulsos sin control, inseguridad."),
    ("El Ermitaño", "The Hermit", "Hermit", "Introspección, búsqueda interior, guía.",
     "Aislamiento excesivo, rechazo de consejo."),
    ("La Rueda de la Fortuna", "Wheel of Fortune", "Wheel_of_Fortune", "Ciclos, cambio de suerte, destino.",
     "Mala racha, resistencia al cambio, giro inesperado."),
    ("La Justicia", "Justice", "Justice", "Equidad, verdad, causa y efecto.",
     "Injusticia, deshonestidad, evitar responsabilidad."),
    ("El Colgado", "The Hanged Man", "Hanged_Man", "Pausa, entrega, nueva perspectiva.",
     "Estancamiento, sacrificio inútil, demora."),
    ("La Muerte", "Death", "Death", "Final necesario, transformación, renovación.",
     "Resistencia al cambio, apego al pasado."),
    ("La Templanza", "Temperance", "Temperance", "Equilibrio, moderación, paciencia, síntesis.",
     "Exceso, desequilibrio, prisa."),
    ("El Diablo", "The Devil", "Devil", "Ataduras, apego, sombra, tentación.",
     "Liberación, romper cadenas, recuperar el poder."),
    ("La Torre", "The Tower", "Tower", "Ruptura súbita, revelación, caída de lo falso.",
     "Evitar el desastre, miedo al cambio, caída lenta."),
    ("La Estrella", "The Star", "Star", "Esperanza, sanación, inspiración, fe.",
     "Desánimo, desconfianza, esperanza perdida."),
    ("La Luna", "The Moon", "Moon", "Ilusión, intuición, miedos, lo oculto.",
     "Confusión que se aclara, miedos superados, engaño revelado."),
    ("El Sol", "The Sun", "Sun", "Alegría, éxito, claridad, vitalidad.",
     "Optimismo excesivo, alegría apagada, retraso."),
    ("El Juicio", "Judgement", "Judgement", "Llamada, renacer, balance, absolución.",
     "Autocrítica, duda, ignorar la llamada."),
    ("El Mundo", "The World", "World", "Culminación, plenitud, cierre de ciclo.",
     "Falta de cierre, algo inconcluso, estancamiento."),
]

# (nombre ES, nombre EN, derecho, revés) por número 1..14 y palo
SUITS = [
    ("Bastos", "Wands", "Wands", "fuego: acción, energía, ambición", [
        ("Chispa creativa, inicio lleno de energía.", "Falta de impulso, retraso."),
        ("Planificar, decidir el rumbo.", "Miedo a salir de la zona de confort."),
        ("Expansión, esperar resultados.", "Obstáculos, planes retrasados."),
        ("Celebración, hogar, estabilidad.", "Tensión en casa, celebración aplazada."),
        ("Competencia, conflicto menor.", "Evitar el conflicto, tensión interna."),
        ("Victoria, reconocimiento público.", "Caída del ego, falta de reconocimiento."),
        ("Defender la posición, perseverar.", "Agotamiento, rendirse."),
        ("Rapidez, noticias, movimiento.", "Retrasos, frustración."),
        ("Resistencia, última prueba.", "Agotamiento total, paranoia."),
        ("Carga excesiva, responsabilidades.", "Soltar peso, delegar."),
        ("Mensajero entusiasta, exploración.", "Ideas sin rumbo, impaciencia."),
        ("Aventura, pasión, acción impulsiva.", "Imprudencia, ira, dispersión."),
        ("Carisma, confianza, calidez.", "Celos, exigencia, temperamento."),
        ("Visión, liderazgo audaz.", "Despotismo, impulsividad."),
    ]),
    ("Copas", "Cups", "Cups", "agua: emociones, vínculos, intuición", [
        ("Nuevo amor o emoción, apertura.", "Emociones bloqueadas, vacío."),
        ("Unión, atracción mutua, pareja.", "Desequilibrio, ruptura de acuerdo."),
        ("Amistad, celebración, comunidad.", "Excesos, cotilleo, aislamiento."),
        ("Apatía, contemplación, oferta ignorada.", "Despertar, nuevas oportunidades."),
        ("Pérdida, duelo, mirar lo perdido.", "Aceptación, seguir adelante."),
        ("Nostalgia, infancia, recuerdos.", "Atrapado en el pasado."),
        ("Fantasía, muchas opciones, ilusión.", "Claridad, decisión, desengaño."),
        ("Dejar atrás, buscar algo más profundo.", "Miedo a partir, huida."),
        ("Deseo cumplido, satisfacción.", "Insatisfacción, vanidad."),
        ("Armonía familiar, plenitud emocional.", "Desunión, valores desalineados."),
        ("Mensaje emotivo, sensibilidad, creatividad.", "Inmadurez emocional, bloqueo."),
        ("Romántico, propuesta, seguir el corazón.", "Celos, ilusiones, humor cambiante."),
        ("Compasión, calma emocional, empatía.", "Manipulación emocional, desborde."),
        ("Madurez emocional, diplomacia.", "Frialdad, represión, volatilidad."),
    ]),
    ("Espadas", "Swords", "Swords", "aire: mente, verdad, conflicto", [
        ("Claridad, verdad, avance mental.", "Confusión, juicio nublado."),
        ("Decisión bloqueada, tregua.", "Indecisión, información oculta."),
        ("Dolor, corazón roto, verdad dura.", "Recuperación, perdón."),
        ("Descanso, recuperación, pausa.", "Agotamiento, inquietud."),
        ("Conflicto, victoria vacía.", "Reconciliación, cansancio de pelear."),
        ("Transición, alejarse de lo difícil.", "Resistencia a partir, viaje truncado."),
        ("Astucia, estrategia, sigilo.", "Conciencia, confesión."),
        ("Restricción, sentirse atrapado.", "Liberación, nueva perspectiva."),
        ("Ansiedad, pesadillas, preocupación.", "Esperanza, salir de la angustia."),
        ("Final doloroso, fondo, cierre.", "Recuperación, resistir lo inevitable."),
        ("Curiosidad, mente ágil, vigilancia.", "Palabras hirientes, precipitación."),
        ("Acción rápida, ambición, directo.", "Impaciencia, agresividad verbal."),
        ("Claridad, independencia, honestidad.", "Frialdad, dureza, amargura."),
        ("Autoridad intelectual, verdad, justicia.", "Abuso de poder, manipulación."),
    ]),
    ("Oros", "Pentacles", "Pents", "tierra: dinero, trabajo, cuerpo", [
        ("Oportunidad material, prosperidad.", "Oportunidad perdida, mala planificación."),
        ("Equilibrar prioridades, adaptarse.", "Desorden, sobrecarga."),
        ("Trabajo en equipo, oficio, maestría.", "Falta de colaboración, mediocridad."),
        ("Seguridad, control, ahorro.", "Avaricia, apego, miedo a perder."),
        ("Escasez, dificultad, sentirse excluido.", "Recuperación, ayuda disponible."),
        ("Generosidad, dar y recibir.", "Deudas, caridad condicionada."),
        ("Paciencia, evaluar la inversión.", "Impaciencia, esfuerzo sin fruto."),
        ("Aprendizaje, dedicación al oficio.", "Perfeccionismo, trabajo monótono."),
        ("Independencia, lujo, logro propio.", "Dependencia, exceso de trabajo."),
        ("Legado, riqueza familiar, estabilidad.", "Disputas, pérdida de patrimonio."),
        ("Estudio, nueva meta práctica.", "Procrastinación, falta de foco."),
        ("Constancia, responsabilidad, rutina.", "Estancamiento, terquedad."),
        ("Nutrir, practicidad, abundancia.", "Descuido, dependencia material."),
        ("Éxito sólido, seguridad, negocio.", "Codicia, rigidez, materialismo."),
    ]),
]
RANKS = ["As", "Dos", "Tres", "Cuatro", "Cinco", "Seis", "Siete", "Ocho", "Nueve", "Diez",
         "Sota", "Caballero", "Reina", "Rey"]
RANKS_EN = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Page", "Knight", "Queen", "King"]


def _build():
    cards = []
    for i, (es, en, com, up, rev) in enumerate(MAJOR):
        cards.append(dict(id=i, es=es, en=en, arcana="mayor", suit=None,
                          commons=f"RWS_Tarot_{i:02d}_{com}.jpg", upright=up, reversed=rev))
    nid = 22
    for s_es, s_en, s_com, theme, meanings in SUITS:
        for r in range(14):
            up, rev = meanings[r]
            cards.append(dict(
                id=nid, es=f"{RANKS[r]} de {s_es}", en=f"{RANKS_EN[r]} of {s_en}",
                arcana="menor", suit=s_es, theme=theme,
                commons=f"{s_com}{r + 1:02d}.jpg", upright=up, reversed=rev))
            nid += 1
    return cards


CARDS = _build()
BY_ID = {c["id"]: c for c in CARDS}
assert len(CARDS) == 78


# ---- metadatos para la lectura combinada -------------------------------------------------
MAJOR_ELEMENT = ["Aire", "Aire", "Agua", "Tierra", "Fuego", "Tierra", "Aire", "Agua", "Fuego", "Tierra",
                 "Fuego", "Aire", "Agua", "Agua", "Fuego", "Tierra", "Fuego", "Aire", "Agua", "Fuego",
                 "Fuego", "Tierra"]
SUIT_ELEMENT = {"Bastos": "Fuego", "Copas": "Agua", "Espadas": "Aire", "Oros": "Tierra"}

for _c in CARDS:
    if _c["arcana"] == "mayor":
        _c["element"], _c["num"] = MAJOR_ELEMENT[_c["id"]], _c["id"]
    else:
        _r = (_c["id"] - 22) % 14
        _c["element"], _c["num"] = SUIT_ELEMENT[_c["suit"]], _r + 1     # 11-14 = corte
        _c["court"] = _r >= 10


# ---- polaridad (-1 muy exigente ... +1 muy favorable) y palabras clave --------------------
POL_MAJOR = [.6, .7, .3, .8, .4, .3, .8, .6, .7, 0.0, .3, .2, -.1, -.4, .6, -.8, -.9, .9, -.3, 1.0, .6, .9]
POL_MINOR = {   # as .. diez, sota, caballero, reina, rey
    "Bastos":  [.7, .4, .6, .8, -.3, .8, .2, .5, -.1, -.5, .4, .3, .6, .6],
    "Copas":   [.8, .8, .7, -.2, -.6, .4, -.1, -.2, .9, .9, .5, .4, .6, .3],
    "Espadas": [.4, -.1, -.8, .1, -.5, .2, -.2, -.6, -.8, -.9, .2, .1, .3, .3],
    "Oros":    [.8, .2, .6, .1, -.6, .6, .1, .4, .8, .9, .5, .3, .6, .7],
}
for _c in CARDS:
    _c["polarity"] = POL_MAJOR[_c["id"]] if _c["arcana"] == "mayor" else POL_MINOR[_c["suit"]][_c["num"] - 1]


def _kb_keywords(card_id, reversed_, lang):
    try:
        from tarotcam.carddata import knowledge
    except ImportError:
        return []
    return knowledge.keywords(card_id, reversed_, lang)


def _base_text(card, reversed_, lang):
    if lang == "en":
        return cards_en.meanings(card["id"])[1 if reversed_ else 0]
    return card["reversed"] if reversed_ else card["upright"]


def keywords(card, reversed_=False, k=3, lang=None):
    """Palabras clave en el idioma pedido (por defecto el actual): de la base de conocimiento si existe,
    si no, del significado base. El motor analiza siempre con lang="es"."""
    lang = lang or i18n.lang()
    kws = _kb_keywords(card["id"], reversed_, lang)
    if kws:
        return [x.strip().lower() for x in kws[:k]]
    text = _base_text(card, reversed_, lang)
    return [p.strip().lower() for p in text.replace(".", ",").split(",") if p.strip()][:k]


def meaning(card, reversed_=False):
    """Texto de significado para mostrar, en el idioma actual."""
    kws = _kb_keywords(card["id"], reversed_, i18n.lang())
    if kws:
        t = ", ".join(x.strip().lower() for x in kws[:5])
        return t[:1].upper() + t[1:] + "."
    return _base_text(card, reversed_, i18n.lang())


# ---- correspondencias (número, elemento, astrología, extra) --------------------------------------
from tarotcam.carddata import correspondences  # noqa: E402

correspondences.annotate(CARDS)
