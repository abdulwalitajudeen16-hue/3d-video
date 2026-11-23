---
name: mentor-studio-production
description: Main production workflow for Young Wise Mentor Studio. Use when the user wants to turn a script and/or voiceover into a character-led video starring the Young Wise Mentor, e.g. "make a video from this script", "produce a Reel/Short/TikTok with the mentor", "turn this voiceover into a presenter video", "storytelling video with the mentor". Orchestrates analysis, planning, generation, assembly and QC.
---

# Young Wise Mentor Studio: production workflow

You run a character-led video pipeline. The mentor is the man in `${CLAUDE_PLUGIN_ROOT}/assets/mentor-reference.jpg`. That photo is the only identity source. Read the sibling skills for each stage; this skill sequences them.

## Honesty rules (never break)

- This plugin plans, orchestrates, assembles and checks. It does **not** generate lip-synced video by itself. A real generation provider with credentials is required (see `docs/PROVIDERS.md`). If none is ready, say so, finish everything that does not need one (analysis, plan, subtitles, job packages), and state exactly what is missing.
- Never claim lip-sync, identity or realism is good unless QC measured it or a human confirmed it. Report QC results as returned, including FAIL and NEEDS_REVIEW.
- Never state that a provider works unless the user has run it. Adapters are tested against local fakes only.
- The `mock` provider is for pipeline testing. Never present mock output as a finished video.

## Inputs to collect (ask only what is missing)

1. Script text. 2. Voiceover audio file (WAV/MP3/M4A). Without audio, stop at planning and ask for it; do not invent timings.
3. Target: `youtube` (16:9), `youtube-shorts`, `instagram-reels`, `tiktok` (9:16) or `vertical`/`landscape`.
4. Subtitles yes/no. 5. Mode: `presenter`, `storytelling`, or mixed (default: let the planner decide per scene).
6. Provider. Check what is ready with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py doctor`.

## Steps

1. **Doctor.** Run `doctor`. Note ffmpeg, providers ready, ASR availability.
2. **Timing.** Follow `voiceover-lipsync`. Prefer real word timings (transcript or ASR). If timings are estimated, say so.
3. **Analyse + plan.** Follow `script-analysis`, `scene-planning`, `gesture-movement-planning`. Run `plan`, then read the plan and improve it yourself: refine actions, expressions, gestures and camera, keeping every storytelling action justified by words in the narration. Re-run `validate` after edits. Show the user a compact scene table and get a go-ahead before spending provider credits unless they told you to proceed.
4. **Generate.** Follow `video-generation`. Presenter scenes need a lip-sync provider; acted storytelling scenes need an image-to-video provider. Check capabilities first; do not route a scene to a provider that cannot do it.
5. **Assemble.** `assemble` with the chosen preset (and `--subtitles --timing timing.json` if requested). The ORIGINAL voiceover is the final audio track.
6. **QC.** Follow `video-quality-control`. Show the verdict and every FAIL/REVIEW line. Send the review sheet so the user can judge identity and realism.
7. **Deliver** the video, subtitles (.srt), QC report and plan. Offer specific fixes for each failed or doubtful check (re-generate named scenes with `--only`-style reruns: delete that scene's clip and re-run; finished clips are reused).

## Character rules (summary; full detail in `character-consistency`)

Photorealistic live-action only. Never cartoon, 2D/3D illustration, filter, different face, hairstyle, skin tone or clothing. If a provider returns any of that, reject the clip.

## Likeness and disclosure

Confirm once that the user has the right to use the photographed person's likeness for synthetic video. Remind them that major platforms ask creators to label realistic AI-generated or altered content; they should check each platform's current rules.
