"""Fast checks on the synthesizer. usage: python tests/test_synth.py"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sayhello import synth

VOWEL = {"ms": 200, "f0": 130, "f1": 550, "f2": 1800, "f3": 2550, "voice": 1, "noise": 0}


def test_length_follows_the_frames():
    assert len(synth.render([VOWEL, dict(VOWEL, ms=100)])) == int(0.3 * synth.SR)


def test_long_answers_are_cut_at_four_seconds():
    assert len(synth.render([dict(VOWEL, ms=9000)])) == synth.SR * synth.MAX_SECONDS


def test_same_frames_same_audio():
    assert np.array_equal(synth.render([VOWEL]), synth.render([VOWEL]))


def test_silence_stays_finite():
    audio = synth.render([dict(VOWEL, voice=0, noise=0)])
    assert np.all(np.isfinite(audio)) and np.abs(audio).max() == 0


def test_wild_values_do_not_blow_up():
    audio = synth.render([dict(VOWEL, f0=5000, f1=-20, f2=99999, f3="3000", voice=7, noise=None)])
    assert np.all(np.isfinite(audio)) and np.abs(audio).max() <= 0.9 + 1e-6


def test_wav_round_trip(tmp=ROOT / "renders" / "test.wav"):
    tmp.parent.mkdir(exist_ok=True)
    audio = synth.render(json.loads((ROOT / "frames" / "reference.json").read_text()))
    synth.save_wav(tmp, audio)
    assert np.abs(synth.load_wav(tmp) - audio).max() < 1e-4


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
