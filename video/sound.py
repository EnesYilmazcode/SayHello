"""The video's sound: each model's own voice, plus a soft plink on a hit and a low knock on a miss.

Nothing sustained, only short sounds tied to what is on screen.
"""
import wave

import numpy as np

SR = 48000
PENTATONIC = (523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66)


def tone(freq, duration, decay, harmonics=(1, 0.2)):
    t = np.arange(int(SR * duration)) / SR
    envelope = np.minimum(1, t / 0.004) * np.exp(-decay * t)
    return envelope * sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harmonics))


def plink(step):
    return tone(PENTATONIC[min(step, len(PENTATONIC) - 1)], 0.6, 9, (1, 0.0, 0.2))


def knock():
    return tone(196.0, 0.35, 14, (1, 0.35, 0.1))


def upsample(audio, rate):
    t = np.arange(int(len(audio) * SR / rate)) / SR
    return np.interp(t, np.arange(len(audio)) / rate, audio)


def mix(events, duration):
    """events: (seconds, kind, payload). kind is voice (payload: (audio, rate, seconds to play)),
    hit (payload: step up the scale) or miss."""
    out = np.zeros(int(SR * (duration + 1)))
    for at, kind, payload in events:
        if kind == "voice":
            audio, rate, play = payload
            sound = upsample(audio, rate)[:int(play * SR)]
            fade = min(len(sound), int(0.12 * SR))
            sound[len(sound) - fade:] *= np.linspace(1, 0, fade) ** 2  # a long clip is cut, not chopped
            sound, gain = sound, 0.55
        elif kind == "hit":
            sound, gain = plink(payload), 0.16
        elif kind == "miss":
            sound, gain = knock(), 0.2
        else:
            raise ValueError(f"unknown sound: {kind}")
        i = int(at * SR)
        piece = sound[:max(0, len(out) - i)] * gain
        out[i:i + len(piece)] += piece
    return np.tanh(out[:int(SR * duration)] * 1.2) / np.tanh(1.2)


def write_wav(path, audio):
    data = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(SR)
        target.writeframes(data.tobytes())
