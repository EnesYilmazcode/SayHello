"""Ask a language model for the frames that make the synthesizer say a word.

The model gets text only and must answer with numbers. It cannot run code or listen to anything.
"""
import json
import os
import re

import requests

GATEWAY = "https://ai-gateway.vercel.sh/v1/chat/completions"


def prompt(word):
    return f"""You are controlling a formant speech synthesizer. You cannot run code or use tools.

Output a JSON array of frames. Each frame is an object:
  "ms":    duration of the frame in milliseconds
  "f0":    voice pitch in Hz (0 = no voicing)
  "f1", "f2", "f3": the first three formant frequencies in Hz
  "voice": loudness of the voiced (buzz) source, 0 to 1
  "noise": loudness of the breath/hiss noise source, 0 to 1

Values glide linearly from one frame to the next. Both sources pass through the formant filters.

Make the synthesizer say the word "{word}" as clearly as you can, so a person would recognize it.
Reply with only the JSON array."""


def ask(model, word, max_tokens=12000):
    r = requests.post(
        GATEWAY,
        headers={"Authorization": f"Bearer {os.environ['AI_GATEWAY_API_KEY']}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt(word)}], "max_tokens": max_tokens},
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"] or ""


def parse(reply):
    """The first JSON array in the reply, which must be a list of frame objects."""
    match = re.search(r"\[.*\]", reply, re.S)
    if not match:
        raise ValueError("no JSON array in the reply")
    frames = json.loads(match.group(0))
    if not (isinstance(frames, list) and frames and all(isinstance(f, dict) for f in frames)):
        raise ValueError("the array is not a list of frames")
    return frames
