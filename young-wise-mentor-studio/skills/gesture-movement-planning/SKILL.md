---
name: gesture-movement-planning
description: Plans natural hand gestures, head and body movement, posture changes and facial expression for each scene of a mentor video, tied to the meaning and emotion of the narration. Use when the user asks about gestures, body language, avoiding stiff or repetitive movement, or how to make him not stand still.
---

# Gesture and movement planning

The planner (`scripts/ymm/gestures.py`) gives each scene timed `gesture_cues`. Refine them by hand when the narration calls for something specific.

## Vocabulary

| Gesture | Use for |
|---|---|
| open_palms | inclusive/open statements ("everyone", "possible") |
| one_hand_explain | neutral explanation, default rhythm |
| two_hand_frame | introducing an idea or framework |
| point_to_camera | "you" in urgent or questioning lines, calls to action |
| count_fingers | "first, second, third" lists |
| closed_fist / chop_emphasis | strong emphasis words (never, must, stop, now) |
| spread_hands | contrast ("but", "instead") or scale |
| hand_to_chest | sincerity, personal admission |
| palm_down_calm | calming, patience, slowing down |
| lean_forward | urgency, intimacy, key point |
| head_nod / head_tilt | confirmation / questioning |
| shoulder_settle / posture_shift | breath, topic change, reset after a heavy point |

## Rules

- Gesture follows meaning: choose from the words and emotion, place the cue on the trigger word's timestamp when real timings exist.
- No back-to-back repeats and no single gesture dominating (QC enforces: 0 consecutive repeats, no gesture above 50% share on 6+ cues).
- Minimum motion density: about 3 events per 10 s so he never freezes. Pointing is rare and earned; do not point every sentence.
- Pair gestures with expression and posture: frustration = tight jaw + chop or hand over face; hope = softer eyes + open palms; sadness = slower, fewer gestures, shoulder settle.
- Storytelling scenes: the action carries the movement (hands busy with phone/laptop). Keep extra gestures minimal.
- Make rhythm irregular: vary spacing between cues; return to a relaxed rest pose between gestures.

## Honest limitation

Audio-driven engines such as OmniHuman choose their own gestures from the speech; prompts only nudge them, and exact cue timing is not guaranteed. Treat the plan as direction and verify in review. Storytelling image-to-video engines follow prompts more literally but do not lip-sync.
