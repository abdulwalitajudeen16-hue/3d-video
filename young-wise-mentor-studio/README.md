# Young Wise Mentor Studio

A Claude plugin for character-led, photorealistic self-improvement videos. It turns a script and voiceover into a scene plan, drives a real lip-sync / video-generation provider, assembles the result with ffmpeg, adds subtitles, and gates the output with an honest quality check.

The character is the man in `assets/mentor-reference.jpg`. That photograph is permanent and authoritative. He is never cartoonised, restyled or replaced, and his hoodie stays on.

## What it does and does not do

| Does (implemented and tested) | Needs an external service | Not possible in code |
|---|---|---|
| Speech/pause analysis; script analysis; scene, gesture and camera planning; prompt building with an identity lock; plan validation (no invented actions) | Lip-synced talking-head generation (built-in adapter: fal.ai OmniHuman v1.5) | Judging photorealism, lip-sync accuracy and gesture naturalness automatically; those are flagged for a human |
| Voiceover-locked assembly to 9:16 / 16:9, SRT + burned subtitles, resumable runs | Acted storytelling shots (configure any image-to-video API, or hand-process) | |
| QC gate: dimensions, length, A/V sync, audio match, black frames, frozen presenter shots, gesture variety, plan integrity | | |

**No video has been generated with a real provider during development**, so lip-sync quality and identity fidelity of real output are unverified. See `docs/PROVIDERS.md`.

## Install

Package the folder as a `.plugin` (zip of this directory) and add it to Claude, or place it in a Claude Code plugin marketplace/directory. Skills appear as `produce-video`, `plan-video`, `check-video`, `studio-setup`, plus the production, character, script, scene, voiceover, gesture, generation and QC skills.

## Requirements

- Python 3.10+, `ffmpeg` and `ffprobe` on PATH (with libass for burned subtitles), `requests`, `Pillow`.
- A generation provider with credentials (see `docs/PROVIDERS.md`). For the built-in one: `export FAL_KEY=...`.
- Optional: `faster-whisper` (real word timestamps), `face_recognition` (identity scoring).
- Run the CLI on a machine with internet access to your provider; sandboxes with restricted networking will refuse the API calls.

## Quick start

```bash
python3 scripts/ymm_cli.py doctor
python3 scripts/ymm_cli.py timing --audio vo.wav --script script.txt --out work/timing.json
python3 scripts/ymm_cli.py plan --script script.txt --timing work/timing.json --aspect 9:16 --out work/plan.json
python3 scripts/ymm_cli.py run --script script.txt --audio vo.wav --work work --preset youtube-shorts \
        --out final.mp4 --provider fal-omnihuman --story-provider manual --subtitles --title "My video"
```

Use `--provider mock` to test the pipeline without credentials. The QC gate will mark mock output FAILED by design.

## Layout

```
.claude-plugin/plugin.json      manifest
assets/                         mentor-reference.jpg (original), character-profile.json
skills/                         12 skills (production, character, script, scene, voiceover, gesture, generation, QC + 4 slash actions)
scripts/ymm_cli.py              command line
scripts/ymm/                    timing, script_analysis, scene_planner, gestures, prompts, subtitles, assemble, qc, pipeline
scripts/ymm/providers/          base interface, fal_omnihuman, generic_http, manual, mock
config/                         platforms.json, providers.example.json
docs/PROVIDERS.md               integrations, verification status
examples/sample-script.txt      example script
tests/                          pytest suite (24+ tests)
```

## Tests

`python3 -m pytest tests` (needs ffmpeg). They cover timing, planning rules, gestures, subtitles, provider protocols against local fakes, assembly, QC gating (including that mock output fails) and landscape reference cropping.

## Responsible use

Use only a likeness you have the right to use. Most platforms require labelling of realistic AI-generated or altered content; check each platform's current policy before posting.
