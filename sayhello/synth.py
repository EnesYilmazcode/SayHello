"""A small cascade formant synthesizer. A list of frames goes in, 16 kHz audio comes out.

Each frame sets a voice pitch, three formants and how loud the buzz and the hiss are. Values glide
linearly from one frame to the next, and both sources pass through the same three resonators.
"""
import wave

import numpy as np

SR = 16000
BW = (70.0, 100.0, 160.0)  # formant bandwidths in Hz
MAX_SECONDS = 4


def frame_samples(frame):
    return max(1, int(float(frame.get("ms", 50)) * SR / 1000))


def track(frames, key, n):
    """One value per sample, ramping from each frame's value to the next one's."""
    at, values, t = [], [], 0
    for frame in frames:
        at.append(t)
        values.append(float(frame.get(key, 0) or 0))
        t += frame_samples(frame)
    at.append(t)
    values.append(values[-1])
    return np.interp(np.arange(n), at, values)


def resonate(x, freq, bandwidth):
    """Two-pole resonator with unity gain at 0 Hz, its centre moving sample by sample."""
    freq = np.clip(freq, 50, SR / 2 - 200)
    r = np.exp(-np.pi * bandwidth / SR)
    a1 = 2 * r * np.cos(2 * np.pi * freq / SR)
    a2 = -r * r
    gain = 1 - a1 - a2
    y = np.zeros(len(x))
    y1 = y2 = 0.0
    for i in range(len(x)):
        v = gain[i] * x[i] + a1[i] * y1 + a2 * y2
        y[i] = v
        y2, y1 = y1, v
    return y


def render(frames):
    n = min(sum(frame_samples(f) for f in frames), SR * MAX_SECONDS)
    f0, voice, noise = (track(frames, k, n) for k in ("f0", "voice", "noise"))

    # glottal source: a smooth pulse per period, differentiated for brightness
    phase = np.cumsum(np.clip(f0, 0, 600) / SR) % 1.0
    pulse = np.where(phase < 0.6, np.sin(np.pi * phase / 0.6) ** 2, 0.0)
    pulse = np.diff(pulse, prepend=0) * 10
    source = pulse * np.clip(voice, 0, 1) * (f0 > 20)
    rng = np.random.default_rng(0)
    source = source + rng.standard_normal(n) * 0.15 * np.clip(noise, 0, 1)

    out = source
    for key, bandwidth in zip(("f1", "f2", "f3"), BW):
        out = resonate(out, track(frames, key, n), bandwidth)
    peak = np.max(np.abs(out)) or 1.0
    return (out / peak * 0.9).astype(np.float32)


def save_wav(path, audio):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def load_wav(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768.0
