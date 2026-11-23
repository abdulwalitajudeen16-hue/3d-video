"""Mock provider for pipeline testing ONLY.

Produces a static still of the reference photo with the audio. It performs NO lip-sync and NO motion.
It tags the file's metadata so QC can recognise it and will mark lip-sync/motion checks as FAILED.
"""
from __future__ import annotations

from pathlib import Path

from .. import ffutil
from .base import Capabilities, Provider, SceneJob

MOCK_TAG = "YMM_MOCK_NOT_LIPSYNCED"

DIMS = {"9:16": (720, 1280), "16:9": (1280, 720)}


class Mock(Provider):
    capabilities = Capabilities(
        name="mock", lipsync=True, image_to_video=True, verified_live=True,
        notes="Static image + audio. Not lip-synced. For testing assembly/QC only.")

    def check_config(self) -> tuple[bool, str]:
        return True, "always available; output is NOT a real video generation"

    def generate(self, job: SceneJob) -> Path:
        w, h = DIMS[job.aspect]
        out = Path(job.out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", "30",
               "-i", job.image_path]
        if job.audio_path:
            cmd += ["-i", job.audio_path]
        cmd += ["-t", f"{job.duration:.3f}",
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30"]
        if job.audio_path:
            cmd += ["-c:a", "aac", "-shortest"]
        cmd += ["-metadata", f"comment={MOCK_TAG}", str(out)]
        ffutil.run(cmd)
        return out
