"""The three datasets cover the 78 cards, and StarTarot independently confirms our correspondences."""
import datasets
import i18n
from cards import BY_ID
from correspondences import build

if not datasets.available():
    print("SKIP: run python fetch_datasets.py first\nOK: test_datasets")
    raise SystemExit
for source in ("tarotoo", "smallcat", "startarot"):
    n = sum(source in e for e in datasets.DATA.values())
    assert n == 78, (source, n)
    print(f"OK  {source}: 78/78 cards matched by name")
for area in datasets.AREAS:
    missing = [(i, r) for i in range(78) for r in (False, True) if not datasets.area_text(i, area, r)]
    print(f"OK  area '{area}': {156 - len(missing)}/156 texts")
    if area == "money":                          # smallcat only gives finance texts for the major arcana
        assert all(i >= 22 for i, _ in missing), missing[:5]
    else:
        assert not missing, missing[:5]

diffs, checked = [], 0
for cid in range(78):
    ref, mine = datasets.correspondence(cid), build(BY_ID[cid], "en")
    if ref.get("hebrew_letter"):
        checked += 1
        norm = lambda s: s.lower().replace("au", "av").replace("tz", "ts").replace("ch", "h").replace("q", "k").rstrip("h")[:3]
        if norm(ref["hebrew_letter"]) != norm(mine["extra"]):
            diffs.append((cid, "letter", ref["hebrew_letter"], mine["extra"]))
        if ref.get("hebrew_letter_char") and ref["hebrew_letter_char"] != mine["glyph"]:
            diffs.append((cid, "glyph", ref["hebrew_letter_char"], mine["glyph"]))
    card = BY_ID[cid]
    if card["arcana"] == "menor" and 2 <= card["num"] <= 10:
        checked += 1
        got = (ref.get("planet"), ref.get("zodiac"))
        want = tuple(mine["astro"].split(" in "))
        if got != want:
            diffs.append((cid, "decan", got, want))
for d in diffs:
    print("DIFF", BY_ID[d[0]]["en"], d[1:])
print(f"Cross-check against StarTarot (Golden Dawn sources): {checked} attributions, {len(diffs)} differences")
assert not diffs
print("\nOK: test_datasets")
