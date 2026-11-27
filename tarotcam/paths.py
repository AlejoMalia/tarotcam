"""Where local, unversioned data lives (everything under data/ is git-ignored)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DECKS = DATA / "decks"
RWS_DECK = DECKS / "rws"
DATASETS = DATA / "datasets"
KNOWLEDGE_FILE = DATA / "knowledge" / "kb.json"
