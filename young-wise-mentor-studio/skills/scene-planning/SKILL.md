---
name: scene-planning
description: Divides a script plus voiceover timing into synchronised scenes with action, expression, gestures, body movement, environment, camera, emotion and presenter/storytelling mode. Use when the user wants a scene breakdown, shot list, or storyboard for a mentor video, or after script analysis.
---

# Scene planning

## Produce the baseline, then improve it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py plan --script script.txt --timing timing.json \
  --aspect 9:16 --title "My title" --max-presenter-s 25 --out plan.json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py validate --plan plan.json
```

The planner groups beats, snaps cuts into pauses, picks cameras, assigns gestures and builds prompts. Read `plan.json` and refine by editing the JSON, then re-run `validate`.

## Every scene must specify

narration, start/end (seconds, from the voiceover), mode, `needs_lipsync`, action, expression, hands, body, environment, camera_angle, camera_movement, emotion, gesture_cues, prompt.

## Rules

- Scenes tile the audio exactly: no gaps, no overlaps, last scene ends at the audio end.
- Cut in pauses. Notes like "Boundary not in a pause" mean a cut lands mid-speech; fix by merging scenes or choosing a different boundary.
- Presenter scenes: eye contact, speaking on camera, lip-sync required, length within the provider limit (OmniHuman via fal: under 30 s at 1080p, 60 s at 720p; the planner's `--max-presenter-s` should stay below that).
- Storytelling scenes: narration is voice-over, he is not speaking on camera (`needs_lipsync: false`), and `action_trigger` must be words actually in the narration. `validate` rejects invented actions.
- Vary framing: do not use the same camera angle in consecutive presenter scenes. Vertical: medium close-up and close-up dominate; landscape: allow wider medium shots (needs a wide reference, see `character-consistency`).
- Environment stays plausible and low-key; the reference setting is a dim interior with warm light. Storytelling environments may change but the hoodie and identity do not.
- Match camera movement to emotion: slow push-in for intensity, handheld micro-shake for frustration, tracking for walking, static for calm.

## Show the user

A compact table (scene, time, mode, action, expression, camera). Offer to adjust before generating, since generation costs money.
