#!/usr/bin/env python3
"""Young Wise Mentor Studio command line.

  ymm_cli.py doctor
  ymm_cli.py timing   --audio vo.wav [--script script.txt] [--transcript words.json|.srt|.vtt] --out timing.json
  ymm_cli.py plan     --script script.txt --timing timing.json --aspect 9:16 --title "..." --out plan.json
  ymm_cli.py validate --plan plan.json
  ymm_cli.py generate --plan plan.json --audio vo.wav --work work/ --provider fal-omnihuman [--story-provider NAME]
  ymm_cli.py assemble --plan plan.json --audio vo.wav --work work/ --preset youtube-shorts --out final.mp4 [--subtitles --timing timing.json]
  ymm_cli.py qc       --plan plan.json --audio vo.wav --work work/ --video final.mp4 --preset youtube-shorts
  ymm_cli.py run      (timing + plan + generate + assemble + qc in one go)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ymm import assemble, ffutil, pipeline, qc, scene_planner, subtitles, timing as timing_mod  # noqa: E402
from ymm.models import ScenePlan, Timing, validate_plan  # noqa: E402
from ymm.providers import ProviderError, describe_all, load_provider  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_CFG = str(ROOT / "config" / "providers.json")


def cmd_doctor(a):
    print("Young Wise Mentor Studio: environment check\n")
    for b in ("ffmpeg", "ffprobe"):
        print(f"  {b:8} {'OK' if shutil.which(b) else 'MISSING (required)'}")
    ref = pipeline.REFERENCE
    print(f"  reference photo  {'OK' if ref.exists() else 'MISSING'}  {ref}")
    for mod, why in (("requests", "provider HTTP calls (required for real providers)"), ("PIL", "QC review sheet (required)"),
                     ("faster_whisper", "word-level ASR (optional)"), ("whisper", "word-level ASR alternative (optional)"),
                     ("face_recognition", "automated identity check (optional)")):
        try:
            __import__(mod)
            print(f"  {mod:16} OK        {why}")
        except ImportError:
            print(f"  {mod:16} not installed  {why}")
    print("\nProviders:")
    for r in describe_all(PROVIDERS_CFG):
        print(f"  {r['name']:16} ready={r['ready']!s:5} lipsync={r['lipsync']!s:5} image_to_video={r['image_to_video']!s:5} "
              f"verified_live={r['verified_live']}\n                   {r['detail']}")
    print("\nNo real generation provider is ready until its credentials are set. See docs/PROVIDERS.md.")


def cmd_timing(a):
    t = timing_mod.analyse(a.audio, Path(a.script).read_text() if a.script else "", a.transcript, use_asr=not a.no_asr)
    Path(a.out).write_text(json.dumps(t.to_dict(), indent=2))
    print(f"duration {t.duration:.2f}s, {len(t.speech_segments)} speech segments, {len(t.silences)} pauses, "
          f"{len(t.words)} words (source: {t.word_source})")
    if t.word_source == "estimated":
        print("WARNING: word times are ESTIMATED, not measured. Supply --transcript or install faster-whisper for real alignment.")


def cmd_plan(a):
    t = Timing.from_dict(json.loads(Path(a.timing).read_text()))
    plan = scene_planner.plan_scenes(Path(a.script).read_text(), t, a.aspect, a.title, max_presenter_s=a.max_presenter_s)
    plan.save(a.out)
    probs = validate_plan(plan)
    for s in plan.scenes:
        print(f"scene {s.id:>2}  {s.start:6.2f}-{s.end:6.2f}s  {s.mode:12} {s.action[:60]}")
    print(f"\nwrote {a.out}; validation: {'OK' if not probs else probs}")
    return 0 if not probs else 1


def cmd_validate(a):
    probs = validate_plan(ScenePlan.load(a.plan))
    print("OK" if not probs else "\n".join(probs))
    return 0 if not probs else 1


def _prov(a):
    p = load_provider(a.provider, PROVIDERS_CFG)
    sp = load_provider(a.story_provider, PROVIDERS_CFG) if a.story_provider else None
    return p, sp


def cmd_generate(a):
    plan = ScenePlan.load(a.plan)
    p, sp = _prov(a)
    for prov in (p, sp):
        if prov:
            ok, msg = prov.check_config()
            if not ok:
                print(f"provider {prov.capabilities.name} not configured: {msg}", file=sys.stderr)
                return 2
    man = pipeline.generate_clips(plan, a.audio, a.work, p, sp, a.resolution)
    for i, e in man.items():
        print(f"scene {i}: {e['status']:15} {e['provider']:14} {e['error']}")
    bad = [i for i, e in man.items() if e["status"] != "done"]
    return 0 if not bad else 1


def _subs(a, plan, preset):
    if not a.subtitles:
        return None
    t = Timing.from_dict(json.loads(Path(a.timing).read_text()))
    if not t.words:
        raise SystemExit("subtitles need word timings; run `timing` with a script or transcript")
    if t.word_source == "estimated":
        print("WARNING: subtitle timing is estimated, not measured.")
    pr = assemble.load_preset(preset)
    vertical = plan.aspect == "9:16"
    cues = subtitles.group_words(t.words, max_chars=22 if vertical else 40)
    work = Path(a.work)
    subtitles.write_srt(cues, work / "subtitles.srt")
    subtitles.write_ass(cues, work / "subtitles.ass", pr["width"], pr["height"], pr.get("caption_bottom_margin_pct", 15))
    return str(work / "subtitles.ass")


def cmd_assemble(a):
    plan = ScenePlan.load(a.plan)
    man = json.loads((Path(a.work) / "manifest.json").read_text())
    clips = pipeline.clips_from_manifest(man)
    missing = [s.id for s in plan.scenes if s.id not in clips]
    if missing:
        print(f"cannot assemble: scenes without finished clips: {missing}", file=sys.stderr)
        return 1
    info = assemble.assemble(plan, clips, a.audio, a.out, Path(a.work) / "assemble", a.preset, _subs(a, plan, a.preset))
    print(json.dumps(info, indent=2))


def cmd_qc(a):
    plan = ScenePlan.load(a.plan)
    man = json.loads((Path(a.work) / "manifest.json").read_text())
    t = Timing.from_dict(json.loads(Path(a.timing).read_text())) if a.timing else None
    rep = qc.run_qc(a.video, plan, a.audio, a.preset, str(pipeline.REFERENCE),
                    {int(i): e["provider"] for i, e in man.items()}, pipeline.clips_from_manifest(man), t,
                    str(Path(a.work) / "qc"), a.max_seconds)
    print(Path(a.work, "qc", "qc_report.md").read_text())
    return {"FAILED": 1, "NEEDS_HUMAN_REVIEW": 0, "PASSED": 0}[rep["verdict"]]


def cmd_run(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    a.timing_path = str(work / "timing.json")
    t = timing_mod.analyse(a.audio, Path(a.script).read_text(), a.transcript, use_asr=not a.no_asr)
    Path(a.timing_path).write_text(json.dumps(t.to_dict(), indent=2))
    p, sp = _prov(a)
    limit = p.max_seconds(a.resolution)
    plan = scene_planner.plan_scenes(Path(a.script).read_text(), t, assemble.load_preset(a.preset)["aspect"], a.title,
                                     max_presenter_s=(limit - 2) if limit else 25.0)
    plan.save(work / "plan.json")
    probs = validate_plan(plan)
    if probs:
        print("plan invalid:\n" + "\n".join(probs), file=sys.stderr)
        return 1
    for prov in (p, sp):
        if prov:
            ok, msg = prov.check_config()
            if not ok:
                print(f"provider {prov.capabilities.name} not configured: {msg}\nPlan saved to {work/'plan.json'}.", file=sys.stderr)
                return 2
    man = pipeline.generate_clips(plan, a.audio, work, p, sp, a.resolution)
    for i, e in man.items():
        print(f"scene {i}: {e['status']:15} {e['error']}")
    if any(e["status"] != "done" for e in man.values()):
        print("not all scenes finished; fix the above and re-run (finished clips are reused).", file=sys.stderr)
        return 1
    a.work = str(work)
    a.plan = str(work / "plan.json")
    a.timing = a.timing_path
    a.video = a.out
    cmd_assemble(a)
    return cmd_qc(a)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ymm_cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    s = sub.add_parser("timing"); s.add_argument("--audio", required=True); s.add_argument("--script"); s.add_argument("--transcript")
    s.add_argument("--no-asr", action="store_true"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_timing)
    s = sub.add_parser("plan"); s.add_argument("--script", required=True); s.add_argument("--timing", required=True)
    s.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"]); s.add_argument("--title", default="Untitled")
    s.add_argument("--max-presenter-s", type=float, default=25.0); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("validate"); s.add_argument("--plan", required=True); s.set_defaults(fn=cmd_validate)
    def prov_args(x):
        x.add_argument("--provider", required=True); x.add_argument("--story-provider"); x.add_argument("--resolution", default="720p", choices=["720p", "1080p"])
    s = sub.add_parser("generate"); s.add_argument("--plan", required=True); s.add_argument("--audio", required=True); s.add_argument("--work", required=True)
    prov_args(s); s.set_defaults(fn=cmd_generate)
    s = sub.add_parser("assemble"); s.add_argument("--plan", required=True); s.add_argument("--audio", required=True); s.add_argument("--work", required=True)
    s.add_argument("--preset", required=True); s.add_argument("--out", required=True); s.add_argument("--subtitles", action="store_true"); s.add_argument("--timing")
    s.set_defaults(fn=cmd_assemble)
    s = sub.add_parser("qc"); s.add_argument("--plan", required=True); s.add_argument("--audio", required=True); s.add_argument("--work", required=True)
    s.add_argument("--video", required=True); s.add_argument("--preset", required=True); s.add_argument("--timing"); s.add_argument("--max-seconds", type=float)
    s.set_defaults(fn=cmd_qc)
    s = sub.add_parser("run"); s.add_argument("--script", required=True); s.add_argument("--audio", required=True); s.add_argument("--work", required=True)
    s.add_argument("--preset", required=True); s.add_argument("--out", required=True); s.add_argument("--title", default="Untitled")
    s.add_argument("--transcript"); s.add_argument("--no-asr", action="store_true"); s.add_argument("--subtitles", action="store_true")
    s.add_argument("--max-seconds", type=float); prov_args(s); s.set_defaults(fn=cmd_run)
    a = ap.parse_args(argv)
    try:
        return a.fn(a) or 0
    except ProviderError as e:
        print(f"provider error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
