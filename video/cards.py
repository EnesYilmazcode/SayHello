"""One model's card: its logo, its name, its voice as a row of bars, and a mark for the verdict.

Every size is a fraction of the card's height, so the same drawing works for the big opening card
and the small grid cards, and for every size in between while one shrinks into the other.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/segoeuib.ttf"
BG, CARD, DARK, LIGHT = "#faf8ef", "#eee4da", "#776e65", "#d6cdc4"
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


def draw_card(canvas, box, model, levels, played=0.0, verdict=None, mark=0.0, fade=1.0):
    """box: (x, y, w, h) in canvas pixels. played: how much of the voice has sounded, 0 to 1.
    verdict: True heard as the word, False not, None not judged yet. mark: how far the mark has
    popped in, 0 to 1. fade: 0 draws nothing, 1 the full card."""
    x, y, w, h = box
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x, y, x + w, y + h), radius=h * 0.06, fill=CARD)

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
    lit = DARK if verdict is None else mix(DARK, HIT if verdict else MISS, mark)
    for i, level in enumerate(levels):
        bx = left + i * step + step * 0.2
        bh = max(h * 0.008, level * half)
        colour = lit if (i + 0.5) / len(levels) <= played else LIGHT
        d.rounded_rectangle((bx, mid - bh, bx + step * 0.6, mid + bh), radius=step * 0.3, fill=colour)

    # the mark: a filled circle with a tick or a cross, springing in
    if verdict is not None and mark > 0:
        pop = 1 + 0.25 * np.sin(np.pi * min(1, mark)) * (mark < 1)
        r = h * 0.075 * min(1, mark * 1.6) * pop
        cx, cy = x + w / 2, y + h * 0.86
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=HIT if verdict else MISS)
        width = max(2, int(r * 0.22))
        if verdict:
            d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.35), (cx + r * 0.48, cy - r * 0.32)],
                   fill="white", width=width, joint="curve")
        else:
            for sx in (-1, 1):
                d.line([(cx - r * 0.38 * sx, cy - r * 0.38), (cx + r * 0.38 * sx, cy + r * 0.38)], fill="white", width=width)

    if fade < 1:
        alpha = layer.getchannel("A").point(lambda a: int(a * fade))
        layer.putalpha(alpha)
    canvas.alpha_composite(layer)
