"""The judge: Whisper writes down what it hears in a clip.

usage: python -m sayhello.hear a.wav b.wav ...
"""
import sys
from functools import lru_cache

import numpy as np

from sayhello import synth


@lru_cache(maxsize=1)
def model():
    from faster_whisper import WhisperModel
    return WhisperModel("small.en", device="cpu", compute_type="int8")


PAD = 0.4  # seconds of silence on each side; Whisper guesses wildly on a clip with no lead-in


def pad(audio):
    silence = np.zeros(int(PAD * synth.SR), np.float32)
    return np.concatenate([silence, np.asarray(audio, np.float32), silence])


def hear(audio):
    """Text Whisper heard, and its confidence: the mean token probability."""
    segments, _ = model().transcribe(pad(audio), beam_size=5, language="en",
                                     condition_on_previous_text=False)
    segments = list(segments)
    text = " ".join(s.text.strip() for s in segments).strip()
    confidence = float(np.exp(np.mean([s.avg_logprob for s in segments]))) if segments else 0.0
    return text, confidence


if __name__ == "__main__":
    for path in sys.argv[1:]:
        text, confidence = hear(synth.load_wav(path))
        print(f"{path}\t{text or '(nothing)'}\t{confidence:.2f}")
