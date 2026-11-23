"""Thin, tested wrappers around ffmpeg/ffprobe. No other module shells out directly."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def require_binaries() -> None:
    missing = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    if missing:
        raise FFmpegError(f"missing required binaries: {', '.join(missing)}")


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise FFmpegError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p


def probe(path: str | Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(p.stdout)


def video_info(path: str | Path) -> dict:
    info = probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    out = {
        "duration": float(info["format"].get("duration", 0) or 0),
        "has_video": v is not None,
        "has_audio": a is not None,
    }
    if v:
        out.update(width=int(v["width"]), height=int(v["height"]), v_duration=float(v.get("duration", out["duration"]) or 0))
        num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
        out["fps"] = round(float(num) / float(den or 1), 3) if float(den or 1) else 0.0
    if a:
        out.update(a_duration=float(a.get("duration", out["duration"]) or 0), sample_rate=int(a.get("sample_rate", 0)))
    return out


def audio_duration(path: str | Path) -> float:
    return float(probe(path)["format"]["duration"])


_SIL_START = re.compile(r"silence_start: (-?[0-9.]+)")
_SIL_END = re.compile(r"silence_end: (-?[0-9.]+)")


def detect_silences(path: str | Path, noise_db: float = -35.0, min_len: float = 0.25) -> list[tuple[float, float]]:
    """Silence intervals via ffmpeg silencedetect. Trailing silence is closed at file duration."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
             f"silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"])
    total = audio_duration(path)
    out: list[tuple[float, float]] = []
    cur = None
    for line in p.stderr.splitlines():
        m = _SIL_START.search(line)
        if m:
            cur = max(0.0, float(m.group(1)))
            continue
        m = _SIL_END.search(line)
        if m and cur is not None:
            out.append((cur, min(total, float(m.group(1)))))
            cur = None
    if cur is not None:
        out.append((cur, total))
    return out


def cut_audio(src: str | Path, dst: str | Path, start: float, end: float, sample_rate: int = 44100) -> None:
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
         "-i", str(src), "-vn", "-ac", "1", "-ar", str(sample_rate), str(dst)])


_FREEZE_START = re.compile(r"freeze_start: ([0-9.]+)")
_FREEZE_END = re.compile(r"freeze_end: ([0-9.]+)")


def detect_freezes(path: str | Path, noise_db: float = -50.0, min_len: float = 1.5) -> list[tuple[float, float]]:
    """Spans where the picture is (near-)static. Used as a 'he must not stay stationary' check."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf",
             f"freezedetect=n={noise_db}dB:d={min_len}", "-f", "null", "-"])
    total = video_info(path)["duration"]
    spans, cur = [], None
    for line in p.stderr.splitlines():
        m = _FREEZE_START.search(line)
        if m:
            cur = float(m.group(1))
            continue
        m = _FREEZE_END.search(line)
        if m and cur is not None:
            spans.append((cur, float(m.group(1))))
            cur = None
    if cur is not None:
        spans.append((cur, total))
    return spans


_BLACK = re.compile(r"black_start:([0-9.]+) black_end:([0-9.]+)")


def detect_black(path: str | Path, min_len: float = 0.3) -> list[tuple[float, float]]:
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf",
             f"blackdetect=d={min_len}:pix_th=0.05", "-f", "null", "-"])
    return [(float(a), float(b)) for a, b in _BLACK.findall(p.stderr)]


def extract_frame(src: str | Path, dst: str | Path, t: float, width: int | None = None) -> None:
    vf = ["-vf", f"scale={width}:-2"] if width else []
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(src),
         "-frames:v", "1", *vf, str(dst)])
