"""tools/verify_kit.py — confirm every studio file was written exactly (run right after installing).

  python tools/verify_kit.py
Prints MISMATCH/MISSING for any file that differs from the tested version; copy those files again from the plugin kit folder.
(Line endings and leading/trailing blank lines are ignored. Files you customise later, e.g. engine/styles.js, will of course differ.)
"""
import hashlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = {
    "audio/dsp.py": "589d305d94d8acc3",
    "audio/mix.py": "a48273c523b68c3b",
    "audio/music.py": "2fb3ce1df2fe5c7d",
    "audio/sfx.py": "2fa56141e2423718",
    "engine/core.js": "c012ddbe79332629",
    "engine/fx2d.js": "d09f93f6d44366fa",
    "engine/lipsync.js": "c098c1b3a30c4aff",
    "engine/mentor2d.js": "3580a7c11b1b8f36",
    "engine/player.js": "02ddc7b9ab6dd8fc",
    "engine/rig2d.js": "6b7390c6d988b0d1",
    "engine/styles.js": "7ec413d8c73b6a0d",
    "engine/three-kit.js": "02e249e302b95420",
    "engine/ui2d.js": "babd2978a5d2a6db",
    "examples/character-sheet/config.json": "0227026d0c035ce6",
    "examples/character-sheet/scenes/shots/sheet.js": "62b46938afe20de1",
    "examples/character-sheet/story/shots.json": "7a8666a2b27ce89a",
    "examples/mentor-demo/config.json": "5d05884b2a571e87",
    "examples/mentor-demo/scenes/sets/rooms.js": "581d730f8c7f5104",
    "examples/mentor-demo/scenes/shots/01_demo.js": "44a892dc667cd90c",
    "examples/mentor-demo/story/shots.json": "44f6e8ef1b872550",
    "examples/mentor-demo/timeline/words.json": "e1589b64993eba55",
    "package.json": "53a458b221850914",
    "player.html": "5ffdd7da4a48cd4b",
    "render.mjs": "8c73b01d70018bfd",
    "tools/beats.py": "eb42a8aef4d87584",
    "tools/common.py": "e237321f2f12416e",
    "tools/doctor.py": "67ce3ea2b97a360f",
    "tools/lipsync_check.py": "3d2fed9f63851720",
    "tools/lipsync_curve.mjs": "ee94a800e78f7bd8",
    "tools/new_project.py": "c1002963a2bbba50",
    "tools/parse_script.py": "5163cf3162b2579b",
    "tools/scene_cards.py": "6b79f5c73dbf169e",
    "tools/transcribe.py": "ecd48d05a6655d13",
}
bad = 0
for rel, want in EXPECTED.items():
    p = os.path.join(ROOT, *rel.split("/"))
    if not os.path.exists(p):
        print(f"MISSING   {rel}"); bad += 1; continue
    got = hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n").strip()).hexdigest()[:16]
    if got != want:
        print(f"MISMATCH  {rel}"); bad += 1
print(f"{len(EXPECTED) - bad}/{len(EXPECTED)} files verified." + ("" if not bad else "  Copy the files listed above again from the plugin's kit folder, then run this again."))
sys.exit(1 if bad else 0)
