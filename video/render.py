"""Render the showcase video with PIL at 2x and encode it with ffmpeg.

usage: python video/render.py [word] [out.mp4] [fps]

All ten cards sit in one grid the whole time. The best model plays first, then the rest in a fixed
shuffled order, so hits and misses are mixed. Each card types out what Whisper heard while its
clip plays, and a stamp comes down on the bars when it ends. The first frame is the finished grid,
which dissolves into the start, because X uses the first frame as the thumbnail.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cards import BG, bars, draw_card
from sayhello import synth
from sound import mix, write_wav

W, H, S = 1800, 1200, 2
COLS, CARD_W, CARD_H, GAP = 5, 312, 505, 30
MAX_PLAY = 1.6                    # seconds of a clip that play; longer ones fade out
LEAD_HOLD, LEAD_FADE, END_HOLD = 0.85, 0.45, 1.5
FIRST = 0.4                       # seconds of the empty grid before the first voice
STAMP = 0.08                      # seconds from the end of a clip to its stamp
GAPS = (0.45, 0.2)                # pause after each stamp, first to last
SEED = 9                          # fixes the shuffle; no more than two hits or misses in a row


def ease(t):
    t = float(np.clip(t, 0, 1))
    return t * t * (3 - 2 * t)


def slot(i):
    left = (W - COLS * CARD_W - (COLS - 1) * GAP) / 2
    top = (H - 2 * CARD_H - GAP) / 2
    return (left + (i % COLS) * (CARD_W + GAP), top + (i // COLS) * (CARD_H + GAP), CARD_W, CARD_H)


def load(word):
    """Cards in play order, which is also grid order: the featured model, then the rest shuffled."""
    out = ROOT / "results" / word
    board = json.loads((out / "scoreboard.json").read_text(encoding="utf8"))
    cards = []
    for m in board["models"]:
        audio = synth.load_wav(out / f"{m['clip']}.wav")
        play = min(len(audio) / synth.SR, MAX_PLAY)
        cards.append({"model": m["model"], "audio": audio, "play": play, "hit": m["hits"] > 0,
                      "heard": m["heard"], "levels": bars(audio[:int(play * synth.SR)])})
    featured = [c for c in cards if c["model"] == board["featured"]]
    rest = [c for c in cards if c["model"] != board["featured"]]
    random.Random(SEED).shuffle(rest)
    return featured + rest


def timeline(cards):
    """When each card's voice starts and when its stamp lands, in story seconds."""
    t = FIRST
    for k, c in enumerate(cards):
        c["start"] = t
        c["mark"] = t + c["play"] + STAMP
        t = c["mark"] + 0.3 + GAPS[0] + (GAPS[1] - GAPS[0]) * k / max(1, len(cards) - 1)
    return t + END_HOLD


def frame(t, cards):
    canvas = Image.new("RGBA", (W * S, H * S), BG)
    for i, c in enumerate(cards):
        played = float(np.clip((t - c["start"]) / c["play"], 0, 1))
        mark = float(np.clip((t - c["mark"]) / 0.35, 0, 1))
        active = ease((t - c["start"] + 0.15) / 0.15) - ease((t - c["mark"] - 0.2) / 0.3)
        draw_card(canvas, tuple(v * S for v in slot(i)), c["model"], c["levels"], played,
                  c["hit"] if mark > 0 else None, mark, c["heard"], active)
    return canvas.convert("RGB").resize((W, H), Image.LANCZOS)


def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "hello"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "renders" / f"{word}.mp4"
    fps = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    out.parent.mkdir(parents=True, exist_ok=True)

    cards = load(word)
    story = timeline(cards)
    lead = LEAD_HOLD + LEAD_FADE
    total = lead + story
    print("order:", ", ".join(f"{c['model']} ({'hit' if c['hit'] else 'miss'})" for c in cards))

    events, hits = [], 0
    for c in cards:
        events.append((lead + c["start"], "voice", (c["audio"], synth.SR, c["play"])))
        events.append((lead + c["mark"], "hit" if c["hit"] else "miss", hits))
        hits += c["hit"]
    wav = out.with_suffix(".wav")
    write_wav(wav, mix(events, total))

    finish = frame(story, cards)
    opening = frame(0, cards)
    encoder = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(fps), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    n = int(total * fps)
    for k in range(n):
        t = k / fps
        if t < LEAD_HOLD:
            image = finish
        elif t < lead:
            image = Image.blend(finish, opening, ease((t - LEAD_HOLD) / LEAD_FADE))
        else:
            image = frame(t - lead, cards)
        encoder.stdin.write(image.tobytes())
        if k % fps == 0:
            print(f"{t:5.1f} / {total:.1f} s", flush=True)
    encoder.stdin.close()
    encoder.wait()
    print(out)


if __name__ == "__main__":
    main()
