"""Video assembly: normalise scene clips, concatenate, mux the ORIGINAL voiceover, optional burned subtitles."""
from __future__ import annotations

import json
from pathlib import Path

from . import ffutil
from .models import ScenePlan

CONFIG = Path(__file__).resolve().parents[2] / "config" / "platforms.json"


def load_preset(name: str) -> dict:
    presets = json.loads(CONFIG.read_text(encoding="utf-8"))["presets"]
    if name not in presets:
        raise ValueError(f"unknown platform preset '{name}'. Choose from: {', '.join(presets)}")
    return presets[name]


def normalise_clip(src: str | Path, dst: str | Path, width: int, height: int, fps: int, duration: float) -> None:
    """Cover-scale + centre-crop to target, hold last frame if short, trim if long, drop clip audio."""
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
          f"fps={fps},tpad=stop_mode=clone:stop_duration={max(0.0, duration):.3f},setsar=1")
    ffutil.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-an", "-vf", vf,
                "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-pix_fmt", "yuv420p", str(dst)])


def assemble(plan: ScenePlan, clips: dict[int, str], voiceover: str, out_path: str | Path, work_dir: str | Path,
             preset: str = "vertical", subtitles_ass: str | None = None) -> dict:
    ffutil.require_binaries()
    pr = load_preset(preset)
    if pr["aspect"] != plan.aspect:
        raise ValueError(f"preset '{preset}' is {pr['aspect']} but the plan is {plan.aspect}")
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    norm = []
    for sc in plan.scenes:
        if sc.id not in clips:
            raise FileNotFoundError(f"no clip for scene {sc.id}")
        dst = work / f"norm_{sc.id:02d}.mp4"
        normalise_clip(clips[sc.id], dst, pr["width"], pr["height"], pr["fps"], sc.duration)
        norm.append(dst)
    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in norm), encoding="utf-8")
    silent = work / "assembled_silent.mp4"
    ffutil.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy", str(silent)])
    dur = ffutil.audio_duration(voiceover)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent), "-i", str(voiceover)]
    if subtitles_ass:
        esc = str(Path(subtitles_ass).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        cmd += ["-vf", f"ass='{esc}'", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-c:v", "copy"]
    cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}",
            "-movflags", "+faststart", str(out_path)]
    ffutil.run(cmd)
    return {"output": str(out_path), "preset": preset, "width": pr["width"], "height": pr["height"], "fps": pr["fps"],
            "duration": dur, "subtitles_burned": bool(subtitles_ass)}
