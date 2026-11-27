"""Tarot de Marseille: data, numbering, readings in both languages and (if the images are present) recognition."""
import random
import re

import numpy as np

from tarotcam import i18n
from tarotcam.carddata import cards, decks
from tarotcam.carddata.cards import BY_ID
from tarotcam.engine import narrator, reading
from tarotcam.engine.spreads import analyze
from tests.fixtures import GEOMETRY, SPANISH, tr

cards.set_system("marseille")
assert len(BY_ID) == 78 and len({c["fr"] for c in BY_ID.values()}) == 78
assert BY_ID[11]["num"] == 8 and BY_ID[8]["num"] == 11 and BY_ID[13]["fr"] == "L'Arcane sans nom"
assert BY_ID[16]["es"] == "La Casa de Dios" and BY_ID[36]["fr"] == "As de Coupe" and BY_ID[63]["fr"] == "Roi d'Épée"
assert all(c["upright"] and c["en_up"] and c["corr"]["numero"] and not c["corr"]["planets"] for c in BY_ID.values())
assert len({decks.commons_name(s, i) for s in ("cbd", "dodal") for i in range(78)}) == 156
assert decks.commons_name("cbd", 11) == "Ben-Dov_MA08.jpg" and decks.commons_name("dodal", 64) == "Jean_Dodal_D01.jpg"
print("OK  78 Marseille cards: French names, VIII Justice / XI Strength, no astrology, file names")

rng = random.Random(5)
count = 0
for _ in range(25):
    for geom in [g for g in GEOMETRY if len(g) <= 10]:
        ids = rng.sample(range(78), len(geom))
        tracks = [tr(i, x, y, a, rng.random() < .35, k + 1) for k, (i, (x, y, a)) in enumerate(zip(ids, geom))]
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            layout = analyze(tracks)
            items, secs = reading.compose(layout)
            story = narrator.compose(layout, rng.choice(narrator.FOCI))
            text = " ".join(story + [t for _, t in secs])
            assert "The High Priestess" not in text and "La Sacerdotisa" not in text and "La Torre" not in text
            if lang == "en":
                m = SPANISH.search(" ".join([x["name"] + " " + x["meaning"] for x in items] + [text]))
                assert not m, (m.group(0), text[:300])
            count += 1
print(f"OK  {count} Marseille readings in English and Spanish")
i18n.set_lang("en")
cards.set_system("rws")
assert BY_ID[16]["en"] == "The Tower" and BY_ID[8]["num"] == 8
print("OK  switching back to Rider-Waite-Smith")

if decks.folders("marseille"):
    import cv2
    from tarotcam.vision.recognizer import Deck, GlobalScanner
    from tests import sim
    cards.set_system("marseille")
    scanner = GlobalScanner(Deck(decks.folders("marseille")))
    for folder in decks.folders("marseille"):
        sim.DECK_DIR = folder
        gen = np.random.default_rng(1)
        ok = wrong = 0
        for cid in range(78):
            rev = bool(gen.integers(2))
            frame = sim.render([(cid, rev)], gen)[0]
            found = scanner.scan(frame)
            ok += any(f.card_id == cid for f in found)
            wrong += sum(f.card_id != cid for f in found)
        print(f"recognition {folder.name}: {ok}/78 identified, {wrong} wrong")
    cards.set_system("rws")
else:
    print("SKIP recognition: python -m tarotcam.tools.download_deck --deck marseille")
print("\nOK: test_marseille")
