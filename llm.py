"""Optional prose writer backed by a LOCAL language model with an OpenAI-compatible API (Ollama, LM Studio,
llama.cpp server). Off by default. Only loopback addresses are accepted, so the reading never leaves the machine.

The model only rewrites facts produced by the engine. While it thinks (or if it fails) the rule-based narrative
is shown, so the app never blocks.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from urllib.parse import urlparse

import chartlink
import datasets
import i18n
import narrator
import reading

DEFAULT_URL = "http://127.0.0.1:11434/v1"          # Ollama
DEFAULT_MODEL = "qwen2.5:3b"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
SETTLE = 2.0                                       # segundos sin cambios en la mesa antes de pedir texto


def facts(layout, focus: str, chart=None) -> str:
    lines = [f"Spread: {layout.name}. Focus: {focus}."]
    for c in reading._states(layout):
        cid = c.card["id"]
        line = f"- {c.role}: {c.name}{' (reversed)' if c.reversed else ''}. Keywords: {c.kw(5)}."
        if focus != "general" and datasets.area_text(cid, focus, c.reversed):
            line += f" For {focus}: {datasets.area_text(cid, focus, c.reversed)}"
        if datasets.golden_dawn_title(cid):
            line += f" Golden Dawn title: {datasets.golden_dawn_title(cid)}."
        lines.append(line)
    if chart is not None:
        cs = reading._states(layout)
        lines.append(f"Client: {chart.name}. Natal chart: {chartlink.summary(chart)}.")
        lines += [f"- {text}" for _, _, text in chartlink.resonances(chart, cs, 5)]
    lines.append("Analysis draft:")
    lines += narrator.compose(layout, focus, chart)
    return "\n".join(lines)


def messages(layout, focus: str, chart=None) -> list[dict]:
    language = "Spanish (from Spain)" if i18n.lang() == "es" else "English"
    system = (
        "You are a professional tarot reader writing for a client. Write the complete reading in " + language + ". "
        "Use 3 or 4 flowing paragraphs of natural prose: no headings, no lists, no markdown. "
        "Use ONLY the cards, positions and meanings given; never invent other cards. Name every card at least once. "
        "Do not repeat phrases or restate the same idea. Connect the cards into one story. "
        "Present it as reflection, not as certain prediction, and give no medical, legal or financial instructions."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": facts(layout, focus, chart)}]


def clean(text: str) -> list[str]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"[*_#`>]+", "", text)
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]


class LocalWriter:
    def __init__(self, url: str = DEFAULT_URL, model: str = DEFAULT_MODEL, timeout: float = 120, settle: float = SETTLE):
        if urlparse(url).hostname not in LOOPBACK:
            raise ValueError("Only a local model server is allowed (127.0.0.1 / localhost).")
        self.url, self.model, self.timeout, self.settle = url.rstrip("/"), model, timeout, settle
        self.status = ""
        self._cache: dict[str, list[str]] = {}
        self._failed: set[str] = set()
        self._pending: tuple[str, float] = ("", 0.0)
        self._busy = False

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.url + "/models", timeout=1.5) as r:
                data = json.load(r)
            return any(self.model == m.get("id") for m in data.get("data", []))
        except (OSError, ValueError):
            return False

    def generate(self, msgs: list[dict]) -> list[str]:
        body = json.dumps({"model": self.model, "messages": msgs, "temperature": 0.7, "max_tokens": 900,
                           "stream": False}).encode()
        req = urllib.request.Request(self.url + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.load(r)
        return clean(data["choices"][0]["message"]["content"])

    def request(self, layout, focus: str, chart=None) -> list[str] | None:
        """No bloquea. Devuelve el texto del modelo si ya existe para esta mesa; si no, None."""
        if not layout.slots:
            return None
        key = "|".join([i18n.lang(), focus, layout.kind, f"{chart.name}{chart.local}" if chart else ""]
                       + [f"{s.track.card_id}{int(s.track.reversed)}{s.key}" for s in layout.slots])
        if key in self._cache:
            self.status = "local model"
            return self._cache[key]
        if key in self._failed:
            self.status = "local model failed, using rules"
            return None
        if self._pending[0] != key:
            self._pending = (key, time.time())
        elif not self._busy and time.time() - self._pending[1] >= self.settle:
            self._busy = True
            msgs = messages(layout, focus, chart)      # se construye en el hilo principal (idioma estable)
            threading.Thread(target=self._work, args=(key, msgs), daemon=True).start()
        self.status = "local model writing…" if self._busy else "waiting for the table to settle"
        return None

    def _work(self, key: str, msgs: list[dict]) -> None:
        try:
            out = self.generate(msgs)
            if out:
                self._cache[key] = out
            else:
                self._failed.add(key)
        except (OSError, ValueError, KeyError, IndexError):
            self._failed.add(key)
        finally:
            self._busy = False
