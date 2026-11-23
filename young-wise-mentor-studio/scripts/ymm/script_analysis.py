"""Script analysis: split a script into beats and tag each with emotion and storytelling triggers."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lexicon import EMOTIONS, PRESENTER_CUES, STORY_ACTIONS, STORY_CUES


@dataclass
class Beat:
    index: int
    text: str
    emotion: str = "neutral"
    expression: str = "calm, attentive"
    story_action: str | None = None   # key into STORY_ACTIONS
    story_trigger: str = ""           # exact narration words that matched
    presenter_cue: bool = False
    is_question: bool = False
    words: int = 0
    notes: list[str] = field(default_factory=list)


_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“'‘(])")


def split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(para.split())
        if para:
            out += [s.strip() for s in _SENT.split(para) if s.strip()]
    return out


def classify_emotion(text: str) -> tuple[str, str]:
    scores = {}
    for name, (pat, _expr) in EMOTIONS.items():
        n = len(re.findall(pat, text, flags=re.I))
        if n:
            scores[name] = n
    if not scores:
        return "neutral", "calm, attentive"
    best = max(scores, key=lambda k: (scores[k], k))
    return best, EMOTIONS[best][1]


def find_story_action(text: str) -> tuple[str | None, str]:
    for key, spec in STORY_ACTIONS.items():
        for pat in spec["triggers"]:
            m = re.search(pat, text, flags=re.I)
            if m:
                return key, m.group(0)
    return None, ""


def analyse_script(text: str) -> list[Beat]:
    beats: list[Beat] = []
    for i, sent in enumerate(split_sentences(text)):
        emo, expr = classify_emotion(sent)
        key, trig = find_story_action(sent)
        beats.append(Beat(
            index=i, text=sent, emotion=emo, expression=expr, story_action=key, story_trigger=trig,
            presenter_cue=bool(re.search(PRESENTER_CUES, sent, flags=re.I)),
            is_question=sent.rstrip().endswith("?"), words=len(sent.split()),
        ))
        if re.search(STORY_CUES, sent, flags=re.I) and key is None:
            beats[-1].notes.append("story cue present but no recognised action; kept as presenter")
    return beats
