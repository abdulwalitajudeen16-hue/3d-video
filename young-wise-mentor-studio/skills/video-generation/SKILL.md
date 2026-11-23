---
name: video-generation
description: Generates scene clips through the provider interface, then assembles, subtitles and exports the final mentor video for YouTube, Shorts, Reels or TikTok. Use when a scene plan exists and the user wants clips generated, assembly run, subtitles burned in, or provider setup help.
---

# Video generation, assembly and export

## Provider interface

All backends implement `Provider.generate(SceneJob) -> mp4` (`scripts/ymm/providers/`). Check readiness first:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py doctor
```

| Provider | Does | Status |
|---|---|---|
| `fal-omnihuman` | presenter lip-sync (image + audio) | documented API, adapter tested vs local fake only; needs `FAL_KEY` |
| `generic` via `config/providers.json` | anything with submit/poll/download | user supplies vendor details; untested until the user runs it |
| `manual` | writes job folders for hand processing | works, quality depends on tool used |
| `mock` | static still + audio for pipeline testing | never a deliverable; QC fails it |

Capability routing: presenter scenes need `lipsync`; storytelling scenes need `image_to_video`. The pipeline refuses mismatches instead of faking. No built-in storytelling engine is verified: configure one via `generic`, or use `manual`.

Network note: if this runs inside a sandbox without outbound access to the provider, generation will fail with a clear provider error. Run the CLI on the user's own machine in that case.

## Commands

```bash
CLI=${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py
python3 $CLI generate --plan plan.json --audio vo.wav --work work --provider fal-omnihuman [--story-provider NAME] [--resolution 720p|1080p]
python3 $CLI assemble --plan plan.json --audio vo.wav --work work --preset youtube-shorts --out final.mp4 [--subtitles --timing timing.json]
python3 $CLI run --script script.txt --audio vo.wav --work work --preset tiktok --out final.mp4 --provider NAME --subtitles   # everything incl. QC
```

Presets (`config/platforms.json`): `youtube` 1920x1080, `youtube-shorts` / `instagram-reels` / `tiktok` / `vertical` 1080x1920, `landscape` 1920x1080. Duration limits are not hard-coded; check each platform's current rules.

## Behaviour to rely on

- Resumable: finished `work/clips/scene_NN.mp4` are reused. To redo a scene, delete its clip and re-run.
- Clips are normalised (cover-scale, centre-crop, 30 fps, trimmed/held to scene length, clip audio dropped); the original voiceover is muxed as the only audio.
- Subtitles: SRT plus a styled ASS burn-in with a caption safe margin above platform UI. Subtitle timing is only as good as the word timings; with `estimated` timings, warn the user.
- Landscape needs a landscape reference; see `character-consistency`.
- Always run QC afterwards (`video-quality-control`).
