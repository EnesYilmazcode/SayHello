"""One model's card: its logo, its name, its voice as a row of bars, what Whisper heard, and a stamp.

Every size is a fraction of the card's height, so the same drawing works for the big opening card
and the small grid cards, and for every size in between while one shrinks into the other.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/segoeuib.ttf"
BG, CARD, ACTIVE, DARK, LIGHT = "#faf8ef", "#eee4da", "#e3d6c8", "#776e65", "#d6cdc4"
HIT, MISS = (25, 108, 240), (229, 81, 140)
BARS = 28

NAMES = {
    "meta/llama-3.1-8b": ("Llama 3.1 8B", "meta-color"),
    "openai/gpt-oss-20b": ("gpt-oss-20b", "openai"),
    "alibaba/qwen-3-32b": ("Qwen3 32B", "qwen-color"),
    "meta/llama-3.3-70b": ("Llama 3.3 70B", "meta-color"),
    "deepseek/deepseek-v4-pro": ("DeepSeek V4 Pro", "deepseek-color"),
    "moonshotai/kimi-k3": ("Kimi K3", "kimi-color"),
    "google/gemini-3.5-flash": ("Gemini 3.5 Flash", "gemini-color"),
    "openai/gpt-5.5": ("GPT-5.5", "openai"),
    "anthropic/claude-haiku-5.5": ("Claude Haiku 5.5", "claude-color"),
    "anthropic/claude-opus-5.5": ("Claude Opus 5.5", "claude-color"),
}


@lru_cache(maxsize=None)
def font(size):
    return ImageFont.truetype(FONT, max(8, int(size)))


@lru_cache(maxsize=None)
def logo(key, size):
    image = Image.open(HERE / "logos" / f"{key}.png").convert("RGBA")
    return image.resize((size, size), Image.LANCZOS)


def bars(audio, n=BARS):
    """Loudness of each slice of the clip, 0 to 1, square-rooted so quiet sounds still show."""
    chunks = np.array_split(np.abs(audio), n)
    level = np.array([np.sqrt(np.mean(c ** 2)) if len(c) else 0 for c in chunks])
    return np.sqrt(level / (level.max() or 1))


def mix(a, b, t):
    a = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(a, str) else a
    b = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(b, str) else b
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


@lru_cache(maxsize=None)
def stamp(verdict, size, angle=-12):
    """A stamp: a cream disc with a ring and a tick or a cross, tilted, on its own layer."""
    k = 4  # drawn large, then shrunk, for clean edges
    n = size * k
    image = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    colour = HIT if verdict else MISS
    ring = n * 0.07
    d.ellipse((ring / 2, ring / 2, n - ring / 2, n - ring / 2), fill=BG, outline=colour, width=int(ring))
    d.ellipse((ring * 1.9, ring * 1.9, n - ring * 1.9, n - ring * 1.9), outline=colour, width=max(1, int(ring * 0.35)))
    c, r, width = n / 2, n * 0.3, int(n * 0.1)
    if verdict:
        d.line([(c - r * 0.75, c + r * 0.02), (c - r * 0.2, c + r * 0.55), (c + r * 0.8, c - r * 0.55)],
               fill=colour, width=width, joint="curve")
    else:
        for sx in (-1, 1):
            d.line([(c - r * 0.6 * sx, c - r * 0.6), (c + r * 0.6 * sx, c + r * 0.6)], fill=colour, width=width)
    return image.rotate(angle, resample=Image.BICUBIC).resize((size, size), Image.LANCZOS)


def draw_card(canvas, box, model, levels, played=0.0, verdict=None, mark=0.0, heard="", active=0.0):
    """box: (x, y, w, h) in canvas pixels. played: how much of the voice has sounded, 0 to 1.
    verdict: True heard as the word, False not, None not judged yet. mark: how far the stamp has
    come down, 0 to 1. heard: what Whisper wrote down, typed out as the clip plays. active: 1 while
    this card is the one speaking, which warms its background a little."""
    ox, oy, w, h = box
    # draw on a layer just big enough for the card, then place it; a full-canvas layer per card is slow
    pad = int(h * 0.02) + 2
    layer = Image.new("RGBA", (int(w) + 2 * pad, int(h) + 2 * pad), (0, 0, 0, 0))
    x = y = pad
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x, y, x + w, y + h), radius=h * 0.06, fill=mix(CARD, ACTIVE, active))

    name, key = NAMES[model]
    size = int(h * 0.2)
    layer.alpha_composite(logo(key, size), (int(x + (w - size) / 2), int(y + h * 0.08)))
    f = font(h * 0.062)
    while f.getlength(name) > w * 0.9 and f.size > 8:
        f = font(f.size - 1)
    d.text((x + w / 2, y + h * 0.37), name, font=f, fill=DARK, anchor="mm")

    # the voice: bars light up as the clip plays, then take the verdict's colour
    top, bottom = y + h * 0.47, y + h * 0.71
    mid, half = (top + bottom) / 2, (bottom - top) / 2
    step = w * 0.84 / len(levels)
    left = x + w * 0.08
    tint = HIT if verdict else MISS
    lit = DARK if verdict is None else mix(DARK, mix(tint, CARD, 0.5), mark)  # soft, so the stamp stands out
    for i, level in enumerate(levels):
        bx = left + i * step + step * 0.2
        bh = max(h * 0.008, level * half)
        colour = lit if (i + 0.5) / len(levels) <= played else LIGHT
        d.rounded_rectangle((bx, mid - bh, bx + step * 0.6, mid + bh), radius=step * 0.3, fill=colour)

    # what Whisper heard, typed out while the clip plays
    shown = heard[:int(round(len(heard) * played))]
    if shown:
        f = font(h * 0.075)
        while f.getlength(f'"{heard}"') > w * 0.9 and f.size > 8:
            f = font(f.size - 1)
        text = f'"{shown}"' if len(shown) == len(heard) else f'"{shown}'
        d.text((x + w / 2, y + h * 0.85), text, font=f, fill=mix(DARK, tint, mark) if verdict is not None else DARK,
               anchor="mm")

    # the stamp lands on the bars once the clip is over: big and faint, then down and solid
    if verdict is not None and mark > 0:
        drop = 1 - (1 - min(1, mark / 0.45)) ** 3
        scale = 1.75 - 0.75 * drop + 0.05 * np.sin(np.pi * np.clip((mark - 0.45) / 0.55, 0, 1))
        side = max(4, int(h * 0.3 * scale))
        image = stamp(verdict, int(h * 0.3)) if side == int(h * 0.3) else stamp(verdict, int(h * 0.3 * 1.75)).resize((side, side), Image.LANCZOS)
        image.putalpha(image.getchannel("A").point(lambda a: int(a * min(1, drop * 1.3))))
        layer.alpha_composite(image, (int(x + w / 2 - side / 2), int(mid - side / 2)))

    canvas.alpha_composite(layer, (int(ox) - pad, int(oy) - pad))
