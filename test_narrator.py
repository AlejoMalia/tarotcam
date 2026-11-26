"""Narrative writer: deterministic, complete, non-repetitive, bilingual; and the local-model connector."""
import json
import random
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import i18n
import llm
import narrator
from cards import BY_ID
from spreads import analyze
from test_i18n_data import GEOMETRY, SPANISH, tr


def sentences(paragraphs):
    return [s.strip().lower() for p in paragraphs for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]


rng = random.Random(11)
count, longest = 0, 0
for _ in range(60):
    for geom in GEOMETRY:
        ids = rng.sample(range(78), len(geom))
        tracks = [tr(i, x, y, a, rng.random() < .35, k + 1) for k, (i, (x, y, a)) in enumerate(zip(ids, geom))]
        focus = rng.choice(narrator.FOCI)
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            layout = analyze(tracks)
            text = narrator.compose(layout, focus)
            assert text == narrator.compose(layout, focus), "not deterministic"
            joined = " ".join(text)
            assert not re.search(r"[{}]|  |\.\.|: [^.]{0,60}: |\bde el\b|\ba el\b", joined), (lang, joined[:300])
            sents = sentences(text)
            dup = {s for s in sents if sents.count(s) > 1}
            assert not dup, (lang, len(geom), dup)
            if len(geom) <= 10:
                for i in ids:
                    name = narrator.card_name(BY_ID[i]).lower()
                    name = re.sub(r"^(el|la|los|las|the) ", "", name)
                    assert name in joined.lower(), (lang, name, joined)
            if lang == "en":
                m = SPANISH.search(joined)
                assert not m, (m.group(0), joined[:300])
            count += 1
            longest = max(longest, len(joined))
print(f"OK  {count} narratives: deterministic, no repeated sentences, every card named (≤10), longest {longest} chars")

# the story fits on screen without truncation, even with the longest focus
from PIL import Image, ImageDraw
import ui
draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
smallest = 99
for _ in range(40):
    for geom in [g for g in GEOMETRY if len(g) <= 10]:
        ids = rng.sample(range(78), len(geom))
        tracks = [tr(i, x, y, a, rng.random() < .35, k + 1) for k, (i, (x, y, a)) in enumerate(zip(ids, geom))]
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            story = narrator.compose(analyze(tracks), rng.choice(narrator.FOCI))
            size, placed = ui.detail_layout(draw, [("", p) for p in story], ui.VID_H + 78, ui.CANVAS_H - 44, 2, (18, 9))
            assert not placed[-1][2].endswith("…"), (lang, len(geom))
            smallest = min(smallest, size)
print(f"OK  the story always fits (1-10 cards); smallest font used: {smallest} px")

# with a natal chart: personalised, bilingual, still fits and never repeats
import natal
CHART = natal.compute("Alex Demo", "1990-07-15", "12:00", 40.4165, -3.70256, "Europe/Madrid", "Madrid, ES")
NOTIME = natal.compute("Alex Demo", "1985-02-03", None, -34.6, -58.4, "America/Argentina/Buenos_Aires")
hits = 0
for _ in range(50):
    for geom in [g for g in GEOMETRY if len(g) <= 10]:
        ids = rng.sample(range(78), len(geom))
        tracks = [tr(i, x, y, a, rng.random() < .35, k + 1) for k, (i, (x, y, a)) in enumerate(zip(ids, geom))]
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            chart = rng.choice([CHART, NOTIME])
            layout = analyze(tracks)
            text = narrator.compose(layout, rng.choice(narrator.FOCI), chart)
            joined = " ".join(text)
            assert text[0].startswith("Alex Demo, "), text[0]
            sents = sentences(text)
            assert len(sents) == len(set(sents)), (lang, joined)
            assert not re.search(r"[{}]|  |\bde el\b|\ba el\b", joined), joined
            if chart is NOTIME:
                assert "rising" not in joined.lower() and "Ascend" not in joined and " house " not in joined, joined
            if lang == "en":
                m = SPANISH.search(joined)
                assert not m, (m.group(0), joined)
            size, placed = ui.detail_layout(draw, [("", p) for p in text], ui.VID_H + 78, ui.CANVAS_H - 44, 2, (18, 9))
            assert not placed[-1][2].endswith("…"), (lang, len(geom))
            import reading
            secs = reading.compose(layout, chart)[1]
            assert any(t in ("Your chart", "Tu carta astral") for t, _ in secs)
            body = [s for s in secs if s[0] != reading.headline_key()]
            _, _, placed = ui.analysis_layout(draw, body, ui.VID_H + 78, ui.CANVAS_H - 44)
            assert [p[2] for p in placed if p[3]] == [t.upper() for t, _ in body], "analysis truncated with chart"
            hits += "your chart" in joined.lower() or "tu carta" in joined.lower()
print(f"OK  natal chart readings: personalised, no repetition, fit on screen ({hits} checked)")
# the Seven of Wands decan (20-30 Leo) lights up for a natal planet placed there
import chartlink, reading
c = natal.Chart("T", "", "2000-01-01T12:00", True, {**CHART.positions, "Marte": 145.0}, CHART.ascendant, CHART.midheaven)
i18n.set_lang("en")
found = chartlink.resonances(c, reading._states(analyze([tr(28, 320, 240, 0, False, 1)])))
assert found[0][0] == 5 and "Mars" in found[0][2], found
print("OK  exact decan contact is detected and ranked first")

# distinct tables read differently
i18n.set_lang("en")
openings = {narrator.compose(analyze([tr(a, 200, 240, 0, False, 1), tr(b, 440, 240, 0, False, 2)]))[0]
            .split(" ")[0] for a, b in [(rng.randrange(0, 39), rng.randrange(39, 78)) for _ in range(60)]}
print(f"OK  {len(openings)} different opening words across 60 tables")
assert len(openings) >= 3

# ------------------------------------------------------------- local model connector (fake server)
REPLY = {"fail": False}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"data": [{"id": "fake-model"}]})

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert "The Tower" in req["messages"][1]["content"]
        if REPLY["fail"]:
            return self._send({}, 500)
        self._send({"choices": [{"message": {"content": "<think>x</think>**First** paragraph.\n\nSecond one."}}]})


server = HTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}/v1"
layout = analyze([tr(16, 200, 240, 0, False, 1), tr(19, 440, 240, 0, False, 2)])
try:
    llm.LocalWriter("http://example.com/v1")
    raise AssertionError("remote host accepted")
except ValueError:
    print("OK  remote model servers are refused")
w = llm.LocalWriter(url, "fake-model", settle=0)
assert w.available() and not llm.LocalWriter(url, "other-model").available()
assert w.request(layout, "general") is None              # no bloquea
deadline = time.time() + 5
out = None
while out is None and time.time() < deadline:
    out = w.request(layout, "general")
    time.sleep(0.05)
assert out == ["First paragraph.", "Second one."], out
print("OK  local model: non-blocking, cached, output cleaned")
REPLY["fail"] = True
w2 = llm.LocalWriter(url, "fake-model", settle=0)
for _ in range(60):
    assert w2.request(layout, "love") is None
    if "failed" in w2.status:
        break
    time.sleep(0.05)
assert "failed" in w2.status
print("OK  local model failure falls back to the built-in writer")
server.shutdown()
i18n.set_lang("en")
print("\nOK: test_narrator")
