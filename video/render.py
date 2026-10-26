"""Render the showcase video with PIL at 2x and encode it with ffmpeg.

usage: python video/render.py [word] [out.mp4] [fps]

The best model plays first on a big card, which then shrinks into a grid of all ten. The rest play
one by one, smallest model to largest. The first frame is the finished grid, which dissolves into
the opening, because X uses the first frame as the thumbnail.
"""
import json
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
BIG_H = 1000
MAX_PLAY = 1.6                    # seconds of a clip that play; longer ones fade out
LEAD_HOLD, LEAD_FADE, END_HOLD = 0.85, 0.45, 2.0
HIGHLIGHT, LIFT = 0.18, 1.08      # seconds to lift a card as its turn starts, and how much
GAPS = (0.35, 0.15)               # pause after each verdict, first to last


def ease(t):
    t = float(np.clip(t, 0, 1))
    return t * t * (3 - 2 * t)


def lerp_box(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def scale_box(box, k):
    x, y, w, h = box
    return (x + w * (1 - k) / 2, y + h * (1 - k) / 2, w * k, h * k)


def slot(i):
    left = (W - COLS * CARD_W - (COLS - 1) * GAP) / 2
    top = (H - 2 * CARD_H - GAP) / 2
    return (left + (i % COLS) * (CARD_W + GAP), top + (i // COLS) * (CARD_H + GAP), CARD_W, CARD_H)


def load(word):
    out = ROOT / "results" / word
    board = json.loads((out / "scoreboard.json").read_text(encoding="utf8"))
    cards = []
    for m in board["models"]:
        audio = synth.load_wav(out / f"{m['clip']}.wav")
        play = min(len(audio) / synth.SR, MAX_PLAY)
        cards.append({"model": m["model"], "audio": audio, "play": play, "hit": m["hits"] > 0,
                      "levels": bars(audio[:int(play * synth.SR)])})
    featured = next(i for i, c in enumerate(cards) if c["model"] == board["featured"])
    return cards, featured


def timeline(cards, featured):
    """When each card's voice starts and when its mark lands, in story seconds."""
    big_w = BIG_H * CARD_W / CARD_H
    big = ((W - big_w) / 2, (H - BIG_H) / 2, big_w, BIG_H)
    f = cards[featured]
    f["start"] = 0.5
    f["mark"] = f["start"] + f["play"] + 0.12
    morph = (f["mark"] + 0.9, f["mark"] + 1.65)
    t = morph[1] + 0.3
    others = [i for i in range(len(cards)) if i != featured]
    for k, i in enumerate(others):
        c = cards[i]
        c["lift"] = t
        c["start"] = t + HIGHLIGHT
        c["mark"] = c["start"] + c["play"] + 0.08
        t = c["mark"] + 0.25 + GAPS[0] + (GAPS[1] - GAPS[0]) * k / max(1, len(others) - 1)
    return big, morph, t + END_HOLD


def state(t, cards, featured, big, morph):
    """Box, progress and mark for every card at story time t. The lifted card is drawn last."""
    drawn = []
    grow = ease((t - morph[0]) / (morph[1] - morph[0]))
    for i, c in enumerate(cards):
        played = np.clip((t - c["start"]) / c["play"], 0, 1)
        mark = np.clip((t - c["mark"]) / 0.35, 0, 1)
        if i == featured:
            box, fade, lift = lerp_box(big, slot(i), grow), 1.0, 0
        else:
            box, fade = slot(i), grow
            lift = ease((t - c["lift"]) / HIGHLIGHT) - ease((t - c["mark"] - 0.15) / 0.2)
            box = scale_box(box, 1 + (LIFT - 1) * lift)
        drawn.append((lift, i, box, played, mark, fade))
    return sorted(drawn, key=lambda d: (d[0] > 0, d[1]))


def frame(t, cards, featured, big, morph):
    canvas = Image.new("RGBA", (W * S, H * S), BG)
    for _, i, box, played, mark, fade in state(t, cards, featured, big, morph):
        if fade <= 0:
            continue
        c = cards[i]
        draw_card(canvas, tuple(v * S for v in box), c["model"], c["levels"], played,
                  c["hit"] if mark > 0 else None, mark, fade)
    return canvas.convert("RGB").resize((W, H), Image.LANCZOS)


def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "hello"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "renders" / f"{word}.mp4"
    fps = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    out.parent.mkdir(parents=True, exist_ok=True)

    cards, featured = load(word)
    big, morph, story = timeline(cards, featured)
    lead = LEAD_HOLD + LEAD_FADE
    total = lead + story

    events, hits = [], 0
    for c in cards:
        events.append((lead + c["start"], "voice", (c["audio"], synth.SR, c["play"])))
        events.append((lead + c["mark"], "hit" if c["hit"] else "miss", hits))
        hits += c["hit"]
    wav = out.with_suffix(".wav")
    write_wav(wav, mix(events, total))

    finish = frame(story, cards, featured, big, morph)
    opening = frame(0, cards, featured, big, morph)
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
            image = frame(t - lead, cards, featured, big, morph)
        encoder.stdin.write(image.tobytes())
        if k % fps == 0:
            print(f"{t:5.1f} / {total:.1f} s", flush=True)
    encoder.stdin.close()
    encoder.wait()
    print(out)


if __name__ == "__main__":
    main()
