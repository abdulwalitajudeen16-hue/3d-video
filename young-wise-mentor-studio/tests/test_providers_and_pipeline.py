import json
import subprocess

import pytest
import requests

from ymm import assemble, ffutil, pipeline, qc, scene_planner, subtitles, timing
from ymm.models import validate_plan
from ymm.providers import ManualStepRequired, ProviderError, ProviderNotConfigured, SceneJob, load_provider
from ymm.providers.fal_omnihuman import FalOmniHuman
from ymm.providers.generic_http import GenericHTTP

REF = str(pipeline.REFERENCE)


def _job(tmp_path, voiceover, dur=5.0, mode="presenter"):
    audio = tmp_path / "a.wav"
    ffutil.cut_audio(voiceover, audio, 0, dur)
    return SceneJob(1, mode, REF, "prompt", "9:16", dur, str(tmp_path / "clips" / "scene_01.mp4"),
                    str(audio) if mode == "presenter" else None)


def test_fal_requires_key(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    ok, msg = FalOmniHuman().check_config()
    assert not ok and "FAL_KEY" in msg


def test_fal_queue_protocol_against_local_fake(monkeypatch, fake_service, tmp_path, voiceover):
    monkeypatch.setenv("FAL_KEY", "test-key")
    p = FalOmniHuman(queue_base=fake_service["base"], poll_interval=0, sleep=lambda s: None)
    out = p.generate(_job(tmp_path, voiceover))
    assert ffutil.video_info(out)["has_video"]
    path, body = fake_service["submitted"][0]
    assert path == "/fal-ai/bytedance/omnihuman/v1.5"
    assert body["resolution"] == "720p" and body["image_url"].startswith("data:image/jpeg;base64,")
    assert body["audio_url"].startswith("data:audio/wav;base64,")
    assert fake_service["status_calls"] >= 2  # polled until COMPLETED


def test_fal_bad_key_and_limits_and_wrong_mode(monkeypatch, fake_service, tmp_path, voiceover):
    monkeypatch.setenv("FAL_KEY", "wrong")
    p = FalOmniHuman(queue_base=fake_service["base"], sleep=lambda s: None)
    with pytest.raises(ProviderError, match="401"):
        p.generate(_job(tmp_path, voiceover))
    monkeypatch.setenv("FAL_KEY", "test-key")
    j = _job(tmp_path, voiceover)
    j.duration = 75
    with pytest.raises(ProviderError, match="limit"):
        p.generate(j)
    with pytest.raises(ProviderError, match="presenter"):
        p.generate(_job(tmp_path, voiceover, mode="storytelling"))


def test_generic_http_roundtrip_and_env_check(monkeypatch, fake_service, tmp_path, voiceover):
    cfg = {"name": "x", "image_to_video": True, "lipsync": True,
           "submit": {"url": fake_service["base"] + "/v1/jobs", "headers": {"Authorization": "Bearer ${ENV:X_KEY}"},
                      "json": {"p": "${PROMPT}", "img": "${IMAGE_DATA_URI}"}},
           "job_id_path": "id",
           "poll": {"url": fake_service["base"] + "/v1/jobs/${JOB_ID}", "status_path": "status",
                    "done_values": ["done"], "failed_values": ["failed"]},
           "result": {"video_url_path": "output.0.url"}}
    p = GenericHTTP(cfg, poll_interval=0, sleep=lambda s: None)
    monkeypatch.delenv("X_KEY", raising=False)
    ok, msg = p.check_config()
    assert not ok and "X_KEY" in msg
    monkeypatch.setenv("X_KEY", "k")
    assert p.check_config()[0]
    out = p.generate(_job(tmp_path, voiceover, mode="storytelling"))
    assert ffutil.video_info(out)["has_video"]
    assert fake_service["headers"][-1].get("Authorization") == "Bearer k"


def test_generic_refuses_lipsync_when_not_declared(tmp_path, voiceover):
    cfg = {"name": "i2v", "image_to_video": True, "lipsync": False, "submit": {"url": "http://x"}, "job_id_path": "id",
           "poll": {"url": "http://x"}, "result": {}}
    with pytest.raises(ProviderError, match="not configured as lip-sync"):
        GenericHTTP(cfg).generate(_job(tmp_path, voiceover))


def test_manual_writes_job_package(tmp_path, voiceover):
    p = load_provider("manual")
    with pytest.raises(ManualStepRequired):
        p.generate(_job(tmp_path, voiceover))
    jd = tmp_path / "jobs" / "scene_01"
    assert (jd / "reference.jpg").exists() and (jd / "audio.wav").exists() and (jd / "prompt.txt").exists()


def test_unknown_provider():
    with pytest.raises(ProviderError, match="unknown provider"):
        load_provider("nope")


def test_end_to_end_with_mock_is_gated_as_failed(tmp_path, voiceover, script_text):
    """Whole pipeline mechanics with the mock provider. QC must refuse to call a mock render a success."""
    t = timing.analyse(str(voiceover), script_text, use_asr=False)
    plan = scene_planner.plan_scenes(script_text, t, "9:16", "E2E")
    assert validate_plan(plan) == []
    mock = load_provider("mock")
    man = pipeline.generate_clips(plan, str(voiceover), tmp_path, mock, mock)
    assert all(e["status"] == "done" for e in man.values())
    # resume: second call reuses clips
    assert all("reused" in e.get("note", "") for e in pipeline.generate_clips(plan, str(voiceover), tmp_path, mock, mock).values())
    cues = subtitles.group_words(t.words, 22)
    subtitles.write_ass(cues, tmp_path / "s.ass", 1080, 1920, 22)
    out = tmp_path / "final.mp4"
    info = assemble.assemble(plan, pipeline.clips_from_manifest(man), str(voiceover), out, tmp_path / "asm",
                             "youtube-shorts", str(tmp_path / "s.ass"))
    vi = ffutil.video_info(out)
    assert (vi["width"], vi["height"]) == (1080, 1920) and vi["has_audio"]
    assert abs(vi["duration"] - t.duration) < 0.15
    rep = qc.run_qc(str(out), plan, str(voiceover), "youtube-shorts", REF, {i: e["provider"] for i, e in man.items()},
                    pipeline.clips_from_manifest(man), t, str(tmp_path / "qc"))
    by = {c["id"]: c for c in rep["checks"]}
    assert rep["verdict"] == "FAILED"
    assert by["dimensions"]["status"] == "PASS"
    assert by["voiceover_duration"]["status"] == "PASS"
    assert by["av_sync"]["status"] == "PASS"
    assert by["audio_is_voiceover"]["status"] == "PASS"
    assert by["real_generation"]["status"] == "FAIL"
    assert by["lipsync"]["status"] == "FAIL"
    assert by["not_stationary"]["status"] == "FAIL"      # static still is correctly flagged
    assert by["word_timing_quality"]["status"] == "NEEDS_REVIEW"
    assert by["photorealism"]["status"] == "NEEDS_REVIEW"
    assert (tmp_path / "qc" / "review_sheet.jpg").exists() and (tmp_path / "qc" / "qc_report.md").exists()


def test_qc_flags_wrong_dimensions_and_audio_mismatch(tmp_path, voiceover, script_text):
    t = timing.analyse(str(voiceover), script_text, use_asr=False)
    plan = scene_planner.plan_scenes(script_text, t, "9:16", "bad")
    bad = tmp_path / "bad.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=640x360:rate=30:duration=10", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", "10", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(bad)], check=True)
    rep = qc.run_qc(str(bad), plan, str(voiceover), "youtube-shorts", REF, {}, {}, t, str(tmp_path / "qc"))
    by = {c["id"]: c for c in rep["checks"]}
    assert rep["verdict"] == "FAILED"
    assert by["dimensions"]["status"] == "FAIL"
    assert by["voiceover_duration"]["status"] == "FAIL"
    assert by["audio_is_voiceover"]["status"] == "FAIL"


def test_assemble_rejects_aspect_mismatch(tmp_path, voiceover, script_text):
    t = timing.analyse(str(voiceover), script_text, use_asr=False)
    plan = scene_planner.plan_scenes(script_text, t, "9:16", "x")
    with pytest.raises(ValueError, match="9:16"):
        assemble.assemble(plan, {}, str(voiceover), tmp_path / "o.mp4", tmp_path, "youtube")


def test_generate_refuses_to_fake_lipsync(tmp_path, voiceover, script_text):
    t = timing.analyse(str(voiceover), script_text, use_asr=False)
    plan = scene_planner.plan_scenes(script_text, t, "9:16", "x")
    man = pipeline.generate_clips(plan, str(voiceover), tmp_path, FalOmniHuman(), FalOmniHuman())
    assert all(e["status"] == "failed" for e in man.values())
    assert any("cannot make acted storytelling" in e["error"] for e in man.values())


def test_landscape_reference_is_unedited_crop(tmp_path):
    from PIL import Image
    assert pipeline.reference_for_aspect("9:16", tmp_path) == pipeline.REFERENCE
    p = pipeline.reference_for_aspect("16:9", tmp_path)
    im = Image.open(p)
    assert im.size[0] / im.size[1] == pytest.approx(16 / 9, rel=0.01)
    assert im.size[0] == Image.open(pipeline.REFERENCE).size[0]  # full width, no rescale or generative fill
