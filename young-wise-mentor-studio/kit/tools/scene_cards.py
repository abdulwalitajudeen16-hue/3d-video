"""tools/scene_cards.py — turn story/shots.json into a readable scene-card sheet (and optional external-tool prompts).

  python tools/scene_cards.py --project projects/<slug> [--prompts]

Writes story/scene-cards.md: one card per shot with narration, mode (presenter / story), emotion, action, expression,
gesture, environment, camera and duration, plus warnings (missing fields, gesture repeated 3x in a row, long presenter
runs, shots shorter than 0.8 s). With --prompts it also writes story/scene-prompts.md: a self-contained text prompt per
shot (character sheet text + action + camera) for people who want to render some shots in an outside video tool.
"""
import argparse, json, os
from collections import Counter

ap = argparse.ArgumentParser(); ap.add_argument("--project", required=True); ap.add_argument("--prompts", action="store_true"); a = ap.parse_args()
sp = os.path.join(a.project, "story", "shots.json"); data = json.load(open(sp)); shots = data["shots"]
FIELDS = ["mode", "emotion", "action", "expression", "gesture", "set", "camera"]
CHAR = ("The Young Wise Mentor: a calm, intelligent young man of about 25, short neat dark hair, clean-shaven, warm natural skin tone, "
        "plain dark charcoal hoodie, dark jeans, white sneakers, calm thoughtful eyes. Keep face, hair, clothing and proportions identical in every scene.")
warn = []; cards = []; prev_g = []; presenter_run = 0
for i, s in enumerate(shots):
    d = s["end"] - s["start"]; miss = [f for f in FIELDS if not s.get(f) and not (f == "action" and s.get("mode") == "presenter")]
    if miss: warn.append(f"{s['id']}: missing {', '.join(miss)}")
    if d < 0.8: warn.append(f"{s['id']}: only {d:.1f}s long")
    g = s.get("gesture"); prev_g = (prev_g + [g])[-3:]
    if g and len(prev_g) == 3 and len(set(prev_g)) == 1 and g not in ("rest", "relaxed"): warn.append(f"{s['id']}: gesture '{g}' used 3 shots in a row, vary it")
    presenter_run = presenter_run + d if s.get("mode") == "presenter" else 0
    if presenter_run > 20: warn.append(f"{s['id']}: more than 20 s of presenter mode in a row, cut to a story or insert shot")
    cards.append((s, d))
mc = Counter(s.get("mode", "?") for s in shots); out = [f"# Scene cards: {data.get('title', '')}", "", f"{len(shots)} shots, {data.get('duration', 0):.1f} s. Modes: " + ", ".join(f"{k} {v}" for k, v in mc.items()), ""]
if warn: out += ["## Warnings", *[f"- {w}" for w in warn], ""]
for s, d in cards:
    out += [f"## {s['id']}  ({s['start']:.1f}s to {s['end']:.1f}s, {d:.1f} s)  [{s.get('mode', '?')}]", f"> {s.get('line', '')}", "",
            f"- **Emotion:** {s.get('emotion', '')}", f"- **Action:** {s.get('action', s.get('scene', ''))}", f"- **Expression:** {s.get('expression', '')}  **Gesture:** {s.get('gesture', '')}",
            f"- **Environment:** {s.get('set', '')}  **Camera:** {s.get('camera', '')}", ""]
open(os.path.join(a.project, "story", "scene-cards.md"), "w", encoding="utf-8").write("\n".join(out)); print(f"wrote story/scene-cards.md ({len(warn)} warnings)")
for w in warn: print(" -", w)
if a.prompts:
    ps = [f"# Scene prompts (for outside video tools)", "", "Character (paste into every prompt): " + CHAR, ""]
    for s, d in cards:
        look = "Looking straight into the camera and speaking to the viewer" if s.get("mode") == "presenter" else s.get("action", s.get("scene", ""))
        ps += [f"## {s['id']} ({d:.1f} s)", f"{CHAR} {look}. Expression: {s.get('expression', '')}. Body language: {s.get('gesture', '')}. Setting: {s.get('set', '')}. Camera: {s.get('camera', '')}. Cinematic lighting, shallow depth of field. Duration {d:.1f} seconds.", f"Narration: {s.get('line', '')}", ""]
    open(os.path.join(a.project, "story", "scene-prompts.md"), "w", encoding="utf-8").write("\n".join(ps)); print("wrote story/scene-prompts.md")
