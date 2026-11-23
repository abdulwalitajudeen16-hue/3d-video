import json

import pytest

from ymm import gestures, scene_planner, subtitles, timing
from ymm.models import Scene, ScenePlan, validate_plan
from ymm.script_analysis import analyse_script, split_sentences


def test_sentence_split_and_story_triggers(script_text):
    beats = analyse_script(script_text)
    assert len(beats) == 6
    actions = {b.story_action for b in beats if b.story_action}
    assert "waking" in actions and "phone" in actions
    assert next(b for b in beats if "phone" in b.text).story_trigger.lower().startswith("pick")


def test_no_trigger_means_no_story_action():
    beats = analyse_script("Discipline is a habit. Habits are built by showing up every single day.")
    assert all(b.story_action is None for b in beats)


def test_timing_detects_pauses(voiceover, script_text):
    t = timing.analyse(str(voiceover), script_text, use_asr=False)
    assert abs(t.duration - 26.2) < 0.2
    assert len(t.silences) == 4
    assert len(t.speech_segments) == 5
    assert t.word_source == "estimated"
    assert t.words and t.words[0].start >= 0 and t.words[-1].end <= t.duration + 0.01
    assert all(a.end <= b.start + 1e-6 for a, b in zip(t.words, t.words[1:]))


def test_import_json_and_srt(tmp_path):
    j = tmp_path / "w.json"
    j.write_text(json.dumps({"segments": [{"words": [{"word": " Hello", "start": 0.1, "end": 0.4}, {"word": "world", "start": 0.5, "end": 0.9}]}]}))
    w = timing.import_words(j)
    assert [x.text for x in w] == ["Hello", "world"] and w[0].source == "imported"
    s = tmp_path / "c.srt"
    s.write_text("1\n00:00:01,000 --> 00:00:03,000\nOne two three four\n")
    w = timing.import_words(s)
    assert len(w) == 4 and abs(w[-1].end - 3.0) < 1e-6


@pytest.fixture
def plan(voiceover, script_text):
    t = timing.analyse(str(voiceover), script_text, use_asr=False)
    return scene_planner.plan_scenes(script_text, t, "9:16", "Test"), t


def test_plan_is_valid_and_covers_audio(plan):
    p, t = plan
    assert validate_plan(p) == []
    assert p.scenes[0].start == 0 and abs(p.scenes[-1].end - t.duration) < 0.01
    assert any(s.mode == "storytelling" for s in p.scenes) and any(s.mode == "presenter" for s in p.scenes)


def test_every_story_action_is_justified_by_narration(plan):
    p, _ = plan
    for s in p.scenes:
        if s.mode == "storytelling":
            assert s.action_trigger and s.action_trigger.lower() in s.narration.lower()
            assert s.needs_lipsync is False
        else:
            assert s.needs_lipsync is True


def test_cuts_land_in_pauses_when_possible(plan):
    p, t = plan
    for a in p.scenes[:-1]:
        if "not in a pause" not in a.notes:
            assert any(s.start <= a.end <= s.end for s in t.silences)


def test_gestures_varied_and_never_stationary(plan):
    p, _ = plan
    rep = gestures.repetition_report(p.scenes)
    assert rep["back_to_back_repeats"] == 0
    assert rep["distinct"] >= 4
    for s in p.scenes:
        assert s.gesture_cues, f"scene {s.id} has no motion cues"
        assert all(0 <= c.at <= s.duration for c in s.gesture_cues)


def test_pointing_is_tied_to_you_in_urgent_context():
    sc = Scene(id=1, narration="You must stop waiting. Now.", start=0, end=6, emotion="urgent")
    gestures.plan_gestures([sc])
    assert any(c.gesture in ("point_to_camera", "closed_fist", "chop_emphasis") for c in sc.gesture_cues)


def test_prompts_carry_identity_lock_and_negatives(plan):
    p, _ = plan
    for s in p.scenes:
        assert "supplied reference photograph" in s.prompt
        assert "cartoon" in s.prompt  # in the negative list
        assert "black pullover hoodie" in s.prompt


def test_validate_rejects_invented_action_and_gaps():
    bad = ScenePlan("x", "9:16", [
        Scene(id=1, narration="Be steady.", start=0, end=4, mode="storytelling", action="walks on the moon"),
        Scene(id=2, narration="Go on.", start=6, end=8)])
    probs = validate_plan(bad)
    assert any("no action_trigger" in p for p in probs)
    assert any("gap" in p for p in probs)


def test_plan_roundtrip(plan, tmp_path):
    p, _ = plan
    p.save(tmp_path / "p.json")
    assert ScenePlan.load(tmp_path / "p.json").to_dict() == p.to_dict()


def test_subtitles(plan, tmp_path):
    _, t = plan
    cues = subtitles.group_words(t.words, max_chars=22)
    assert cues and all(b > a for a, b, _ in cues)
    assert all(len(line) <= 30 for _, _, txt in cues for line in txt.split("\n"))
    subtitles.write_srt(cues, tmp_path / "s.srt")
    subtitles.write_ass(cues, tmp_path / "s.ass", 1080, 1920, 22)
    assert "-->" in (tmp_path / "s.srt").read_text()
    assert "Dialogue:" in (tmp_path / "s.ass").read_text()
