<h1 align="center">Say Hello</h1>

<p align="center"><b>Ten language models try to make a speech synthesizer say "hello".</b><br>
No audio and no tools. Each one writes the numbers that shape the sound, and Whisper says what it heard.</p>

<p align="center">
  <img src="media/say-hello.gif" width="560" alt="Ten model cards, each with its voice as a row of bars and a tick or a cross">
</p>

## How it works

1. **Prompt.** Each model is told it controls a formant synthesizer and must answer with a JSON list of frames: how long each lasts, the voice pitch, the first three formants (the resonances of the mouth that make one vowel sound different from another), and how loud the buzz of the voice and the hiss of breath are. Nothing else. The full prompt is in [`sayhello/ask.py`](sayhello/ask.py).
2. **Synthesize.** A small cascade formant synthesizer, written for this repo, turns the frames into 16 kHz audio. A pulse train makes the voice, noise makes the breath, and both run through three moving resonators.
3. **Listen.** Whisper (`small.en`) transcribes every clip. A try counts when the word hello is in what it wrote down.
4. **Repeat.** Ten models, three tries each, all asked through the Vercel AI Gateway with the same prompt.

## System design

The model never hears anything and never runs code. Its whole answer is a list of numbers, and everything after that is fixed.

```mermaid
flowchart LR
  P["Prompt: make the synthesizer say hello"] --> M["Language model, through the Vercel AI Gateway"]
  M --> F["A JSON list of frames: pitch, three formants, voice and breath loudness"]
  F --> S["Formant synthesizer: 16 kHz audio"]
  S --> W["Whisper writes down what it hears"]
  W --> R["Hit if the transcript contains hello"]
```
