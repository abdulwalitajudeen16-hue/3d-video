---
name: voiceover-lipsync
description: Voiceover analysis, word-level timestamps and the real lip-sync workflow for the mentor's presenter scenes. Use when the user supplies a voiceover/audio file, asks about lip-sync accuracy, timestamps, subtitles timing, or which engine to use.
---

# Voiceover and lip-sync

## Stage 1: analyse the audio

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py timing --audio vo.wav --script script.txt --out timing.json
# with a real transcript of the audio (best option if no ASR installed):
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py timing --audio vo.wav --transcript words.json --out timing.json
```

- Speech/silence map: measured with ffmpeg `silencedetect`. Real measurement.
- Word timestamps, in order of preference: imported transcript (JSON with word times, or SRT/VTT) -> `faster-whisper` / `openai-whisper` if installed (`source: asr`) -> **estimated** by spreading script words over detected speech (`source: estimated`).
- `estimated` is not alignment. It is good enough to place scene cuts near pauses but not to claim lip-sync or subtitle accuracy. Tell the user and recommend a transcript or ASR install.

## Stage 2: lip-sync generation

Lip-sync is done by a real audio-driven engine, never by prompt text such as "mouth moves while talking". The pipeline cuts the voiceover at scene boundaries (`work/audio/scene_NN.wav`) and sends the reference photo plus that audio clip to the provider.

- Built-in adapter: `fal-omnihuman` (ByteDance OmniHuman v1.5 via fal.ai; needs `FAL_KEY`). Public docs: image + audio in, video out, audio under 30 s at 1080p / 60 s at 720p. Not yet run against the live service by this plugin's author. Report that honestly.
- Other engines: define them in `config/providers.json` (`GenericHTTP`) from the vendor's docs, or use `manual` to get job folders for a web UI.
- No provider ready: stop before generation, explain which credentials/integration are needed (`docs/PROVIDERS.md`), and deliver the plan and job packages.

## Stage 3: keep sync

- The final audio is always the original voiceover muxed over the assembled video, so audio cannot drift from the supplied file.
- Pauses: scenes cut in silences; providers decide mouth rest during silence inside a clip. Check pauses in review.
- QC measures duration/sync of streams and that output audio matches the source speech map. It cannot measure whether mouth shapes match phonemes. That is a human watch-through (`NEEDS_REVIEW`).

## Limits to state when relevant

Clip length caps per provider; accents/languages vary in quality by engine; fast speech and heavy emotion can degrade sync; head turns and hand-over-face frames are common failure points.
