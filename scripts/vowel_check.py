"""Hold the vowel in "hello" (F1 550, F2 1800, F3 2550) and print how loud each formant comes out.

In real speech F2 sits about 10 to 15 dB under the loudest peak. Much lower and the vowel turns to "oo".
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sayhello import synth

frames = [{"ms": 300, "f0": 130, "f1": 550, "f2": 1800, "f3": 2550, "voice": 1, "noise": 0}] * 2
audio = synth.render(frames)[2000:6000] * np.hanning(4000)
db = 20 * np.log10(np.abs(np.fft.rfft(audio, 8192)) + 1e-9)
freqs = np.fft.rfftfreq(8192, 1 / synth.SR)
for name, lo, hi in [("F1", 450, 650), ("F2", 1700, 1900), ("F3", 2400, 2700)]:
    band = (freqs > lo) & (freqs < hi)
    print(f"{name}: {db[band].max() - db.max():6.1f} dB")
