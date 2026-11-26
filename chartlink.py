"""Links the cards on the table with a natal chart. Facts only: which card attributions touch which natal positions.

Strength of a resonance (strongest first):
  5  a natal planet or the Ascendant lies inside the card's own decan or zodiac span
  4  the card's sign is the person's Sun, Moon or Rising sign
  3  the card's planet is the Sun, the Moon or the ruler of the Rising sign
  2  where the card's planet sits in the chart (sign and house)
  1  natal planets placed in the card's sign
"""
from __future__ import annotations

from i18n import L, term
from natal import HOUSES, SIGNS, Chart

# regentes tradicionales
RULER = {"Aries": "Marte", "Tauro": "Venus", "Géminis": "Mercurio", "Cáncer": "Luna", "Leo": "Sol",
         "Virgo": "Mercurio", "Libra": "Venus", "Escorpio": "Marte", "Sagitario": "Júpiter",
         "Capricornio": "Saturno", "Acuario": "Saturno", "Piscis": "Júpiter"}


def card_span(card: dict) -> tuple[float, float] | None:
    """Tramo zodiacal propio de la carta (decanato de un pip, rango de un corte)."""
    signs = card["corr"]["signs"]
    if card["arcana"] == "menor" and 2 <= card["num"] <= 10:
        start = SIGNS.index(signs[0]) * 30 + ((card["num"] - 2) % 3) * 10
        return start, start + 10
    if card.get("court") and len(signs) == 2:
        start = SIGNS.index(signs[0]) * 30 + 20
        return start, start + 30
    return None


def _inside(deg: float, span) -> bool:
    return (deg - span[0]) % 360 < span[1] - span[0]


def _point(name: str) -> str:
    return L("Ascendant", "Ascendente") if name == "Asc" else term(name)


def _the(planet: str) -> str:
    """Planeta dentro de una frase: 'the Sun' / 'el Sol'."""
    article = {"Sol": ("the Sun", "el Sol"), "Luna": ("the Moon", "la Luna")}.get(planet)
    return L(*article) if article else term(planet)


def _placement(chart: Chart, planet: str) -> str:
    sign = term(chart.sign(planet))
    house = chart.house(chart.positions[planet])
    if house is None:
        return sign
    en, es = HOUSES[house]
    return L(f"{sign}, in house {house} ({en})", f"{sign}, en la casa {house} ({es})")


def resonances(chart: Chart, cards: list, limit: int = 3) -> list[tuple[int, str, str]]:
    """cards: estados de carta (reading.CS). -> [(fuerza, nombre de carta, frase)] sin repetir carta ni punto."""
    points = dict(chart.positions)
    if chart.ascendant is not None:
        points["Asc"] = chart.ascendant
    big = {chart.sign("Sol"): L("Sun sign", "signo solar")}
    if chart.time_known:
        big.setdefault(chart.sign("Luna"), L("Moon sign", "signo lunar"))
    if chart.asc_sign:
        big.setdefault(chart.asc_sign, L("Rising sign", "signo ascendente"))
    found = []
    for c in cards:
        card, name = c.card, c.label()
        corr, span = card["corr"], card_span(card)
        if span:
            hits = [p for p, deg in points.items() if _inside(deg, span) and (p != "Luna" or chart.time_known)]
            if hits:
                p = hits[0]
                found.append((5, c, p, L(
                    f"Your natal {_point(p)} falls exactly within the degrees of {name}, so this card speaks to you directly.",
                    f"Tu {_point(p)} natal cae justo en los grados de {name}: esta carta te habla de forma directa.")))
        for sign in corr["signs"]:
            if sign in big:
                found.append((4, c, sign, L(f"{name} carries {term(sign)}, your {big[sign]}.",
                                            f"{name} lleva {term(sign)}, tu {big[sign]}.")))
        for planet in corr["planets"]:
            if planet not in chart.positions or (planet == "Luna" and not chart.time_known):
                continue
            if planet in ("Sol", "Luna") or (chart.asc_sign and RULER[chart.asc_sign] == planet):
                role = (L("ruler of your chart", "regente de tu carta")
                        if chart.asc_sign and RULER[chart.asc_sign] == planet else L("one of your two lights", "una de tus dos luminarias"))
                answers = _the(planet).replace("el Sol", "al Sol") if L("en", "es") == "es" else _the(planet)
                found.append((3, c, planet, L(
                    f"{name} is tied to {answers}, {role}, placed at your birth in {_placement(chart, planet)}.",
                    f"{name} responde {answers if answers.startswith('al ') else 'a ' + answers}, {role}, "
                    f"que al nacer estaba en {_placement(chart, planet)}.")))
            else:
                found.append((2, c, planet, L(
                    f"For {name}, the planet is {term(planet)}, which in your chart sits in {_placement(chart, planet)}.",
                    f"El planeta de {name}, {term(planet)}, está en tu carta en {_placement(chart, planet)}.")))
        for sign in corr["signs"]:
            inside = [p for p in chart.positions if chart.sign(p) == sign and (p != "Luna" or chart.time_known)]
            if inside and sign not in big:
                names = ", ".join(term(p) for p in inside[:3])
                found.append((1, c, sign, L(f"{name} touches {term(sign)}, where you have {names}.",
                                            f"{name} toca {term(sign)}, donde tienes {names}.")))
    out, used_cards, used_points = [], set(), set()
    for strength, c, point, text in sorted(found, key=lambda f: (-f[0], -f[1].weight)):
        if c.card["id"] in used_cards or point in used_points:
            continue
        used_cards.add(c.card["id"])
        used_points.add(point)
        out.append((strength, c.name, text))
        if len(out) == limit:
            break
    return out


def elements(chart: Chart, table_element: str) -> str:
    """Compara el elemento que domina la mesa con el reparto de elementos de la carta natal."""
    balance = chart.element_balance()
    mine = max(balance, key=balance.get)
    share = balance[table_element]
    if table_element == mine:
        return L(f"The table speaks your own language: {term(mine)} leads both here and in your chart, "
                 "so the pull will feel familiar, even excessive.",
                 f"La mesa habla tu idioma: {mine} domina aquí y también en tu carta, así que el impulso "
                 "te resultará familiar, incluso excesivo.")
    if share < 0.15:
        return L(f"{term(table_element)} dominates the table yet is scarce in your chart, which leans to {term(mine)}: "
                 "this asks for something that does not come naturally.",
                 f"{table_element} domina la mesa y escasea en tu carta, que se inclina hacia {mine}: "
                 "se te pide algo que no te sale de forma natural.")
    return L(f"Your chart leans to {term(mine)} while the table brings {term(table_element)}, "
             "a different resource you can borrow.",
             f"Tu carta se inclina hacia {mine} y la mesa trae {table_element}, "
             "un recurso distinto que puedes aprovechar.")


def summary(chart: Chart) -> str:
    parts = [L(f"Sun in {term(chart.sign('Sol'))}", f"Sol en {chart.sign('Sol')}")]
    moon = L(f"Moon in {term(chart.sign('Luna'))}", f"Luna en {chart.sign('Luna')}")
    parts.append(moon if chart.time_known else moon + L(" (approximate)", " (aproximada)"))
    if chart.asc_sign:
        parts.append(L(f"{term(chart.asc_sign)} rising", f"Ascendente {chart.asc_sign}"))
    return ", ".join(parts)
