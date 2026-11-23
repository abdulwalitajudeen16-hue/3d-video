# Providers: what is needed, what is verified

The plugin does not render video by itself. Photorealistic lip-synced video needs an external generation service. This page says what each integration needs and, just as important, what has and has not been verified.

## Verification status (as of 2026-11-23)

| Item | Verified how | Not verified |
|---|---|---|
| ffmpeg pipeline (timing, cuts, normalise, concat, mux, subtitles, QC measurements) | automated tests + a CLI end-to-end run with the mock provider | n/a |
| `fal-omnihuman` request/response logic | fal's public docs for the queue API and the OmniHuman v1.5 schema; tested against a **local fake** that implements that documented protocol | any call to the real fal service; real result quality; whether base64 data URIs are accepted for `image_url`/`audio_url` |
| `generic_http` adapter | tested against a local fake REST API | any real vendor |
| `manual` | tested (job folder is written) | n/a |
| Lip-sync accuracy, identity, realism of any real output | **never verified**; no real generation was run during development | everything |

First live run: use a short (5-10 s) presenter scene, then look at the QC report and review sheet before spending more.

## fal.ai + OmniHuman v1.5 (built in, presenter scenes only)

- Why: audio-driven, image-to-video human generation, matches the reference photo to speech and produces body/hand motion from the audio.
- Setup: create a key at https://fal.ai/dashboard/keys, then `export FAL_KEY=...` on the machine running the CLI. Optional: `FAL_OMNIHUMAN_ENDPOINT` to point at another endpoint id.
- Documented inputs: `image_url`, `audio_url` (under 30 s at 1080p, under 60 s at 720p), `prompt`, `resolution` (`720p`/`1080p`), `turbo_mode`. Documented output: `video.url`.
- Billing is per second of output on fal's side; check current pricing on the model page before long runs.
- If data URIs are rejected, host the files at URLs you control and pass them through `SceneJob.extra["image_url"]` / `["audio_url"]` (small code change in `pipeline.generate_clips`).
- It cannot do acted storytelling (walking, phone, desk). Use a second provider for that.

## Storytelling shots (acted scenes)

No built-in adapter is verified. Options:

1. Define an image-to-video API in `config/providers.json` (copy `providers.example.json`) from the vendor's docs. Fields: submit URL/headers/body with `${PROMPT}`, `${IMAGE_DATA_URI}`, `${DURATION}`, `${ASPECT}`, `${ENV:KEY_NAME}`; job-id path; poll URL and status values; result video-URL path. Then `--story-provider <name>`.
2. Use `--story-provider manual`: the pipeline writes `work/jobs/scene_NN/` with the reference image, prompt and instructions; generate in any tool, save as `work/clips/scene_NN.mp4`, re-run.

Identity drift is the main risk for acted scenes. Prefer engines that accept a reference/start image and review these scenes first.

## Word timestamps

Install one of `faster-whisper` or `openai-whisper` for real word-level timings, or pass `--transcript` (JSON `[{"text","start","end"}]`, Whisper-style `segments[].words[]`, or SRT/VTT). Without either, timings are estimated and QC marks them NEEDS_REVIEW.

## Optional identity scoring

`pip install face_recognition` enables automated similarity scoring of presenter frames against the reference (code path included but not exercised in tests because the library was not installed in the build environment).

## Platform limits

Duration, loudness and caption-safe-area rules change. The presets set only size/fps/caption margin. Use `--max-seconds` for a length gate and check the platform's current rules.
