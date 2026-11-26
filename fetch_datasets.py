#!/usr/bin/env python3
"""Download three open tarot datasets into datasets/ (git-ignored), pinned to the reviewed commits.

  Tarotoo-com/tarotoo-tarot-dataset   MIT        keywords, love / career / spiritual / mood, yes-no
  smallcat419/tarot-card-data         CC0 (as stated in its README)   love / career / finance sentences
  StarTarotOnline/tarot-rws-dataset   CC BY 4.0  Waite (1911) meanings, Golden Dawn titles and attributions
"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent / "datasets"
SOURCES = {
    "tarotoo": ("Tarotoo-com/tarotoo-tarot-dataset", "83202267973950eb5bf034f144b9405db9cb1e7e",
                {"cards.json": "data/cards.json", "LICENSE": "LICENSE"}),
    "smallcat": ("smallcat419/tarot-card-data", "b40718b33ea9de3a89dc65fc0e2c9a9a605e409e",
                 {"cards.json": "index.json", "README.md": "README.md"}),
    "startarot": ("StarTarotOnline/tarot-rws-dataset", "7f8ab42b62eef5d018536b8775010e3d6e61eb27",
                  {"cards.jsonl": "data/cards.jsonl", "LICENSE": "data/LICENSE"}),
}


def main():
    for name, (repo, sha, files) in SOURCES.items():
        folder = ROOT / name
        folder.mkdir(parents=True, exist_ok=True)
        for local, remote in files.items():
            url = f"https://raw.githubusercontent.com/{repo}/{sha}/{remote}"
            req = urllib.request.Request(url, headers={"User-Agent": "tarotcam/0.1"})
            data = urllib.request.urlopen(req, timeout=30).read()
            (folder / local).write_bytes(data)
            print(f"ok  {name}/{local}  ({len(data) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
