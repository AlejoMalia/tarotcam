"""Astronomy checks (independent of our formulas), city search and profile handling. Uses fictitious people."""
import math
import tempfile
from pathlib import Path

import ephem

import natal


def diff(a, b):
    return abs((a - b + 180) % 360 - 180)


# 1) hechos astronómicos conocidos: el Sol entra en Aries en el equinoccio y en Cáncer en el solsticio
for when, expected in ((ephem.next_vernal_equinox("2000/1/1"), 0), (ephem.next_summer_solstice("1990/1/1"), 90),
                       (ephem.next_autumnal_equinox("2015/1/1"), 180)):
    assert diff(natal.longitudes(when)["Sol"], expected) < 0.02, (when, natal.longitudes(when)["Sol"])
print("OK  Sun at 0°/90°/180° on equinoxes and solstice")

# 2) al salir el Sol, el Sol está sobre el Ascendente; al ponerse, sobre el Descendente
worst = 0
for lat, lon in ((40.42, -3.70), (-34.6, -58.4), (51.5, -0.12), (19.4, -99.1), (59.9, 10.7), (1.35, 103.8)):
    for start in ("1975/1/10", "1990/4/5", "2003/7/20", "2020/10/30"):
        o = ephem.Observer()
        o.lat, o.lon, o.date, o.pressure, o.horizon = str(lat), str(lon), start, 0, "0"
        sun = ephem.Sun()
        for event, offset in ((o.next_rising(sun, use_center=True), 0), (o.next_setting(sun, use_center=True), 180)):
            asc, _ = natal._angles(event, lat, lon)
            worst = max(worst, diff((asc + offset) % 360, natal.longitudes(event)["Sol"]))
assert worst < 1.0, worst
print(f"OK  Sun on the Ascendant at sunrise / Descendant at sunset in 48 cases (worst {worst:.2f}°)")

# 3) Medio Cielo = Sol al mediodía solar
o = ephem.Observer()
o.lat, o.lon, o.date = "40.42", "-3.70", "1995/3/1"
noon = o.next_transit(ephem.Sun())
_, mc = natal._angles(noon, 40.42, -3.70)
assert diff(mc, natal.longitudes(noon)["Sol"]) < 0.6, (mc, natal.longitudes(noon)["Sol"])
print("OK  Sun on the Midheaven at solar noon")

# 4) carta completa, horario histórico y casas
c = natal.compute("Test Person", "1990-07-15", "12:00", 40.4165, -3.70256, "Europe/Madrid", "Madrid, ES")
assert c.local.endswith("+02:00") and c.sign("Sol") == "Cáncer" and c.house(c.ascendant) == 1
assert abs(sum(c.element_balance().values()) - 1) < 1e-9 and len(c.positions) == 10
assert natal.compute("T", "1990-01-15", "12:00", 40.4, -3.7, "Europe/Madrid").local.endswith("+01:00")
u = natal.compute("T", "1990-07-15", None, 40.4, -3.7, "Europe/Madrid")
assert u.ascendant is None and u.house(10) is None and not u.time_known
for bad in (("1700-01-01", "12:00", 0, 0), ("1990-01-01", "12:00", 95, 0)):
    try:
        natal.compute("T", *bad, "UTC")
        raise AssertionError(bad)
    except ValueError:
        pass
print("OK  daylight saving history, houses, unknown time and invalid input")

# 5) ciudades offline
assert natal.search_city("Madrid")[0]["countrycode"] == "ES"
assert natal.search_city("córdoba, AR")[0]["timezone"].startswith("America/Argentina")
assert natal.search_city("Mexico City")[0]["countrycode"] == "MX" and not natal.search_city("zzzzqqq")
print("OK  offline city search (accents, country filter)")

# 6) perfil: se guarda con permisos privados y se vuelve a leer
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "profile.json"
    natal.save(dict(name="Test", date="1990-07-15", time="12:00", lat=40.4, lon=-3.7, tz="Europe/Madrid"), p)
    assert oct(p.stat().st_mode)[-3:] == "600" and natal.load(p).sign("Sol") == "Cáncer"
    assert natal.load(Path(d) / "missing.json") is None
print("OK  private profile file")
print("\nOK: test_natal")
