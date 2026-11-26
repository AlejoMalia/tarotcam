#!/usr/bin/env python3
"""Natal chart, computed entirely on this machine (PyEphem + an offline city list). Nothing is sent anywhere.

  python natal.py            interactive setup (name, date, time, birthplace); saves ~/.tarotcam/profile.json
  python natal.py --show     print the saved chart
  python natal.py --delete   delete the saved profile

Tropical zodiac, geocentric apparent positions, whole-sign houses. Without a birth time the chart uses local noon
and omits Ascendant, Midheaven and houses (and the Moon is flagged as uncertain).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import ephem

import i18n
from i18n import L, term

PROFILE = Path(os.environ.get("TAROTCAM_PROFILE", Path.home() / ".tarotcam" / "profile.json"))
SIGNS = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio",
         "Acuario", "Piscis"]
SIGN_ELEMENT = {s: ("Fuego", "Tierra", "Aire", "Agua")[i % 4] for i, s in enumerate(SIGNS)}
BODIES = {"Sol": ephem.Sun, "Luna": ephem.Moon, "Mercurio": ephem.Mercury, "Venus": ephem.Venus,
          "Marte": ephem.Mars, "Júpiter": ephem.Jupiter, "Saturno": ephem.Saturn, "Urano": ephem.Uranus,
          "Neptuno": ephem.Neptune, "Plutón": ephem.Pluto}
HOUSES = {
    1: ("identity and the way you start things", "identidad y forma de empezar las cosas"),
    2: ("money, resources and self-worth", "dinero, recursos y valor propio"),
    3: ("communication, learning and your close surroundings", "comunicación, aprendizaje y entorno cercano"),
    4: ("home, family and roots", "hogar, familia y raíces"),
    5: ("creativity, pleasure and romance", "creatividad, placer y romance"),
    6: ("daily work, health and habits", "trabajo diario, salud y hábitos"),
    7: ("partnership and one-to-one bonds", "pareja y vínculos de tú a tú"),
    8: ("intimacy, shared resources and transformation", "intimidad, recursos compartidos y transformación"),
    9: ("beliefs, study and travel", "creencias, estudios y viajes"),
    10: ("vocation, reputation and public life", "vocación, reputación y vida pública"),
    11: ("friends, groups and projects", "amistades, grupos y proyectos"),
    12: ("solitude, the unconscious and closure", "soledad, inconsciente y cierres"),
}


@dataclass
class Chart:
    name: str
    place: str
    local: str                      # fecha (y hora) local, ISO
    time_known: bool
    positions: dict                 # planeta -> longitud eclíptica en grados
    ascendant: float | None
    midheaven: float | None

    def sign(self, body: str) -> str:
        return SIGNS[int(self.positions[body] // 30)]

    def degree(self, body: str) -> float:
        return self.positions[body] % 30

    @property
    def asc_sign(self) -> str | None:
        return None if self.ascendant is None else SIGNS[int(self.ascendant // 30)]

    def house(self, longitude: float) -> int | None:
        """Casa por signos completos: la casa 1 es el signo del Ascendente."""
        if self.ascendant is None:
            return None
        return (int(longitude // 30) - int(self.ascendant // 30)) % 12 + 1

    def element_balance(self) -> dict[str, float]:
        weights = {"Sol": 3, "Luna": 3, "Mercurio": 2, "Venus": 2, "Marte": 2}
        out = dict.fromkeys(("Fuego", "Agua", "Aire", "Tierra"), 0.0)
        for body in self.positions:
            out[SIGN_ELEMENT[self.sign(body)]] += weights.get(body, 1)
        if self.asc_sign:
            out[SIGN_ELEMENT[self.asc_sign]] += 3
        total = sum(out.values())
        return {k: v / total for k, v in out.items()}


def _angles(date: ephem.Date, lat: float, lon: float) -> tuple[float, float]:
    """Ascendente y Medio Cielo (grados eclípticos)."""
    observer = ephem.Observer()
    observer.date, observer.lat, observer.lon = date, str(lat), str(lon)
    ramc = float(observer.sidereal_time())
    centuries = (float(date) - float(ephem.Date("2000/1/1 12:00"))) / 36525
    eps = math.radians(23.4392911 - 0.0130042 * centuries)
    phi = math.radians(lat)
    asc = math.atan2(math.cos(ramc), -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)))
    mc = math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))
    return math.degrees(asc) % 360, math.degrees(mc) % 360


def longitudes(date: ephem.Date) -> dict[str, float]:
    out = {}
    for name, cls in BODIES.items():
        body = cls()
        body.compute(date, epoch=date)
        ecl = ephem.Ecliptic(ephem.Equatorial(body.g_ra, body.g_dec, epoch=date), epoch=date)
        out[name] = math.degrees(float(ecl.lon)) % 360
    return out


def compute(name: str, date: str, time: str | None, lat: float, lon: float, tz: str, place: str = "") -> Chart:
    """date 'YYYY-MM-DD'; time 'HH:MM' o None; tz nombre IANA (p. ej. 'Europe/Madrid')."""
    day = dt.date.fromisoformat(date)
    if not 1800 <= day.year <= 2100:
        raise ValueError("year must be between 1800 and 2100")
    if not -90 < lat < 90 or not -180 <= lon <= 180:
        raise ValueError("invalid coordinates")
    clock = dt.time.fromisoformat(time) if time else dt.time(12, 0)
    local = dt.datetime.combine(day, clock, tzinfo=ZoneInfo(tz))      # aplica el horario histórico de la zona
    utc = local.astimezone(dt.timezone.utc)
    e = ephem.Date(utc.replace(tzinfo=None))
    asc = mc = None
    if time and abs(lat) < 66.5:                                      # sobre los círculos polares el Asc se degrada
        asc, mc = _angles(e, lat, lon)
    return Chart(name.strip(), place, local.isoformat(timespec="minutes"), bool(time), longitudes(e), asc, mc)


# ------------------------------------------------------------------ ciudades (offline)
def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn").strip()


def search_city(query: str, limit: int = 8) -> list[dict]:
    """'Madrid' o 'Cordoba, AR'. Ordena por coincidencia exacta y población."""
    import geonamescache
    name, _, country = (p.strip() for p in query.partition(","))
    wanted = _plain(name)
    if not wanted:
        return []
    exact, partial = [], []
    for city in geonamescache.GeonamesCache(min_city_population=5000).get_cities().values():
        if country and city["countrycode"].lower() != country.lower():
            continue
        main = _plain(city["name"])
        if main == wanted or any(_plain(a) == wanted for a in city.get("alternatenames", []) if a):
            exact.append(city)
        elif main.startswith(wanted):
            partial.append(city)
    return sorted(exact, key=lambda c: -c["population"])[:limit] or sorted(partial, key=lambda c: -c["population"])[:limit]


# ------------------------------------------------------------------ perfil
def save(data: dict, path: Path = PROFILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    path.chmod(0o600)                                                  # solo legible por el usuario


def load(path: Path = PROFILE) -> Chart | None:
    try:
        d = json.loads(path.read_text())
        return compute(d["name"], d["date"], d.get("time"), d["lat"], d["lon"], d["tz"], d.get("place", ""))
    except (OSError, ValueError, KeyError):
        return None


def describe(chart: Chart) -> str:
    def spot(deg: float) -> str:
        return f"{term(SIGNS[int(deg // 30)])} {int(deg % 30):2d}°{int(deg % 1 * 60):02d}'"

    lines = [f"{chart.name} · {chart.local.replace('T', ' ')} · {chart.place}"]
    for body, deg in chart.positions.items():
        house = chart.house(deg)
        lines.append(f"  {term(body):10s} {spot(deg)}" + (L(f"   house {house}", f"   casa {house}") if house else ""))
    if chart.ascendant is not None:
        lines.append(f"  {L('Ascendant', 'Ascendente'):10s} {spot(chart.ascendant)}")
        lines.append(f"  {L('Midheaven', 'Medio Cielo'):10s} {spot(chart.midheaven)}")
    if not chart.time_known:
        lines.append(L("  (no birth time: local noon used, no Ascendant or houses, Moon sign approximate)",
                       "  (sin hora de nacimiento: mediodía local, sin Ascendente ni casas, Luna aproximada)"))
    return "\n".join(lines)


# ------------------------------------------------------------------ asistente
def _ask(prompt: str, parse):
    while True:
        try:
            return parse(input(prompt).strip())
        except (ValueError, KeyError, IndexError) as e:
            print("  ✗", e)


def _parse_date(s: str) -> str:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(L("use YYYY-MM-DD or DD/MM/YYYY", "usa AAAA-MM-DD o DD/MM/AAAA"))


def _parse_time(s: str) -> str | None:
    return dt.datetime.strptime(s, "%H:%M").strftime("%H:%M") if s else None


def setup(path: Path = PROFILE) -> Chart:
    print(L("Natal chart setup. Everything stays on this computer.\n",
            "Configurar carta astral. Todo se queda en este ordenador.\n"))
    name = _ask(L("Name: ", "Nombre: "), lambda s: s or (_ for _ in ()).throw(ValueError(L("required", "obligatorio"))))
    date = _ask(L("Birth date (YYYY-MM-DD or DD/MM/YYYY): ", "Fecha de nacimiento (AAAA-MM-DD o DD/MM/AAAA): "), _parse_date)
    time = _ask(L("Birth time HH:MM (Enter if unknown): ", "Hora de nacimiento HH:MM (Intro si no la sabes): "), _parse_time)
    while True:
        query = input(L("Birthplace (city, or city,COUNTRY like 'Cordoba,AR'; 'm' for coordinates): ",
                        "Lugar de nacimiento (ciudad, o ciudad,PAÍS como 'Cordoba,AR'; 'm' para coordenadas): ")).strip()
        if query.lower() == "m":
            lat = _ask(L("Latitude: ", "Latitud: "), float)
            lon = _ask(L("Longitude (east positive): ", "Longitud (este positivo): "), float)
            tz = _ask(L("Time zone (e.g. Europe/Madrid): ", "Zona horaria (p. ej. Europe/Madrid): "),
                      lambda s: (ZoneInfo(s), s)[1] if s else (_ for _ in ()).throw(ValueError("required")))
            place = f"{lat:.3f}, {lon:.3f}"
            break
        found = search_city(query)
        if not found:
            print(L("  Not found. Try a nearby larger town or 'm'.", "  No encontrada. Prueba una ciudad cercana o 'm'."))
            continue
        for i, c in enumerate(found, 1):
            print(f"  {i}. {c['name']}, {c['countrycode']}  (pop. {c['population']:,})  {c['timezone']}")
        pick = _ask(L("Number (0 to search again): ", "Número (0 para buscar otra): "),
                    lambda s: int(s or 1) if 0 <= int(s or 1) <= len(found) else int("x"))
        if pick:
            c = found[pick - 1]
            lat, lon, tz, place = c["latitude"], c["longitude"], c["timezone"], f"{c['name']}, {c['countrycode']}"
            break
    data = dict(name=name, date=date, time=time, lat=lat, lon=lon, tz=tz, place=place)
    chart = compute(**data)
    save(data, path)
    print("\n" + describe(chart))
    print(L(f"\nSaved to {path}. Delete it with: python natal.py --delete",
            f"\nGuardado en {path}. Bórralo con: python natal.py --delete"))
    return chart


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--lang", choices=i18n.LANGS, default="en")
    a = ap.parse_args()
    i18n.set_lang(a.lang)
    if a.delete:
        PROFILE.unlink(missing_ok=True)
        print(L("Profile deleted.", "Perfil borrado."))
    elif a.show:
        chart = load()
        print(describe(chart) if chart else L("No saved profile.", "No hay perfil guardado."))
    else:
        try:
            setup()
        except (KeyboardInterrupt, EOFError):
            print()
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
