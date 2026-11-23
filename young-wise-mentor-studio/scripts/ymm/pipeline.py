"""Orchestration: plan -> clips -> assemble -> QC. Resumable; never hides failures."""
from __future__ import annotations

import json
from pathlib import Path

from . import ffutil
from .models import ScenePlan, Timing
from .providers import ManualStepRequired, Provider, ProviderError, SceneJob

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REFERENCE = PLUGIN_ROOT / "assets" / "mentor-reference.jpg"


def reference_for_aspect(aspect: str, work: str | Path) -> Path:
    """Reference image to send to providers. 9:16 -> the original photo, untouched.
    16:9 -> approved derived wide reference if present, else an unedited face-centred crop of the original."""
    if aspect == "9:16":
        return REFERENCE
    derived = PLUGIN_ROOT / "assets" / "derived" / "mentor-reference-16x9.jpg"
    if derived.exists():
        return derived
    from PIL import Image
    prof = json.loads((PLUGIN_ROOT / "assets" / "character-profile.json").read_text())
    frac = prof["landscape_reference"]["crop_y_center_frac"]
    im = Image.open(REFERENCE).convert("RGB")
    w, h = im.size
    ch = round(w * 9 / 16)
    top = max(0, min(h - ch, round(frac * h - ch / 2)))
    out = Path(work) / "reference_16x9_crop.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.crop((0, top, w, top + ch)).save(out, quality=95)
    return out


def clip_path(work: Path, scene_id: int) -> Path:
    return work / "clips" / f"scene_{scene_id:02d}.mp4"


def generate_clips(plan: ScenePlan, voiceover: str, work: str | Path, presenter_provider: Provider,
                   story_provider: Provider | None = None, resolution: str = "720p",
                   reference: str | Path | None = None, only: list[int] | None = None) -> dict:
    """Returns manifest {scene_id: {provider, clip, status, error}}. status: done | pending_manual | failed | skipped."""
    work = Path(work)
    (work / "audio").mkdir(parents=True, exist_ok=True)
    reference = reference or reference_for_aspect(plan.aspect, work)
    story_provider = story_provider or presenter_provider
    manifest: dict[int, dict] = {}
    for sc in plan.scenes:
        if only and sc.id not in only:
            continue
        prov = presenter_provider if sc.mode == "presenter" else story_provider
        out = clip_path(work, sc.id)
        entry = {"provider": prov.capabilities.name, "clip": str(out), "status": "failed", "error": ""}
        manifest[sc.id] = entry
        if out.exists() and out.stat().st_size > 0:
            entry["status"] = "done"
            entry["note"] = "reused existing clip"
            continue
        audio = None
        if sc.mode == "presenter":
            if not prov.capabilities.lipsync:
                entry["error"] = f"provider {prov.capabilities.name} has no lip-sync capability; refusing to fake it"
                continue
            audio = str(work / "audio" / f"scene_{sc.id:02d}.wav")
            ffutil.cut_audio(voiceover, audio, sc.start, sc.end)
        elif not prov.capabilities.image_to_video:
            entry["error"] = (f"provider {prov.capabilities.name} cannot make acted storytelling shots "
                              "(no image-to-video). Configure a storytelling provider or use manual.")
            continue
        job = SceneJob(scene_id=sc.id, mode=sc.mode, image_path=str(reference), prompt=sc.prompt, aspect=plan.aspect,
                       duration=sc.duration, out_path=str(out), audio_path=audio, resolution=resolution)
        try:
            prov.generate(job)
            entry["status"] = "done"
        except ManualStepRequired as e:
            entry["status"], entry["error"] = "pending_manual", str(e)
        except ProviderError as e:
            entry["error"] = str(e)
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def clips_from_manifest(manifest: dict) -> dict[int, str]:
    return {int(i): e["clip"] for i, e in manifest.items() if e["status"] == "done"}
