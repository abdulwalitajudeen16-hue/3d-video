"""Voiceover analysis: speech/silence map and word timestamps.

Word timestamps come from (in order of preference):
  1. an imported transcript (SRT/VTT/JSON with word times)          -> source "imported"
  2. faster-whisper or openai-whisper, if installed                  -> source "asr"
  3. an ESTIMATE spread over detected speech segments                -> source "estimated"

"estimated" is NOT real alignment. Downstream code and QC treat it as lower confidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import ffutil
from .models import SpeechSegment, Timing, Word

_TOKEN = re.compile(r"[\w'’-]+|[.,!?;:]", re.UNICODE)


def tokenize_words(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text) if re.match(r"[\w]", t)]


def speech_segments_from_silences(silences: list[tuple[float, float]], duration: float) -> list[SpeechSegment]:
    segs, cur = [], 0.0
    for s, e in sorted(silences):
        if s - cur > 0.05:
            segs.append(SpeechSegment(round(cur, 3), round(s, 3)))
        cur = max(cur, e)
    if duration - cur > 0.05:
        segs.append(SpeechSegment(round(cur, 3), round(duration, 3)))
    return segs


def estimate_words(script_text: str, segments: list[SpeechSegment]) -> list[Word]:
    """Distribute script words across speech segments proportionally to character length."""
    words = tokenize_words(script_text)
    if not words or not segments:
        return []
    total_speech = sum(s.end - s.start for s in segments)
    total_chars = sum(len(w) + 1 for w in words)
    sec_per_char = total_speech / total_chars
    out: list[Word] = []
    seg_i, t = 0, segments[0].start
    for w in words:
        dur = (len(w) + 1) * sec_per_char
        while seg_i < len(segments) - 1 and t + dur > segments[seg_i].end + 1e-6:
            seg_i += 1
            t = segments[seg_i].start
        out.append(Word(w, round(t, 3), round(min(t + dur, segments[seg_i].end), 3), "estimated"))
        t += dur
    return out


def _ts(s: str) -> float:
    s = s.strip().replace(",", ".")
    parts = s.split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def import_words(path: str | Path) -> list[Word]:
    """Import word timings from JSON ([{text,start,end}] or whisper-style {segments:[{words:[...]}]}),
    or cue-level SRT/VTT (cues are split into words proportionally and marked 'imported')."""
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(raw)
        items = data if isinstance(data, list) else None
        if items is None and "words" in data:
            items = data["words"]
        if items is None and "segments" in data:
            items = [w for seg in data["segments"] for w in seg.get("words", [])]
        if not items:
            raise ValueError("no word-level entries found in JSON")
        return [Word((i.get("text") or i.get("word")).strip(), float(i["start"]), float(i["end"]), "imported") for i in items]
    words: list[Word] = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [l for l in block.splitlines() if l.strip() and l.strip() != "WEBVTT"]
        for i, l in enumerate(lines):
            if "-->" in l:
                a, b = [x.strip().split(" ")[0] for x in l.split("-->")]
                text = " ".join(lines[i + 1:])
                toks = tokenize_words(re.sub(r"<[^>]+>", "", text))
                if not toks:
                    break
                t0, t1 = _ts(a), _ts(b)
                step = (t1 - t0) / len(toks)
                words += [Word(w, round(t0 + k * step, 3), round(t0 + (k + 1) * step, 3), "imported") for k, w in enumerate(toks)]
                break
    if not words:
        raise ValueError("could not parse any cues")
    return words


def transcribe_with_asr(audio_path: str, language: str | None = None) -> list[Word] | None:
    """Word-level ASR if a supported library is installed; returns None otherwise (never fakes it)."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel("small", compute_type="int8")
        segs, _ = model.transcribe(audio_path, word_timestamps=True, language=language)
        return [Word(w.word.strip(), round(w.start, 3), round(w.end, 3), "asr") for s in segs for w in (s.words or [])]
    except ImportError:
        pass
    try:
        import whisper  # type: ignore
        model = whisper.load_model("small")
        res = model.transcribe(audio_path, word_timestamps=True, language=language)
        return [Word(w["word"].strip(), round(w["start"], 3), round(w["end"], 3), "asr")
                for s in res["segments"] for w in s.get("words", [])]
    except ImportError:
        return None


def analyse(audio_path: str, script_text: str = "", transcript_path: str | None = None,
            use_asr: bool = True, noise_db: float = -35.0, min_silence: float = 0.25,
            language: str | None = None) -> Timing:
    ffutil.require_binaries()
    duration = ffutil.audio_duration(audio_path)
    silences = ffutil.detect_silences(audio_path, noise_db, min_silence)
    speech = speech_segments_from_silences(silences, duration)
    words: list[Word] = []
    source = "none"
    if transcript_path:
        words, source = import_words(transcript_path), "imported"
    elif use_asr:
        asr = transcribe_with_asr(audio_path, language)
        if asr:
            words, source = asr, "asr"
    if not words and script_text:
        words, source = estimate_words(script_text, speech), "estimated"
    return Timing(
        audio_path=str(audio_path), duration=round(duration, 3),
        speech_segments=speech, silences=[SpeechSegment(round(a, 3), round(b, 3)) for a, b in silences],
        words=words, word_source=source,
    )


def nearest_silence_midpoint(t: float, silences: list[SpeechSegment], tolerance: float) -> float | None:
    best, best_d = None, tolerance
    for s in silences:
        mid = (s.start + s.end) / 2
        d = abs(mid - t)
        if d <= best_d:
            best, best_d = mid, d
    return best
