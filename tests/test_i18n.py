"""Bilingual checks: no Spanish leaks into English readings, and both languages give the same reading."""
import random

from tarotcam import i18n
from tarotcam.carddata import knowledge
from tarotcam.engine import reading
from tarotcam.engine.spreads import MODES, analyze
from tests.fixtures import GEOMETRY, SPANISH, tr

def texts(tracks, mode):
    layout = analyze(tracks, mode)
    items, secs = reading.compose(layout)
    out = [layout.name, layout.note]
    for it in items:
        out += [it["pos"], it["name"], it["meaning"]]
        out += [str(v) for k, v in it["corr"].items() if k not in ("planets", "signs", "glyph")]
    for title, body in secs:
        out += [title, body]
    return layout, items, secs, out


def run(label, rounds):
    rng = random.Random(7)
    checked = 0
    for _ in range(rounds):
        for geom in GEOMETRY:
            ids = rng.sample(range(78), len(geom))
            revs = [rng.random() < .35 for _ in ids]
            tracks = [tr(i, x, y, a, r, k + 1) for k, (i, r, (x, y, a)) in enumerate(zip(ids, revs, geom))]
            mode = rng.choice(MODES + ["auto"] * 6)
            i18n.set_lang("en")
            lay_en, it_en, s_en, out = texts(tracks, mode)
            for s in out:
                m = SPANISH.search(s)
                assert not m, f"[{label}] Spanish leaked: {m.group(0)!r} in {s[:160]!r}"
            i18n.set_lang("es")
            lay_es, it_es, s_es, _ = texts(tracks, mode)
            assert lay_en.kind == lay_es.kind
            assert [x["id"] for x in it_en] == [x["id"] for x in it_es]
            assert len(s_en) == len(s_es), (label, [t for t, _ in s_en], [t for t, _ in s_es])
            checked += 1
    print(f"OK  {label}: {checked} readings, English free of Spanish, same structure in both languages")


def check_detail_complete(rounds=30):
    """La lectura detallada muestra todas las secciones (hasta 10 cartas) en ambos idiomas."""
    from PIL import Image, ImageDraw
    from tarotcam.interface import ui
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    rng = random.Random(3)
    for lang in i18n.LANGS:
        i18n.set_lang(lang)
        for _ in range(rounds):
            for geom in [g for g in GEOMETRY if len(g) <= 10]:
                ids = rng.sample(range(78), len(geom))
                tracks = [tr(i, x, y, a, rng.random() < .35, k + 1) for k, (i, (x, y, a)) in enumerate(zip(ids, geom))]
                _, secs = reading.compose(analyze(tracks))
                body = [s for s in secs if s[0] != reading.headline_key()]
                _, _, placed = ui.analysis_layout(d, body, ui.VID_H + 78, ui.CANVAS_H - 44)
                shown = [p[2] for p in placed if p[3]]
                assert shown == [t.upper() for t, _ in body], (lang, len(geom), shown)
                assert not placed[-1][2].endswith("…"), (lang, len(geom), "truncated")
    print("OK  detailed view shows every section, nothing truncated (1-10 cards, both languages)")


check_detail_complete()
run("with knowledge base" if knowledge.available() else "built-in meanings", 40)
if knowledge.available():
    saved = dict(knowledge.KB)
    knowledge.KB.clear()
    run("built-in meanings (public repo)", 40)
    knowledge.KB.update(saved)
i18n.set_lang("en")
print("\nOK: test_i18n")
