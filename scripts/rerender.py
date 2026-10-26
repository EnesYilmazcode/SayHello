"""Rebuild every frames file and wav from the saved raw replies, with no API calls.

usage: python scripts/rerender.py [word]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import render

word = sys.argv[1] if len(sys.argv) > 1 else "hello"
out = ROOT / "results" / word
for reply in sorted(out.glob("*.txt")):
    print(reply.stem, render(reply.read_text(encoding="utf8"), out, reply.stem))
