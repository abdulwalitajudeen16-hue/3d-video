"""Subtitles from word timings (SRT + styled ASS for burn-in)."""
from __future__ import annotations

from pathlib import Path

from .models import Word


def group_words(words: list[Word], max_chars: int = 28, max_lines: int = 2, max_dur: float = 3.5,
                min_dur: float = 0.5) -> list[tuple[float, float, str]]:
    cues: list[tuple[float, float, str]] = []
    cur: list[Word] = []
    def flush():
        if not cur:
            return
        text, lines, line = [], [], ""
        for w in cur:
            if line and len(line) + 1 + len(w.text) > max_chars:
                lines.append(line)
                line = w.text
            else:
                line = f"{line} {w.text}".strip()
        lines.append(line)
        start, end = cur[0].start, cur[-1].end
        if end - start < min_dur:
            end = start + min_dur
        cues.append((start, end, "\n".join(lines)))
        cur.clear()
    for w in words:
        trial = cur + [w]
        chars = sum(len(x.text) + 1 for x in trial)
        if cur and (chars > max_chars * max_lines or w.end - cur[0].start > max_dur
                    or cur[-1].text.endswith((".", "!", "?"))):
            flush()
        cur.append(w)
    flush()
    # avoid overlaps
    for i in range(len(cues) - 1):
        s, e, t = cues[i]
        if e > cues[i + 1][0]:
            cues[i] = (s, cues[i + 1][0], t)
    return cues


def _srt_ts(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _ass_ts(t: float) -> str:
    cs = round(t * 100)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def write_srt(cues, path: str | Path) -> None:
    out = [f"{i}\n{_srt_ts(a)} --> {_srt_ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)]
    Path(path).write_text("\n".join(out), encoding="utf-8")


def write_ass(cues, path: str | Path, width: int, height: int, bottom_margin_pct: float = 22.0,
              font: str = "Inter", font_size_pct: float = 4.2) -> None:
    fs = round(height * font_size_pct / 100)
    mv = round(height * bottom_margin_pct / 100)
    head = (
        "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
        f"PlayResX: {width}\nPlayResY: {height}\n\n[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
        "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Default,{font},{fs},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{max(2, fs // 14)},0,2,"
        f"{round(width * 0.06)},{round(width * 0.06)},{mv},1\n\n[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    lines = [f"Dialogue: 0,{_ass_ts(a)},{_ass_ts(b)},Default,,0,0,0,,{t.replace(chr(10), chr(92) + 'N')}" for a, b, t in cues]
    Path(path).write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
