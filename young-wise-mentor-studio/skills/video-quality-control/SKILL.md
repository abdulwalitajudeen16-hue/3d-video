---
name: video-quality-control
description: Quality-control gate for finished or draft mentor videos: identity, photorealism, lip-sync, movement, gestures, emotion, scene relevance, timing, dimensions and A/V sync. Use before delivering any video, when the user asks "is it ready", or when reviewing a render.
---

# Video quality control

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py qc --plan plan.json --audio vo.wav --work work \
  --video final.mp4 --preset youtube-shorts --timing work/timing.json [--max-seconds 60]
```

Outputs `work/qc/qc_report.md`, `qc_report.json` and `review_sheet.jpg` (reference tile first, then frames from each scene).

## Statuses

- **PASS**: measured and within tolerance.
- **FAIL**: measured problem, or provably impossible to pass (e.g. mock clips cannot be lip-synced).
- **NEEDS_REVIEW**: code cannot judge this; a human must.
- Verdict: `FAILED` if any FAIL; `NEEDS_HUMAN_REVIEW` if any REVIEW; `PASSED` only if everything including human items is PASS. Expect `NEEDS_HUMAN_REVIEW` as the best automated outcome.

## What is measured

Dimensions vs preset; video length vs voiceover (±0.15 s); audio/video stream sync (±0.1 s); output speech map equals the supplied voiceover (≥95% overlap); black frames; plan validity (coverage, no invented actions); cuts in pauses; gesture variety; stationary/frozen spans in presenter scenes; provider honesty (mock = FAIL); face similarity if `face_recognition` is installed.

## What only a human can judge (always NEEDS_REVIEW)

Photorealism, lip-sync accuracy, natural body movement, gesture fit, expression/emotion fit, storytelling relevance, and identity if no face library is present. Watch the full video at normal speed with sound, open `review_sheet.jpg`, and check each presenter scene's mouth against the audio.

## Reporting

Show the verdict and every non-PASS line verbatim. Never summarise a FAIL or REVIEW as "looks good". For each failure, propose a concrete fix (regenerate named scenes, split a long scene, provide real transcript, change provider). If the user marks human items as approved, record that in your reply; do not edit the report to say PASS.
