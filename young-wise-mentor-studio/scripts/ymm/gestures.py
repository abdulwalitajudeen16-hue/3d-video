"""Gesture and movement planning.

Gestures are chosen from the narration's meaning, not at random, and a repetition guard keeps
the same gesture from recurring back-to-back. A minimum motion density guarantees he never
sits stationary. Variation is deterministic (seeded by scene id) so plans are reproducible.
"""
from __future__ import annotations

import re
from typing import Iterable

from .lexicon import CONTRAST_WORDS, EMPHASIS_WORDS, ORDINALS
from .models import GestureCue, Scene, Word

# name -> (prompt phrase, family)
GESTURES: dict[str, tuple[str, str]] = {
    "open_palms": ("opens both palms outward, shoulders relaxed", "both"),
    "one_hand_explain": ("explains with one hand, palm up, small circular motion", "one"),
    "two_hand_frame": ("brings both hands together in front of him, framing an idea", "both"),
    "point_to_camera": ("points toward the camera with his index finger on the key word", "one"),
    "count_fingers": ("counts on his fingers as he lists points", "one"),
    "closed_fist": ("closes his hand into a firm fist for emphasis", "one"),
    "hand_to_chest": ("places a hand on his chest, sincere", "one"),
    "palm_down_calm": ("lowers a flat palm slowly, calming gesture", "one"),
    "chop_emphasis": ("makes a short downward chop with one hand", "one"),
    "spread_hands": ("spreads both hands wide to show scale or contrast", "both"),
    "lean_forward": ("leans slightly toward the camera", "body"),
    "head_nod": ("gives a subtle confirming nod", "head"),
    "shoulder_settle": ("shoulders rise and settle with a breath", "body"),
    "posture_shift": ("shifts weight and resets posture", "body"),
    "head_tilt": ("tilts his head slightly, considering", "head"),
}

# Each rule: (predicate on lowercase words list, gesture, reason)
def _has(ws: list[str], vocab: Iterable[str]) -> str | None:
    vs = set(vocab)
    for w in ws:
        if w in vs:
            return w
    return None


def _candidates(narration: str, emotion: str) -> list[tuple[str, str, float]]:
    """Return (gesture, trigger, intensity) candidates ranked by relevance."""
    ws = re.findall(r"[\w']+", narration.lower())
    cands: list[tuple[str, str, float]] = []
    if (w := _has(ws, ORDINALS)) and w in ("first", "second", "third", "fourth"):
        cands.append(("count_fingers", w, 0.5))
    if (w := _has(ws, {"you", "your", "yours"})) and ("?" in narration or emotion in ("urgent", "curious")):
        cands.append(("point_to_camera", w, 0.7))
    if (w := _has(ws, EMPHASIS_WORDS)):
        cands.append(("chop_emphasis" if emotion in ("frustrated", "urgent") else "closed_fist", w, 0.8))
    if (w := _has(ws, CONTRAST_WORDS)):
        cands.append(("spread_hands", w, 0.6))
    if (w := _has(ws, {"imagine", "picture", "think", "idea", "concept", "system", "framework"})):
        cands.append(("two_hand_frame", w, 0.5))
    if (w := _has(ws, {"i", "my", "honestly", "truth", "believe", "trust"})) and emotion in ("sad", "hopeful", "proud", "neutral"):
        cands.append(("hand_to_chest", w, 0.4))
    if (w := _has(ws, {"breathe", "slow", "calm", "patient", "steady", "relax", "quiet"})):
        cands.append(("palm_down_calm", w, 0.4))
    if (w := _has(ws, {"everyone", "everything", "all", "world", "everywhere", "open", "possible"})):
        cands.append(("open_palms", w, 0.6))
    if "?" in narration:
        cands.append(("head_tilt", "?", 0.4))
    if emotion in ("urgent", "frustrated"):
        cands.append(("lean_forward", emotion, 0.6))
    if emotion in ("sad", "calm"):
        cands.append(("shoulder_settle", emotion, 0.3))
    return cands


FALLBACK_CYCLE = ["one_hand_explain", "open_palms", "head_nod", "two_hand_frame", "shoulder_settle", "posture_shift"]


def plan_gestures(scenes: list[Scene], words: list[Word] | None = None, min_events_per_10s: float = 3.0) -> None:
    """Mutates scenes: fills gesture_cues, hands, body. Enforces variety and motion density."""
    recent: list[str] = []
    fallback_i = 0
    for sc in scenes:
        n_target = max(1, round(sc.duration / 10.0 * min_events_per_10s))
        cues: list[GestureCue] = []
        scene_words = [w for w in (words or []) if sc.start - 1e-6 <= w.start < sc.end]
        cands = _candidates(sc.narration, sc.emotion)
        used_in_scene: set[str] = set()
        for g, trig, inten in cands:
            if len(cues) >= n_target:
                break
            if g in used_in_scene or (recent and recent[-1] == g):
                continue
            # time the cue at the trigger word when we have timestamps, else proportionally
            at = None
            for w in scene_words:
                if w.text.lower().strip(".,!?;:") == trig:
                    at = w.start - sc.start
                    break
            if at is None:
                idx = sc.narration.lower().find(trig.lower()) if trig != "?" else len(sc.narration) - 1
                frac = max(0.0, idx) / max(1, len(sc.narration))
                at = frac * sc.duration
            cues.append(GestureCue(g, round(max(0.0, min(at, sc.duration - 0.2)), 2), trig, inten))
            used_in_scene.add(g)
            recent.append(g)
        # top up with unobtrusive fallbacks so he is never static
        while len(cues) < n_target:
            g = FALLBACK_CYCLE[(fallback_i + sc.id) % len(FALLBACK_CYCLE)]
            fallback_i += 1
            if g in used_in_scene or (recent and recent[-1] == g):
                continue
            at = (len(cues) + 0.5) / (n_target + 0.5) * sc.duration
            cues.append(GestureCue(g, round(at, 2), "(rhythm)", 0.3))
            used_in_scene.add(g)
            recent.append(g)
        cues.sort(key=lambda c: c.at)
        sc.gesture_cues = cues
        recent = recent[-4:]
        hands = [GESTURES[c.gesture][0] for c in cues if GESTURES[c.gesture][1] in ("one", "both")]
        body = [GESTURES[c.gesture][0] for c in cues if GESTURES[c.gesture][1] in ("body", "head")]
        if sc.mode == "storytelling":
            # keep acted-scene body language from the action itself; gestures stay minimal
            sc.hands = sc.hands or "hands occupied by the action"
            sc.body = sc.body or "; ".join(body[:2])
        else:
            sc.hands = "; ".join(hands[:3]) or "relaxed, hands low in frame"
            sc.body = "; ".join(body[:2]) or "slight natural sway"


def repetition_report(scenes: list[Scene]) -> dict:
    seq = [c.gesture for s in scenes for c in s.gesture_cues]
    back_to_back = sum(1 for a, b in zip(seq, seq[1:]) if a == b)
    distinct = len(set(seq))
    return {"events": len(seq), "distinct": distinct, "back_to_back_repeats": back_to_back,
            "most_common_share": (max((seq.count(g) for g in set(seq)), default=0) / len(seq)) if seq else 0.0}
