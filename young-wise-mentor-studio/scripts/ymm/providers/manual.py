"""Manual hand-off: writes a self-contained job folder so any web tool/API console can be used by hand.

Workflow: `generate` writes <out_dir>/jobs/scene_NN/{reference.jpg, audio.wav, prompt.txt, job.json, README.txt}
and raises ManualStepRequired. After generating the clip elsewhere, save it as
<out_dir>/clips/scene_NN.mp4 and re-run; the pipeline picks up existing clips and carries on.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .base import Capabilities, ManualStepRequired, Provider, SceneJob


class Manual(Provider):
    capabilities = Capabilities(
        name="manual", lipsync=True, image_to_video=True, verified_live=False,
        notes="No automation. Quality depends on the tool you use by hand.")

    def check_config(self) -> tuple[bool, str]:
        return True, "no credentials needed; produces job folders for hand processing"

    def generate(self, job: SceneJob) -> Path:
        out = Path(job.out_path)
        if out.exists():
            return out
        jdir = out.parent.parent / "jobs" / f"scene_{job.scene_id:02d}"
        jdir.mkdir(parents=True, exist_ok=True)
        shutil.copy(job.image_path, jdir / "reference.jpg")
        if job.audio_path:
            shutil.copy(job.audio_path, jdir / "audio.wav")
        (jdir / "prompt.txt").write_text(job.prompt, encoding="utf-8")
        (jdir / "job.json").write_text(json.dumps({
            "scene_id": job.scene_id, "mode": job.mode, "aspect": job.aspect, "duration_seconds": job.duration,
            "needs_audio_driven_lipsync": bool(job.audio_path), "save_result_as": str(out)}, indent=2))
        (jdir / "README.txt").write_text(
            f"Scene {job.scene_id} ({job.mode}, {job.duration:.2f}s, {job.aspect})\n"
            f"1. Upload reference.jpg{' and audio.wav' if job.audio_path else ''} to your video tool.\n"
            f"2. Paste prompt.txt as the prompt (if the tool accepts one).\n"
            f"3. Export the clip and save it exactly as:\n   {out}\n"
            f"4. Re-run the pipeline.\n"
            f"Do not accept results where his face, hair, skin tone or hoodie changed, or where he looks cartoon/CGI.\n")
        raise ManualStepRequired(f"job package written to {jdir}; save the result as {out}")
