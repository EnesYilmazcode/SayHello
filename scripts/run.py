"""Ask every model for a word a few times and render each answer.

usage: AI_GATEWAY_API_KEY=... python scripts/run.py [word] [tries] [model ...]

Writes results/<word>/<model>_<try>.txt (the raw reply), .json (the frames) and .wav (the audio).
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sayhello import synth
from sayhello.ask import ask, parse

MODELS = [
    "meta/llama-3.1-8b",
    "openai/gpt-oss-20b",
    "alibaba/qwen-3-32b",
    "meta/llama-3.3-70b",
    "deepseek/deepseek-v4-pro",
    "moonshotai/kimi-k3",
    "google/gemini-3.5-flash",
    "openai/gpt-5.5",
    "anthropic/claude-haiku-5.5",
    "anthropic/claude-opus-5.5",
]


def name(model, i):
    return f"{model.split('/')[1]}_{i}"


def render(reply, out, stem):
    frames = parse(reply)
    (out / f"{stem}.json").write_text(json.dumps(frames, indent=1), encoding="utf8")
    synth.save_wav(out / f"{stem}.wav", synth.render(frames))
    return len(frames)


def job(model, i, word, out):
    stem = name(model, i)
    try:
        reply = ask(model, word)
        (out / f"{stem}.txt").write_text(reply, encoding="utf8")
        return stem, "ok", render(reply, out, stem)
    except Exception as e:
        return stem, "FAIL", repr(e)[:200]


def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "hello"
    tries = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    models = sys.argv[3:] or MODELS
    out = ROOT / "results" / word
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(m, i) for m in models for i in range(tries)]
    with ThreadPoolExecutor(12) as pool:
        for result in pool.map(lambda j: job(*j, word, out), jobs):
            print(*result, flush=True)


if __name__ == "__main__":
    main()
