#!/usr/bin/env python3
"""Convierte los documentos de simbología en una base de conocimiento estructurada (knowledge/kb.json).

Fuentes (rutas por defecto = tu iCloud Drive):
  Tarot_simb-cartas.rtf     palabras clave al derecho / al revés de las 78 cartas, 6 idiomas (se usa ES y EN)
  SymboloftheCards.rtf      simbología y 'representación en lecturas' (solo los 22 arcanos mayores tienen
                            símbolos y aspectos nombrados; los menores traen un párrafo)

Salida: knowledge/kb.json  { id: {es_up, es_rev, en_up, en_rev, intro, symbols[], aspects[], closing} }
Estos textos son de terceros: knowledge/ está en .gitignore y no se publica con el repo.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from tarotcam import paths
from tarotcam.carddata.cards import CARDS

ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
OUT = paths.KNOWLEDGE_FILE


def rtf_to_text(path: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "x.txt"
        subprocess.run(["textutil", "-convert", "txt", "-output", str(out), str(path)], check=True)
        return out.read_text().split("\n")


def norm(name: str) -> str:
    n = name.lower().replace("judgment", "judgement").replace("’", "'")
    n = re.sub(r"^the ", "", n)
    return re.sub(r"[^a-z ]", "", n).strip()


NAME_TO_ID = {norm(c["en"]): c["id"] for c in CARDS}


def split_kw(s: str) -> list[str]:
    return [k.strip() for k in s.split(",") if k.strip()]


def parse_zaiphira(lines):
    """-> {id: {en_up, en_rev, es_up, es_rev}}"""
    out, cur, name = {}, None, None
    for ln in lines:
        m = re.match(r"^(\d{2})\. (.+)$", ln.strip())
        if m:
            num, name = int(m.group(1)), m.group(2).strip()
            cur = NAME_TO_ID.get(norm(name))
            if cur is None:
                raise SystemExit(f"Nombre sin correspondencia: {name!r}")
            if cur != num - 1:
                raise SystemExit(f"Orden inesperado: {num} {name} -> id {cur}")
            out[cur] = {}
            continue
        m = re.match(r"^\[(ENGLISH|ESPAÑOL)\]\s*↑\s*(.+?)\s*\|\s*↓\s*(.+)$", ln.strip())
        if m and cur is not None:
            k = "en" if m.group(1) == "ENGLISH" else "es"
            out[cur][f"{k}_up"], out[cur][f"{k}_rev"] = split_kw(m.group(2)), split_kw(m.group(3))
    return out


HDR = re.compile(r"^(\d+\. .+|(Ace|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Page|Knight|Queen|King) of .+):\s*$")


def parse_symbols(lines):
    heads = [(i, l) for i, l in enumerate(lines) if HDR.match(l)]
    out = {}
    for k, (i, l) in enumerate(heads):
        j = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        title = re.sub(r"^\d+\.\s*", "", l.rstrip(":")).strip()
        cid = NAME_TO_ID.get(norm(title))
        if cid is None:
            raise SystemExit(f"Cabecera sin correspondencia: {title!r}")
        body = [x.strip() for x in lines[i + 1:j] if x.strip()]
        entry = {"intro": "", "symbols": [], "aspects": [], "closing": ""}
        mode = "intro"
        for x in body:
            if x == "Symbolism:":
                mode = "sym"
            elif x == "Representation in Readings:":
                mode = "asp"
            elif mode == "intro":
                entry["intro"] += (" " if entry["intro"] else "") + x
            elif mode in ("sym", "asp"):
                m = re.match(r"^([^:]{2,70}):\s+(.+)$", x)
                if m and not x.startswith("In readings"):
                    entry["symbols" if mode == "sym" else "aspects"].append({"name": m.group(1), "text": m.group(2)})
                else:
                    entry["closing"] += (" " if entry["closing"] else "") + x
                    mode = "end"
            else:
                entry["closing"] += " " + x
        out[cid] = entry
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zaiphira", default=str(ICLOUD / "Tarot_simb-cartas.rtf"))
    ap.add_argument("--symbols", default=str(ICLOUD / "SymboloftheCards.rtf"))
    a = ap.parse_args()
    z = parse_zaiphira(rtf_to_text(Path(a.zaiphira)))
    s = parse_symbols(rtf_to_text(Path(a.symbols)))
    kb = {}
    for c in CARDS:
        cid = c["id"]
        e = {**z.get(cid, {}), **s.get(cid, {})}
        kb[str(cid)] = e
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(kb, ensure_ascii=False, indent=1))
    print(f"ZAIPHIRA: {len(z)}/78 cartas con palabras clave ES/EN")
    print(f"Simbología: {len(s)}/78 cartas; con símbolos nombrados: {sum(1 for v in s.values() if v['symbols'])}; "
          f"con aspectos de lectura: {sum(1 for v in s.values() if v['aspects'])}")
    print("->", OUT)


if __name__ == "__main__":
    sys.exit(main())
