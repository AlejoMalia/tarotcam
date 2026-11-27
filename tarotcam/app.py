#!/usr/bin/env python3
"""TarotCam: detects every tarot card in front of the camera, tells which one it is and builds the reading.

Usage (from this folder):
  python -m tarotcam --camera 0                                      # webcam (OpenCV index)
  python -m tarotcam                                                 # PlayStation Eye (needs ../vendor/PS3EyeFullHD)
  python -m tarotcam --image photo.jpg --save out.png                # a single picture, no camera
  python -m tarotcam --lang es                                       # Spanish (default: English)
  python -m tarotcam --spread celtic                                 # force a spread (default: auto)

  python -m tarotcam --focus love                                   # read through an area of life
  python -m tarotcam --setup-chart                                  # add your natal chart (stays local)
  python -m tarotcam --writer local                                 # prose by a local model (Ollama, LM Studio)

  python -m tarotcam --deck marseille                                   # Tarot de Marseille

Keys: t deck (Rider-Waite-Smith / Marseille) · q quit · r reset the table · s save screenshot · d story / analysis · f focus · l English / Español
      n natal chart on/off · a local model on/off (only with --writer local)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import types
from pathlib import Path

# captura opcional con PlayStation Eye: repo hermano ../vendor/PS3EyeFullHD
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "PS3EyeFullHD"))


def _stub_tkinter():
    """pseyepy importa tkinter solo para su ventana de depuración; aquí no se usa."""
    try:
        import tkinter  # noqa: F401
        return
    except ImportError:
        pass

    def ga(name):
        class _Any:
            def __init__(self, *a, **k):
                pass
        return _Any
    for m in ("tkinter", "tkinter.ttk"):
        mod = types.ModuleType(m)
        mod.__getattr__ = ga
        sys.modules[m] = mod


import cv2  # noqa: E402

from tarotcam import i18n  # noqa: E402
from tarotcam.engine import llm  # noqa: E402
from tarotcam.engine import narrator  # noqa: E402
from tarotcam.astro import natal  # noqa: E402
from tarotcam.i18n import L  # noqa: E402
from tarotcam.carddata import cards, decks  # noqa: E402
from tarotcam.carddata.cards import BY_ID  # noqa: E402
from tarotcam.vision.recognizer import Deck, GlobalScanner  # noqa: E402
from tarotcam.engine.spreads import analyze  # noqa: E402
from tarotcam.vision.tracker import Table  # noqa: E402
from tarotcam.interface.ui import render  # noqa: E402


WINDOW = "TarotCam"                      # el título de la ventana no cambia al alternar idioma


def frames_ps3eye(fps):
    _stub_tkinter()
    from ps3eye_hd.capture import PS3Eye
    cam = PS3Eye(fps=fps)
    try:
        while True:
            rgb, _ = cam.read_rgb()
            yield cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    finally:
        cam.close()


def frames_cv(index):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        sys.exit(L(f"Could not open camera {index}.", f"No se pudo abrir la cámara {index}."))
    try:
        while True:
            ok, f = cap.read()
            if not ok:
                return
            yield f
    finally:
        cap.release()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", type=int, help="OpenCV camera index (default: PlayStation Eye)")
    ap.add_argument("--image", help="analyse a picture instead of the camera")
    ap.add_argument("--save", help="with --image: save the result to this PNG")
    ap.add_argument("--spread", choices=["auto", "entry", "line", "rows", "cross", "celtic", "horseshoe"],
                    default="auto", help="spread: auto detects it from the position of the cards")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--detail", "--detalle", dest="detail", action="store_true",
                    help="start with the section-by-section analysis (key d toggles it)")
    ap.add_argument("--focus", choices=narrator.FOCI, default="general", help="area of life (key f cycles it)")
    ap.add_argument("--setup-chart", action="store_true", help="enter your birth data (kept on this computer)")
    ap.add_argument("--no-chart", action="store_true", help="ignore the saved natal chart")
    ap.add_argument("--deck", choices=decks.SYSTEMS, default="rws", help="deck on the table (key t switches it)")
    ap.add_argument("--writer", choices=["rules", "local"], default="rules",
                    help="who writes the story: built-in rules or a local language model")
    ap.add_argument("--model", default=llm.DEFAULT_MODEL, help="local model name")
    ap.add_argument("--llm-url", default=llm.DEFAULT_URL, help="local OpenAI-compatible endpoint")
    ap.add_argument("--lang", choices=i18n.LANGS, default="en", help="interface language (key l toggles it)")
    a = ap.parse_args()

    i18n.set_lang(a.lang)
    if a.setup_chart:
        natal.setup()
    print(L("Loading the deck…", "Cargando baraja…"))
    scanners = {}

    def scanner_for(system):
        if system not in scanners:
            folders = decks.folders(system)
            if not folders:
                return None
            scanners[system] = GlobalScanner(Deck(folders))
        return scanners[system]

    cards.set_system(a.deck)
    scanner = scanner_for(a.deck)
    if scanner is None:
        sys.exit(L(f"Deck images missing. Run: python -m tarotcam.tools.download_deck --deck {a.deck}",
                   f"Faltan las imágenes. Ejecuta: python -m tarotcam.tools.download_deck --deck {a.deck}"))
    table = Table(scanner, spread_mode=a.spread, threaded=not a.image)
    table.detail = a.detail
    table.focus = a.focus
    table.chart = None if a.no_chart else natal.load()
    table.use_chart = table.chart is not None
    if table.chart:
        print(L(f"Natal chart loaded: {table.chart.name} (key n toggles it).",
                f"Carta astral cargada: {table.chart.name} (la tecla n la activa o desactiva)."))
    if a.writer == "local":
        writer = llm.LocalWriter(a.llm_url, a.model)
        if writer.available():
            table.writer, table.use_writer = writer, True
        else:
            print(L(f"Local model '{a.model}' not reachable at {a.llm_url}; using the built-in writer.",
                    f"El modelo local '{a.model}' no responde en {a.llm_url}; se usa el redactor propio."))

    if a.image:
        frame = cv2.imread(a.image)
        if frame is None:
            sys.exit(L(f"Could not read {a.image}", f"No se pudo leer {a.image}"))
        for _ in range(3):                       # varios pases para confirmar
            table.update(frame)
        if table.use_writer:                     # foto fija: esperar al modelo antes de pintar
            layout = analyze(table.spread(), table.spread_mode)
            table.writer.settle = 0
            deadline = time.time() + table.writer.timeout
            while table.writer.request(layout, table.focus, table.chart if table.use_chart else None) is None and time.time() < deadline:
                if "failed" in table.writer.status:
                    break
                time.sleep(0.3)
        out = render(frame, table, L("still image", "imagen estática"))
        if a.save:
            cv2.imwrite(a.save, out)
            print(L("Saved", "Guardado"), a.save)
        else:
            cv2.imshow(WINDOW, out)
            cv2.waitKey(0)
        for t in table.spread():
            print(i18n.card_name(BY_ID[t.card_id]), "-",
                  L("reversed", "al revés") if t.reversed else L("upright", "al derecho"))
        return

    src = frames_cv(a.camera) if a.camera is not None else frames_ps3eye(a.fps)
    t0, n, fps = time.time(), 0, 0.0
    for frame in src:
        table.update(frame)
        n += 1
        if time.time() - t0 >= 1:
            fps, n, t0 = n / (time.time() - t0), 0, time.time()
        status = L(f"{fps:.0f} fps · scan {table.scan_ms:.0f} ms · q quit · r reset · s screenshot",
                   f"{fps:.0f} fps · escaneo {table.scan_ms:.0f} ms · q salir · r reiniciar · s captura")
        cv2.imshow(WINDOW, render(frame, table, status))
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord("r"):
            table.reset()
        if k == ord("d"):
            table.detail = not table.detail
        if k == ord("l"):
            i18n.toggle()
        if k == ord("f"):
            table.focus = narrator.FOCI[(narrator.FOCI.index(table.focus) + 1) % len(narrator.FOCI)]
        if k == ord("n") and table.chart:
            table.use_chart = not table.use_chart
        if k == ord("t"):
            other = decks.SYSTEMS[(decks.SYSTEMS.index(cards.system()) + 1) % len(decks.SYSTEMS)]
            new = scanner_for(other)
            if new is None:
                print(L(f"Deck images missing for {other}.", f"Faltan las imágenes de {other}."))
            else:
                cards.set_system(other)
                table.close()
                old = table
                table = Table(new, spread_mode=old.spread_mode, threaded=True)
                for attr in ("detail", "focus", "writer", "use_writer", "chart", "use_chart"):
                    setattr(table, attr, getattr(old, attr))
        if k == ord("a") and table.writer:
            table.use_writer = not table.use_writer
        if k == ord("s"):
            cv2.imwrite(f"capture_{int(time.time())}.png", render(frame, table))
    table.close()
    cv2.destroyAllWindows()
    # pseyepy/libusb abortan con un assert al liberar la cámara en macOS (inocuo).
    # Se sale sin pasar por ese cierre; el SO libera el USB.
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
