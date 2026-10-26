"""Render a frames file to a wav. usage: python scripts/say.py frames/reference.json out.wav"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sayhello import synth

frames = json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
synth.save_wav(sys.argv[2], synth.render(frames))
