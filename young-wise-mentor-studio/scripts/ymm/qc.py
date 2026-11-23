"""Quality-control gate.

Statuses: PASS | FAIL | NEEDS_REVIEW | SKIPPED.
Automated code can measure dimensions, durations, A/V sync, black frames, stationary spans, plan
quality, and (only if a face library is installed) face similarity. It CANNOT judge photorealism,
lip-sync accuracy, gesture naturalness or emotional fit, so those are NEEDS_REVIEW with a review
sheet for a human, or FAIL when the evidence shows they cannot have passed (e.g. mock clips).
The overall verdict is never "PASSED" unless every check, including human ones, is PASS.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import ffutil, gestures
from .assemble import load_preset
from .models import ScenePlan, Timing, validate_plan
from .providers.mock import MOCK_TAG

PASS, FAIL, REVIEW, SKIP = "PASS", "FAIL", "NEEDS_REVIEW", "SKIPPED"


def _c(cid: str, name: str, status: str, detail: str) -> dict:
    return {"id": cid, "name": name, "status": status, "detail": detail}


def _overlap(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    """Intersection-over-union of two interval sets (seconds)."""
    def merge(x):
        out = []
        for s, e in sorted(x):
            if out and s <= out[-1][1]:
                out[-1][1] = max(out[-1][1], e)
            else:
                out.append([s, e])
        return out
    A, B = merge(a), merge(b)
    inter = sum(max(0.0, min(ae, be) - max(as_, bs)) for as_, ae in A for bs, be in B)
    total = sum(e - s for s, e in A) + sum(e - s for s, e in B) - inter
    return inter / total if total > 0 else 1.0


def face_similarity(reference: str, frame: str) -> float | None:
    """Cosine-like similarity in [0,1] (1 - distance) via `face_recognition` if installed, else None."""
    try:
        import face_recognition  # type: ignore
    except ImportError:
        return None
    ref = face_recognition.load_image_file(reference)
    img = face_recognition.load_image_file(frame)
    re_, ie = face_recognition.face_encodings(ref), face_recognition.face_encodings(img)
    if not re_ or not ie:
        return 0.0
    return float(1.0 - face_recognition.face_distance([re_[0]], ie[0])[0])


def make_review_sheet(video: str, reference: str, plan: ScenePlan, out_path: str, max_tiles: int = 12) -> str:
    from PIL import Image, ImageDraw
    tmp = Path(out_path).parent / "frames"
    tmp.mkdir(parents=True, exist_ok=True)
    vdur = ffutil.video_info(video)["duration"]
    tiles: list[tuple[str, Image.Image]] = [("REFERENCE", Image.open(reference).convert("RGB"))]
    times = []
    for sc in plan.scenes:
        times.append((f"s{sc.id} {sc.mode[:4]} mid", sc.start + sc.duration / 2))
        if sc.mode == "presenter" and sc.duration > 3:
            times.append((f"s{sc.id} late", sc.start + sc.duration * 0.8))
    step = max(1, len(times) // (max_tiles - 1) + (1 if len(times) % (max_tiles - 1) else 0))
    for label, t in times[::step][: max_tiles - 1]:
        f = tmp / f"f_{len(tiles)}.png"
        try:
            ffutil.extract_frame(video, f, min(t, max(0.0, vdur - 0.1)), width=360)
        except ffutil.FFmpegError:
            continue
        if not f.exists():
            continue
        tiles.append((f"{label} @{t:.1f}s", Image.open(f).convert("RGB")))
    th = 480
    resized = []
    for label, im in tiles:
        w = max(1, round(im.width * th / im.height))
        resized.append((label, im.resize((w, th))))
    cols = 4
    rows = [resized[i:i + cols] for i in range(0, len(resized), cols)]
    W = max(sum(im.width for _, im in r) for r in rows)
    sheet = Image.new("RGB", (W, (th + 24) * len(rows)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    y = 0
    for r in rows:
        x = 0
        for label, im in r:
            sheet.paste(im, (x, y + 24))
            d.text((x + 6, y + 6), label, fill=(255, 255, 255))
            x += im.width
        y += th + 24
    sheet.save(out_path, quality=88)
    return out_path


def run_qc(video: str, plan: ScenePlan, voiceover: str, preset: str, reference: str, provider_map: dict[int, str],
           clips: dict[int, str], timing: Timing | None = None, out_dir: str = ".", max_seconds: float | None = None,
           identity_threshold: float = 0.55) -> dict:
    ffutil.require_binaries()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    pr = load_preset(preset)
    vi = ffutil.video_info(video)
    vo_dur = ffutil.audio_duration(voiceover)

    # --- automated, measurable ---
    ok = vi.get("width") == pr["width"] and vi.get("height") == pr["height"]
    checks.append(_c("dimensions", "Video dimensions", PASS if ok else FAIL,
                     f"{vi.get('width')}x{vi.get('height')} (expected {pr['width']}x{pr['height']})"))
    d = abs(vi["duration"] - vo_dur)
    checks.append(_c("voiceover_duration", "Video length matches voiceover", PASS if d <= 0.15 else FAIL,
                     f"video {vi['duration']:.2f}s vs voiceover {vo_dur:.2f}s (Δ{d:.2f}s)"))
    if vi["has_audio"] and vi["has_video"]:
        dd = abs(vi["v_duration"] - vi["a_duration"])
        checks.append(_c("av_sync", "Audio/video stream sync", PASS if dd <= 0.1 else FAIL,
                         f"video stream {vi['v_duration']:.2f}s, audio stream {vi['a_duration']:.2f}s (Δ{dd:.2f}s)"))
        # voice in output equals the supplied voiceover
        src_sp = [(s.start, s.end) for s in _speech(voiceover)]
        out_sp = [(s.start, s.end) for s in _speech(video)]
        iou = _overlap(src_sp, out_sp)
        checks.append(_c("audio_is_voiceover", "Output audio is the supplied voiceover (speech map overlap)",
                         PASS if iou >= 0.95 else FAIL, f"speech/silence overlap {iou:.1%}"))
    else:
        checks.append(_c("av_sync", "Audio/video stream sync", FAIL, "output is missing an audio or video stream"))
    if max_seconds is not None:
        checks.append(_c("max_length", "Within requested max length", PASS if vi["duration"] <= max_seconds else FAIL,
                         f"{vi['duration']:.1f}s vs limit {max_seconds:.0f}s"))
    black = ffutil.detect_black(video)
    checks.append(_c("black_frames", "No unintended black frames", PASS if not black else FAIL,
                     "none" if not black else "black spans: " + ", ".join(f"{a:.1f}-{b:.1f}s" for a, b in black)))

    # --- plan quality ---
    probs = validate_plan(plan)
    checks.append(_c("plan_valid", "Scene plan covers the audio with no gaps/overlaps and no invented actions",
                     PASS if not probs else FAIL, "ok" if not probs else "; ".join(probs[:6])))
    mid_cut = [s.id for s in plan.scenes[:-1] if "not in a pause" in s.notes]
    checks.append(_c("cuts_in_pauses", "Scene cuts fall in pauses", PASS if not mid_cut else REVIEW,
                     "all internal cuts are in silences" if not mid_cut else f"scenes {mid_cut} end mid-speech; listen to those cuts"))
    if plan.word_source == "estimated":
        checks.append(_c("word_timing_quality", "Word timestamps are real alignment", REVIEW,
                         "timings were ESTIMATED from the script, not measured; lip-sync and subtitle timing are unverified. Provide a transcript or install an ASR library."))
    elif plan.word_source == "none":
        checks.append(_c("word_timing_quality", "Word timestamps are real alignment", FAIL, "no word timings at all"))
    else:
        checks.append(_c("word_timing_quality", "Word timestamps are real alignment", PASS, f"source: {plan.word_source}"))
    pres = [s for s in plan.scenes if s.mode == "presenter"]
    missing = [s.id for s in pres if not s.gesture_cues]
    rep = gestures.repetition_report(plan.scenes)
    bad_rep = rep["back_to_back_repeats"] > 0 or (rep["events"] >= 6 and rep["most_common_share"] > 0.5)
    checks.append(_c("gesture_plan", "Gesture plan present, varied, non-repetitive",
                     PASS if not missing and not bad_rep else FAIL,
                     f"{rep['events']} cues, {rep['distinct']} distinct, {rep['back_to_back_repeats']} back-to-back repeats"
                     + (f"; presenter scenes without gestures: {missing}" if missing else "")))

    # --- stationary check on presenter scenes (measured on the final render) ---
    freezes = ffutil.detect_freezes(video)
    worst = (0.0, None)
    for s in pres:
        fz = sum(max(0.0, min(e, s.end) - max(b, s.start)) for b, e in freezes)
        frac = fz / s.duration if s.duration else 0
        if frac > worst[0]:
            worst = (frac, s.id)
    checks.append(_c("not_stationary", "Presenter scenes are not frozen/stationary",
                     PASS if worst[0] <= 0.3 else FAIL,
                     f"max frozen share {worst[0]:.0%}" + (f" (scene {worst[1]})" if worst[1] else "")
                     + "; freeze detection is sensitive to small motion, so PASS is still a human-review item"))

    # --- provider honesty ---
    mock_scenes = [i for i, p in provider_map.items() if p == "mock"]
    for i, p in clips.items():
        try:
            tags = ffutil.probe(p)["format"].get("tags", {})
            if MOCK_TAG in str(tags.get("comment", "")) and i not in mock_scenes:
                mock_scenes.append(i)
        except Exception:
            pass
    if mock_scenes:
        checks.append(_c("real_generation", "Clips come from a real generation provider", FAIL,
                         f"scenes {sorted(mock_scenes)} are mock stills; this is a pipeline test, not a finished video"))
        checks.append(_c("lipsync", "Lip-sync aligned to speech", FAIL, "mock clips contain no lip-sync"))
    else:
        checks.append(_c("real_generation", "Clips come from a real generation provider", PASS,
                         ", ".join(sorted(set(provider_map.values()))) or "unknown"))
        checks.append(_c("lipsync", "Lip-sync aligned to speech", REVIEW if pres else SKIP,
                         "no automated verifier is bundled; watch each presenter scene at full speed against the audio"
                         if pres else "no on-camera speech in this video"))

    # --- identity ---
    sims = []
    tmp = out / "frames"
    tmp.mkdir(parents=True, exist_ok=True)
    for s in plan.scenes:
        if s.mode == "presenter":
            f = tmp / f"id_{s.id}.png"
            ffutil.extract_frame(video, f, min(s.start + s.duration / 2, max(0.0, vi["duration"] - 0.1)))
            sim = face_similarity(reference, str(f))
            if sim is None:
                sims = None
                break
            sims.append((s.id, sim))
    if sims is None:
        checks.append(_c("identity", "Character identity matches reference", REVIEW,
                         "no face-recognition library installed (`pip install face_recognition`); compare review_sheet.jpg to the reference by eye"))
    elif not sims:
        checks.append(_c("identity", "Character identity matches reference", REVIEW, "no presenter frames to measure; check storytelling scenes by eye"))
    else:
        low = [(i, round(v, 2)) for i, v in sims if v < identity_threshold]
        checks.append(_c("identity", "Character identity matches reference", FAIL if low else REVIEW,
                         (f"low similarity in scenes {low}" if low else f"min similarity {min(v for _, v in sims):.2f}; storytelling scenes still need an eye check")))

    # --- human-only judgements ---
    for cid, name in [("photorealism", "Photorealistic appearance (no cartoon/CGI/filter look)"),
                      ("body_movement", "Natural head/shoulder/posture movement"),
                      ("gesture_fit", "Gestures match meaning and emotion of narration"),
                      ("emotion", "Facial expression matches emotional tone"),
                      ("scene_relevance", "Storytelling actions match the narration")]:
        checks.append(_c(cid, name, REVIEW, "judged by a human using review_sheet.jpg and a full watch-through"))

    sheet = make_review_sheet(video, reference, plan, str(out / "review_sheet.jpg"))
    statuses = {c["status"] for c in checks}
    verdict = "FAILED" if FAIL in statuses else "NEEDS_HUMAN_REVIEW" if REVIEW in statuses else "PASSED"
    report = {"verdict": verdict, "video": video, "review_sheet": sheet, "checks": checks,
              "counts": {s: sum(1 for c in checks if c["status"] == s) for s in (PASS, FAIL, REVIEW, SKIP)}}
    (out / "qc_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "qc_report.md").write_text(render_md(report), encoding="utf-8")
    return report


def _speech(path: str):
    from .timing import speech_segments_from_silences
    dur = ffutil.video_info(path)["duration"] if ffutil.video_info(path)["has_video"] else ffutil.audio_duration(path)
    return speech_segments_from_silences(ffutil.detect_silences(path), dur)


def render_md(report: dict) -> str:
    icon = {PASS: "PASS", FAIL: "FAIL", REVIEW: "REVIEW", SKIP: "skip"}
    lines = [f"# QC report: {report['verdict']}", "", f"Video: `{report['video']}`  ",
             f"Review sheet: `{report['review_sheet']}`", "", "| Status | Check | Detail |", "|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {icon[c['status']]} | {c['name']} | {c['detail']} |")
    lines += ["", "FAIL = measured problem or proven impossible to pass. REVIEW = cannot be judged by code; a human must confirm.", ""]
    return "\n".join(lines)
