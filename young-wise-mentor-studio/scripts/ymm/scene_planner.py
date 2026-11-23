"""Deterministic baseline scene planner. Claude refines the result; validate_plan() polices it."""
from __future__ import annotations

from . import gestures as gest
from .lexicon import STORY_ACTIONS
from .models import Scene, ScenePlan, Timing, Word, validate_plan
from .prompts import build_prompt
from .script_analysis import Beat, analyse_script
from .timing import nearest_silence_midpoint, tokenize_words

PRESENTER_CAMERAS_VERTICAL = [
    ("medium close-up, eye level", "slow push-in"),
    ("close-up, eye level", "subtle handheld drift"),
    ("medium shot, slightly low angle", "very slow pull-back"),
    ("medium close-up, eye level", "static with slight breathing drift"),
]
PRESENTER_CAMERAS_LANDSCAPE = [
    ("medium shot, eye level, rule-of-thirds left", "slow push-in"),
    ("medium close-up, eye level", "slow lateral slide"),
    ("medium shot, slightly low angle", "slow pull-back"),
    ("close-up, eye level", "static with slight breathing drift"),
]


def _beat_times(beats: list[Beat], timing: Timing) -> list[tuple[float, float]]:
    """Map each beat to (start, end) seconds using word timestamps, else character proportion."""
    total_dur = timing.duration
    if timing.words:
        words = timing.words
        counts = [max(1, len(tokenize_words(b.text))) for b in beats]
        total = sum(counts)
        out, cum = [], 0
        for c in counts:
            a = min(len(words) - 1, round(cum / total * len(words)))
            b = min(len(words) - 1, max(a, round((cum + c) / total * len(words)) - 1))
            out.append((words[a].start, words[b].end))
            cum += c
        # make contiguous: beat i ends where beat i+1 starts' midpoint of the gap
        res = []
        for i, (s, e) in enumerate(out):
            nxt = out[i + 1][0] if i + 1 < len(out) else total_dur
            res.append((s if i else 0.0, (e + nxt) / 2 if i + 1 < len(out) else total_dur))
        return res
    chars = [len(b.text) for b in beats]
    tc = sum(chars)
    out, t = [], 0.0
    for c in chars:
        d = c / tc * total_dur
        out.append((t, t + d))
        t += d
    return out


def plan_scenes(script_text: str, timing: Timing, aspect: str = "9:16", title: str = "Untitled",
                min_scene_s: float = 4.0, max_presenter_s: float = 25.0, max_story_s: float = 12.0,
                snap_tolerance_s: float = 0.7) -> ScenePlan:
    if aspect not in ("9:16", "16:9"):
        raise ValueError("aspect must be 9:16 or 16:9")
    beats = analyse_script(script_text)
    if not beats:
        raise ValueError("script is empty")
    times = _beat_times(beats, timing)

    # 1) group consecutive beats of the same mode/action
    groups: list[list[int]] = []
    for i, b in enumerate(beats):
        mode_key = ("story", b.story_action) if b.story_action else ("pres", None)
        if groups:
            last = groups[-1][-1]
            lb = beats[last]
            lkey = ("story", lb.story_action) if lb.story_action else ("pres", None)
            span = times[i][1] - times[groups[-1][0]][0]
            cap = max_story_s if mode_key[0] == "story" else max_presenter_s
            if lkey == mode_key and span <= cap:
                groups[-1].append(i)
                continue
            # absorb a too-short group into its neighbour when same mode
            lspan = times[last][1] - times[groups[-1][0]][0]
            if lspan < min_scene_s and lkey[0] == mode_key[0] and span <= cap:
                groups[-1].append(i)
                continue
        groups.append([i])

    # 2) build scenes
    scenes: list[Scene] = []
    for gi, g in enumerate(groups):
        first, last = beats[g[0]], beats[g[-1]]
        narration = " ".join(beats[i].text for i in g)
        start, end = times[g[0]][0], times[g[-1]][1]
        # dominant emotion in group
        emos = [beats[i].emotion for i in g if beats[i].emotion != "neutral"]
        emotion = max(set(emos), key=emos.count) if emos else "neutral"
        expr = next((beats[i].expression for i in g if beats[i].emotion == emotion), "calm, attentive")
        sc = Scene(id=gi + 1, narration=narration, start=round(start, 3), end=round(end, 3), emotion=emotion, expression=expr)
        story = next((beats[i] for i in g if beats[i].story_action), None)
        if story:
            spec = STORY_ACTIONS[story.story_action]
            sc.mode, sc.needs_lipsync = "storytelling", False
            sc.action, sc.action_trigger = spec["action"], story.story_trigger
            sc.environment, sc.expression, sc.body = spec["environment"], spec["expression"], spec["body"]
            sc.camera_angle, sc.camera_movement = spec["camera"]
            sc.notes = "Narration is voice-over; he is not speaking on camera in this scene."
        else:
            cams = PRESENTER_CAMERAS_VERTICAL if aspect == "9:16" else PRESENTER_CAMERAS_LANDSCAPE
            pres_index = sum(1 for s in scenes if s.mode == "presenter")
            sc.camera_angle, sc.camera_movement = cams[pres_index % len(cams)]
        scenes.append(sc)

    # 3) snap internal boundaries into pauses so cuts never land mid-word
    for a, b in zip(scenes, scenes[1:]):
        snapped = nearest_silence_midpoint(a.end, timing.silences, snap_tolerance_s)
        mid = snapped if snapped is not None else a.end
        a.end = b.start = round(mid, 3)
        if snapped is None:
            a.notes = (a.notes + " Boundary not in a pause; cut may fall mid-speech.").strip()
    scenes[0].start = 0.0
    scenes[-1].end = round(timing.duration, 3)

    # 4) gestures, then prompts
    gest.plan_gestures(scenes, timing.words)
    for sc in scenes:
        sc.prompt = build_prompt(sc, aspect)

    plan = ScenePlan(title=title, aspect=aspect, scenes=scenes, audio_path=timing.audio_path,
                     audio_duration=timing.duration, word_source=timing.word_source)
    return plan


def plan_problems(plan: ScenePlan) -> list[str]:
    return validate_plan(plan)
