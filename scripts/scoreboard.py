"""Hits per model, mean Whisper confidence, and the clip each model plays in the video.

usage: python scripts/scoreboard.py [word]

Each model's clip is the try Whisper was surest about. The featured model is the one with the most
hits, ties broken by mean confidence. Writes results/<word>/scoreboard.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run import MODELS, name

word = sys.argv[1] if len(sys.argv) > 1 else "hello"
out = ROOT / "results" / word
rows = json.loads((out / "heard.json").read_text(encoding="utf8"))

board = []
for model in MODELS:
    tries = [r for r in rows if r["model"] == model]
    if not tries:
        continue
    pick = max(tries, key=lambda r: (r["hit"], r["confidence"]))
    board.append({"model": model, "hits": sum(r["hit"] for r in tries), "tries": len(tries),
                  "confidence": round(sum(r["confidence"] for r in tries) / len(tries), 3),
                  "clip": name(model, pick["try"]), "heard": pick["heard"]})
featured = max(board, key=lambda b: (b["hits"], b["confidence"]))

print(f"| Model | Heard as {word} | Mean confidence | Clip in the video |")
print("|---|---:|---:|---|")
for b in board:
    print(f"| {b['model']} | {b['hits']} of {b['tries']} | {b['confidence']:.2f} | \"{b['heard']}\" |")
print(f"\nfeatured: {featured['model']} ({featured['clip']})")
(out / "scoreboard.json").write_text(json.dumps({"featured": featured["model"], "models": board}, indent=1),
                                     encoding="utf8")
