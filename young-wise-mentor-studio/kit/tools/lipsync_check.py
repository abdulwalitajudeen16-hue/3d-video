"""tools/lipsync_check.py — QC the mouth animation against the real voiceover.

  python tools/lipsync_check.py --project projects/<slug> [--audio path] [--max-lag 0.3]

Compares the mouth-open curve the renderer will draw (engine/lipsync.js, run in Node) with the loudness envelope of the
voiceover. Reports the correlation, the best-fit lag in milliseconds (positive = mouth is EARLY, negative = mouth is LATE),
how much of the time the mouth is open while the voice is silent (and the reverse), and writes
build/lipsync_report.txt + build/lipsync_plot.png. A lag beyond about +-80 ms means the timestamps need fixing (re-run
transcribe.py with a bigger model) or config.json -> "lipsyncOffset" should be set.
"""
import argparse, json, os, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--audio")
ap.add_argument("--max-lag", type=float, default=0.3)
a = ap.parse_args()
proj = a.project
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(proj, "config.json")))
audio = a.audio or os.path.join(proj, cfg.get("voiceover", "input/voiceover.mp3"))
if not os.path.exists(audio):
    sys.exit(f"voiceover not found: {audio}")

curve = json.loads(subprocess.check_output(["node", os.path.join(ROOT, "tools", "lipsync_curve.mjs"), proj], text=True))
fps = curve["fps"]; mouth = np.array(curve["open"], float); speaking = np.array(curve["speaking"], float)

SR = 16000
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", audio, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
x = np.frombuffer(raw, np.int16).astype(float) / 32768
hop = SR // fps
n = min(len(x) // hop, len(mouth))
env = np.sqrt(np.array([np.mean(x[i * hop:(i + 1) * hop] ** 2) for i in range(n)]))
env = np.convolve(env, np.ones(3) / 3, mode="same"); env = env / (np.percentile(env, 98) + 1e-9)
m = mouth[:n]
def corr(lag):                              # lag > 0: mouth curve shifted later
    k = int(round(lag * fps))
    if k >= 0: A, B = env[k:], m[:n - k]
    else: A, B = env[:n + k], m[-k:]
    return float(np.corrcoef(A, B)[0, 1]) if len(A) > 10 else -1
lags = np.arange(-a.max_lag, a.max_lag + 1e-6, 1 / fps); cs = [corr(l) for l in lags]
best = lags[int(np.argmax(cs))]; c0, cb = corr(0), max(cs)
voiced = env > 0.12; open_ = m > 0.12
ghost = float(np.mean(open_ & ~voiced)); mute = float(np.mean(voiced & ~open_))
lines = [f"correlation at 0 ms: {c0:.2f}", f"best correlation: {cb:.2f} at lag {best * 1000:+.0f} ms (positive = mouth is early)",
         f"mouth open while silent: {ghost * 100:.1f}% of frames", f"voice present but mouth closed: {mute * 100:.1f}% of frames"]
verdict = "GOOD" if cb > 0.5 and abs(best) <= 0.08 else ("OK: small offset" if cb > 0.4 else "CHECK: timestamps may not match this audio")
lines.append("verdict: " + verdict)
os.makedirs(os.path.join(proj, "build"), exist_ok=True)
open(os.path.join(proj, "build", "lipsync_report.txt"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
try:
    from PIL import Image, ImageDraw
    W, H = 1600, 360; im = Image.new("RGB", (W, H), (18, 20, 26)); d = ImageDraw.Draw(im)
    seg_n = min(n, 50 * 40)                 # first 40 s
    for arr, col, y0 in ((env, (110, 180, 255), 170), (m, (255, 190, 90), 340)):
        pts = [(i * W / seg_n, y0 - float(min(1.2, arr[i])) * 150) for i in range(seg_n)]
        d.line(pts, fill=col, width=2)
    d.text((10, 8), "blue: voice loudness   orange: mouth open (first 40 s)   " + lines[1], fill=(200, 205, 215))
    im.save(os.path.join(proj, "build", "lipsync_plot.png"))
except Exception as e:
    print("(plot skipped:", e, ")")
