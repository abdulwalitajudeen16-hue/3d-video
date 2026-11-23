---
name: plan-video
description: Slash action to analyse a script and voiceover and output the scene plan only, with no generation or spend. Use when the user types /plan-video or asks for a storyboard, shot list or scene breakdown for the mentor.
---

# /plan-video

Run `script-analysis`, `voiceover-lipsync` stage 1, `scene-planning` and `gesture-movement-planning`. Save `plan.json` and present a compact scene table (scene, start-end, mode, action, expression, gestures, camera, emotion). Do not call any generation provider. End by asking whether to proceed to `/produce-video`, and mention if word timings are only estimated.
