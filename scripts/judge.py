"""Let Whisper hear every clip for a word and write the scoreboard.

usage: python scripts/judge.py [word]

Writes results/<word>/heard.json: what Whisper wrote down for every try, its confidence, and
whether the word is in it. A try counts as a hit when the word appears, punctuation aside.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from run import MODELS, name
from sayhello import synth
from sayhello.hear import hear


def hit(word, text):
    return word.lower() in re.findall(r"[a-z']+", text.lower())


def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "hello"
    out = ROOT / "results" / word
    rows = []
    for model in MODELS:
        for i in range(3):
            wav = out / f"{name(model, i)}.wav"
            if not wav.exists():
                continue
            text, confidence = hear(synth.load_wav(wav))
            rows.append({"model": model, "try": i, "heard": text, "confidence": round(confidence, 3),
                         "hit": hit(word, text)})
            print(f"{model:28} {i}  {'HIT ' if rows[-1]['hit'] else 'miss'}  {confidence:.2f}  {text}")
    (out / "heard.json").write_text(json.dumps(rows, indent=1), encoding="utf8")


if __name__ == "__main__":
    main()
