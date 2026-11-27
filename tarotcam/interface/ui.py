"""Interfaz minimalista (inglés / español): vídeo con marcos de color por palo, fichas de cartas y lectura global.

Color del marco según la carta:
  Arcano mayor blanco · Oros amarillo yema · Espadas celeste · Bastos verde · Copas rojo
Lectura: narración continua (por defecto) o análisis por secciones (tecla d). Enfoque con la tecla f.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tarotcam import paths
from tarotcam.carddata.cards import BY_ID
from tarotcam.engine import narrator
from tarotcam.i18n import L, plural
from tarotcam.engine.reading import compose, headline_key
from tarotcam.engine.spreads import analyze

DECK_DIR = paths.RWS_DECK
CANVAS_W, CANVAS_H = 1280, 900
VID_W, VID_H = 640, 480
PAD = 36                                          # margen general

# --- paleta sobria -------------------------------------------------------------------------
BG, FG, MUTED, FAINT, LINE = (18, 18, 22), (236, 234, 228), (140, 140, 150), (84, 84, 94), (44, 44, 52)
ACCENT = (226, 186, 96)

# --- color del marco por tipo de carta (RGB) -----------------------------------------------
SUIT_COLOR = {
    None: (255, 255, 255),          # arcano mayor: blanco
    "Oros": (245, 197, 24),         # amarillo yema
    "Espadas": (135, 206, 250),     # celeste
    "Bastos": (76, 201, 100),       # verde
    "Copas": (230, 57, 70),         # rojo
}
REVERSED = (232, 110, 110)


def card_color(card_id: int):
    return SUIT_COLOR[BY_ID[card_id]["suit"]]


_FONT_PATHS = ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf",
               "/Library/Fonts/Arial.ttf"]
_fonts: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False):
    key = (size, bold)
    if key not in _fonts:
        for p in _FONT_PATHS:
            try:
                _fonts[key] = ImageFont.truetype(p, size, index=1 if bold and p.endswith(".ttc") else 0)
                break
            except OSError:
                continue
        else:
            _fonts[key] = ImageFont.load_default()
    return _fonts[key]


_thumb_cache: dict[tuple[int, bool, int], Image.Image] = {}


def _thumb(card_id, reversed_, h):
    key = (card_id, reversed_, h)
    if key not in _thumb_cache:
        im = Image.open(DECK_DIR / f"{card_id:02d}.jpg").convert("RGB")
        im = im.resize((max(1, int(im.width * h / im.height)), h))
        _thumb_cache[key] = im.rotate(180) if reversed_ else im
    return _thumb_cache[key]


def _wrap(draw, text, fnt, width):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def _fit(d, text, fnt, room):
    if d.textlength(text, font=fnt) <= room:
        return text
    while text and d.textlength(text + "…", font=fnt) > room:
        text = text[:-1]
    return text.rstrip() + "…"


def _clip_lines(lines, max_lines):
    if len(lines) <= max_lines:
        return lines
    out = lines[:max_lines]
    out[-1] = out[-1].rstrip(" .,;") + "…"
    return out


# ------------------------------------------------------------------ panel de cartas (derecha)
_HEBREW_PATHS = ["/System/Library/Fonts/SFHebrew.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                 "/Library/Fonts/Arial Unicode.ttf"]
_hfonts: dict[int, ImageFont.FreeTypeFont] = {}


def hebrew_font(size: int):
    if size not in _hfonts:
        for p in _HEBREW_PATHS:
            try:
                _hfonts[size] = ImageFont.truetype(p, size)
                break
            except OSError:
                continue
        else:
            _hfonts[size] = font(size)
    return _hfonts[size]


def _text_glyph(d, x, y, text, glyph, size, fill, room):
    """Texto + glifo hebreo con su propia fuente. Devuelve la x final."""
    f = font(size)
    text = _fit(d, text, f, max(room - (size + 8 if glyph else 0), 20))
    d.text((x, y), text, font=f, fill=fill)
    if glyph:
        x2 = x + d.textlength(text, font=f) + 6
        d.text((x2, y - 1), glyph, font=hebrew_font(size + 1), fill=fill)
        return x2 + size
    return x + d.textlength(text, font=f)


def _grid(n):
    return (1 if n <= 3 else 2 if n <= 6 else 3 if n <= 12 else 4)


def _level(n):
    """Cuánta información lleva cada ficha según cuántas cartas haya (minimalismo con muchas cartas)."""
    return "full" if n <= 2 else "medium" if n <= 6 else "small" if n <= 12 else "none"


def _draw_cards(d, canvas, items, layout_name):
    x0, w = VID_W + PAD, CANVAS_W - VID_W - 2 * PAD
    d.text((x0, 30), _fit(d, layout_name or L("Empty table", "Mesa vacía"), font(24), w), font=font(24), fill=FG)
    d.text((x0, 62), L(plural(len(items), "card", "cards"), plural(len(items), "carta", "cartas")) if items
           else L("Place a card", "Coloca una carta"),
           font=font(14), fill=MUTED)
    if not items:
        return
    y0, h = 104, VID_H - 104 - 20
    n = len(items)
    cols = _grid(n)
    rows = -(-n // cols)
    gap = 16
    tw = (w - gap * (cols - 1)) // cols
    th = min(220 if n == 1 else 180, (h - gap * (rows - 1)) // rows)
    ph = th - 4
    lvl = _level(n)
    for i, it in enumerate(items):
        cx, cy = x0 + (i % cols) * (tw + gap), y0 + (i // cols) * (th + gap)
        im = _thumb(it["id"], it["reversed"], ph)
        d.rectangle([cx - 2, cy - 2, cx + im.width + 1, cy + im.height + 1], outline=card_color(it["id"]), width=2)
        canvas.paste(im, (cx, cy))
        tx = cx + im.width + 16
        room = tw - (tx - cx)
        corr = it["corr"]
        role = it["pos"].split(" · ")[-1] if it["pos"][:1].isdigit() else it["pos"]
        d.text((tx, cy), _fit(d, role.upper(), font(11), room), font=font(11), fill=MUTED)
        name_f = font(20 if tw >= 340 else 16 if tw >= 260 else 14, True)
        yy = cy + 18
        for sub in _clip_lines(_wrap(d, it["name"], name_f, room), 2):
            d.text((tx, yy), sub, font=name_f, fill=FG)
            yy += name_f.size + 4
        if it["reversed"]:
            d.text((tx, yy), L("reversed", "al revés"), font=font(13), fill=REVERSED)
            yy += 20
        if n <= 2:                                      # el significado, solo con 1-2 cartas (si no, no cabe)
            yy += 4
            mline = _clip_lines(_wrap(d, it["meaning"], font(14), room), 2)
            for sub in mline:
                d.text((tx, yy), sub, font=font(14), fill=MUTED)
                yy += 20
        yy += 6
        if lvl == "full":                               # número, elemento, astrología y extra, con etiqueta
            rows_ = [(L("NUMBER", "NÚMERO"), corr["numero"], ""), (L("ELEMENT", "ELEMENTO"), corr["elemento"], ""),
                     (L("ASTROLOGY", "ASTROLOGÍA"), corr["astro"], ""),
                     (corr["extra_label"].upper(), corr["extra"], corr["glyph"])]
            for lab, val, glyph in rows_:
                d.text((tx, yy + 2), lab, font=font(10), fill=FAINT)
                _text_glyph(d, tx + 108, yy, val, glyph, 14, FG, room - 108)
                yy += 21
        elif lvl in ("medium", "small"):                # una o dos líneas compactas
            line1 = f"{corr['numero']} · {corr['elemento']} · {corr['short_astro']}"
            if lvl == "medium":
                line1 = f"{corr['numero'].split(' · ')[0]} · {corr['elemento']}"
                d.text((tx, yy), _fit(d, line1, font(13), room), font=font(13), fill=FG)
                yy += 19
                d.text((tx, yy), _fit(d, corr["short_astro"], font(13), room), font=font(13), fill=MUTED)
                yy += 19
                if corr["short_extra"] not in (corr["elemento"],):
                    _text_glyph(d, tx, yy, corr["short_extra"], corr["glyph"], 13, MUTED, room)
            else:
                d.text((tx, yy), _fit(d, f"{corr['numero'].split(' · ')[0]} · {corr['elemento']}", font(12), room),
                       font=font(12), fill=MUTED)
                d.text((tx, yy + 15), _fit(d, corr["short_astro"], font(12), room), font=font(12), fill=FAINT)


# ------------------------------------------------------------------ lectura (abajo)
def _draw_reading(d, secs, detail, story):
    """Abajo: la narración (por defecto) o el análisis por secciones (tecla d)."""
    top = VID_H + 28
    d.line([(PAD, top - 12), (CANVAS_W - PAD, top - 12)], fill=LINE, width=1)
    head = next((t for ti, t in secs if ti == headline_key()), "")
    if not head:                                       # mesa vacía: un único mensaje
        d.text((PAD, top + 6), story[0] if story else "", font=font(18), fill=MUTED)
        return
    d.text((PAD, top), _fit(d, head, font(22), CANVAS_W - 2 * PAD), font=font(22), fill=FG)
    y, bottom = top + 50, CANVAS_H - 44
    if detail:                                          # todas las secciones, en 3 o 4 columnas
        cols, size, placed = analysis_layout(d, [(ti, t) for ti, t in secs if ti != headline_key()], y, bottom)
    else:                                               # prosa continua, en 2 columnas
        cols = 2
        size, placed = detail_layout(d, [("", p) for p in story], y, bottom, cols, (18, 9))
    cw = _col_width(cols)
    for col, yy, text, is_title in placed:
        x = PAD + col * (cw + DETAIL_GAP)
        d.text((x, yy), text, font=font(11) if is_title else font(size), fill=ACCENT if is_title else FG)


DETAIL_COLS, DETAIL_GAP = 3, 36


def _col_width(cols):
    return (CANVAS_W - 2 * PAD - DETAIL_GAP * (cols - 1)) // cols


def analysis_layout(d, body, top, bottom):
    """3 columnas; si no cabe todo, 4. -> (columnas, tamaño, colocación)."""
    for cols, sizes in ((DETAIL_COLS, (15, 9)), (DETAIL_COLS + 1, (11, 8))):
        size, placed = detail_layout(d, body, top, bottom, cols, sizes)
        if not _truncated(body, placed):
            break
    return cols, size, placed


def _truncated(body, placed) -> bool:
    titled = sum(1 for t, _ in body if t)
    return sum(1 for p in placed if p[3]) < titled or (bool(placed) and placed[-1][2].endswith("…"))


def detail_layout(d, body, top, bottom, cols=DETAIL_COLS, sizes=(15, 9)):
    """body = [(título o "", texto)] fluyendo línea a línea por columnas, con la fuente mayor que quepa.
    -> (tamaño, [(columna, y, texto, es_título)]). Si ni con la mínima cabe, la última línea acaba en '…'."""
    cw = _col_width(cols)
    for size in range(sizes[0], sizes[1] - 1, -1):
        lh = size + (5 if size < 14 else 8)
        placed, col, y, fits = [], 0, top, True
        for title, text in body:
            lines = _wrap(d, text, font(size), cw)
            if title:
                if y + 18 + lh > bottom:                # el título no se separa de su primera línea
                    col, y = col + 1, top
                if col >= cols:
                    fits = False
                    break
                placed.append((col, y, title.upper(), True))
                y += 18
            for line in lines:
                if y + lh > bottom:
                    col, y = col + 1, top
                if col >= cols:
                    fits = False
                    break
                placed.append((col, y, line, False))
                y += lh
            if not fits:
                break
            y += 12
        if fits:
            return size, placed
    if placed and not placed[-1][3]:
        c, y_, line, t = placed[-1]
        placed[-1] = (c, y_, line.rstrip(" .,;") + "…", t)
    return size, placed


# ------------------------------------------------------------------ render
def render(frame_bgr: np.ndarray, table, status: str = "") -> np.ndarray:
    layout = analyze(table.spread(), getattr(table, "spread_mode", "auto"))
    detail = bool(getattr(table, "detail", False))
    spread = [s.track for s in layout.slots]               # en orden de lectura
    chart = getattr(table, "chart", None) if getattr(table, "use_chart", False) else None
    items, secs = compose(layout, chart)
    focus = getattr(table, "focus", "general")
    writer = getattr(table, "writer", None) if getattr(table, "use_writer", False) else None
    story = (writer.request(layout, focus, chart) if writer else None) or narrator.compose(layout, focus, chart)
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    d = ImageDraw.Draw(canvas)

    vid = Image.fromarray(cv2.cvtColor(cv2.resize(frame_bgr, (VID_W, VID_H)), cv2.COLOR_BGR2RGB))
    vd = ImageDraw.Draw(vid)                           # se dibuja sobre el vídeo: nada se sale del recuadro
    sx, sy = VID_W / frame_bgr.shape[1], VID_H / frame_bgr.shape[0]
    quads = [[(float(x * sx), float(y * sy)) for x, y in t.quad] for t in spread]
    for t, pts in zip(spread, quads):
        vd.line(pts + [pts[0]], fill=card_color(t.card_id), width=3)
    placed_labels: list[tuple[float, float, float, float]] = []
    for i, (t, pts) in enumerate(zip(spread, quads)):    # etiquetas encima de todos los marcos
        col = card_color(t.card_id)
        label = f"{i + 1}  {items[i]['name']}" if len(spread) <= 6 else f"{i + 1}"
        if t.visible < 0.7:                              # carta vista solo en parte
            label += f"  ~{max(5, 5 * round(t.visible * 20))}%"
        w = d.textlength(label, font=font(13))
        x = min(max(min(p[0] for p in pts), 4), VID_W - 14 - w)
        y = min(max(min(p[1] for p in pts) - 24, 4), VID_H - 24)
        for _ in range(12):                              # si pisa otra etiqueta, bajarla una línea
            if not any(x - 6 < bx2 and x + w + 6 > bx1 and y - 2 < by2 and y + 18 > by1
                       for bx1, by1, bx2, by2 in placed_labels):
                break
            y = y + 23 if y + 47 < VID_H else y - 23
        placed_labels.append((x - 6, y - 2, x + w + 6, y + 18))
        vd.rounded_rectangle([x - 6, y - 2, x + w + 6, y + 18], radius=4, fill=BG)
        vd.text((x, y), label, font=font(13), fill=col)
    canvas.paste(vid, (0, 0))

    _draw_cards(d, canvas, items, layout.name)
    _draw_reading(d, secs, detail, story)
    name = L(*narrator.FOCUS_NAME[focus])
    hint = L(f"d  {'story' if detail else 'analysis'}    f  focus: {name}    l  español",
             f"d  {'narración' if detail else 'análisis'}    f  enfoque: {name}    l  English")
    if getattr(table, "chart", None):
        hint += L(f"    n  chart: {'on' if chart else 'off'}", f"    n  carta astral: {'sí' if chart else 'no'}")
    if writer:
        hint += f"    ·    {writer.status}"
    elif getattr(table, "writer", None):
        hint += L("    a  local model", "    a  modelo local")
    d.text((PAD, CANVAS_H - 30), f"{status}    {hint}".strip(), font=font(12), fill=FAINT)
    return cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
