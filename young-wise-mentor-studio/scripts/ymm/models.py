"""Data models shared by every pipeline stage. Plain dataclasses, JSON-serialisable."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

MODES = ("presenter", "storytelling")


@dataclass
class Word:
    text: str
    start: float
    end: float
    source: str = "unknown"  # "asr", "imported", "estimated"


@dataclass
class SpeechSegment:
    start: float
    end: float


@dataclass
class Timing:
    audio_path: str
    duration: float
    speech_segments: list[SpeechSegment]
    silences: list[SpeechSegment]
    words: list[Word]
    word_source: str  # "asr" | "imported" | "estimated" | "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Timing":
        return cls(
            audio_path=d["audio_path"],
            duration=d["duration"],
            speech_segments=[SpeechSegment(**s) for s in d["speech_segments"]],
            silences=[SpeechSegment(**s) for s in d["silences"]],
            words=[Word(**w) for w in d["words"]],
            word_source=d["word_source"],
        )


@dataclass
class GestureCue:
    gesture: str
    at: float  # seconds from scene start
    trigger: str  # narration words that justify the gesture
    intensity: float = 0.5


@dataclass
class Scene:
    id: int
    narration: str
    start: float = 0.0
    end: float = 0.0
    mode: str = "presenter"
    needs_lipsync: bool = True
    action: str = "speaks directly to camera"
    action_trigger: str = ""  # narration words that justify a storytelling action
    expression: str = "calm, attentive"
    hands: str = ""
    body: str = ""
    environment: str = "dim studio, bookshelf and plant behind him"
    camera_angle: str = "medium close-up, eye level"
    camera_movement: str = "slow push-in"
    emotion: str = "neutral"
    gesture_cues: list[GestureCue] = field(default_factory=list)
    prompt: str = ""
    notes: str = ""

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["duration"] = self.duration
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Scene":
        d = dict(d)
        d.pop("duration", None)
        cues = [GestureCue(**c) for c in d.pop("gesture_cues", [])]
        return cls(gesture_cues=cues, **d)


@dataclass
class ScenePlan:
    title: str
    aspect: str  # "9:16" | "16:9"
    scenes: list[Scene]
    audio_path: str = ""
    audio_duration: float = 0.0
    word_source: str = "none"
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "title": self.title,
            "aspect": self.aspect,
            "audio_path": self.audio_path,
            "audio_duration": self.audio_duration,
            "word_source": self.word_source,
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScenePlan":
        return cls(
            title=d["title"],
            aspect=d["aspect"],
            audio_path=d.get("audio_path", ""),
            audio_duration=d.get("audio_duration", 0.0),
            word_source=d.get("word_source", "none"),
            version=d.get("version", 1),
            scenes=[Scene.from_dict(s) for s in d["scenes"]],
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ScenePlan":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def validate_plan(plan: ScenePlan, tolerance: float = 0.05) -> list[str]:
    """Return a list of human-readable problems. Empty list means the plan is structurally sound."""
    problems: list[str] = []
    if plan.aspect not in ("9:16", "16:9"):
        problems.append(f"aspect must be 9:16 or 16:9, got {plan.aspect!r}")
    if not plan.scenes:
        problems.append("plan has no scenes")
        return problems
    prev_end = None
    for s in plan.scenes:
        tag = f"scene {s.id}"
        if s.mode not in MODES:
            problems.append(f"{tag}: mode must be one of {MODES}, got {s.mode!r}")
        if s.end <= s.start:
            problems.append(f"{tag}: end ({s.end}) must be after start ({s.start})")
        if not s.narration.strip():
            problems.append(f"{tag}: empty narration")
        if s.mode == "storytelling" and not s.action_trigger.strip():
            problems.append(
                f"{tag}: storytelling action {s.action!r} has no action_trigger; "
                "actions must be justified by words in the narration (no invented visuals)"
            )
        if s.action_trigger and s.action_trigger.lower() not in s.narration.lower():
            problems.append(f"{tag}: action_trigger {s.action_trigger!r} not found in narration")
        if prev_end is not None:
            gap = s.start - prev_end
            if gap > tolerance:
                problems.append(f"{tag}: {gap:.2f}s gap after previous scene")
            if gap < -tolerance:
                problems.append(f"{tag}: overlaps previous scene by {-gap:.2f}s")
        prev_end = s.end
    ids = [s.id for s in plan.scenes]
    if len(set(ids)) != len(ids):
        problems.append("duplicate scene ids")
    if plan.audio_duration and abs(plan.scenes[-1].end - plan.audio_duration) > 0.25:
        problems.append(
            f"scenes end at {plan.scenes[-1].end:.2f}s but audio is {plan.audio_duration:.2f}s"
        )
    return problems
