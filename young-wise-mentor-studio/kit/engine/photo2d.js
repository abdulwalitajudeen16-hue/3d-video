// engine/photo2d.js — "talking photo" presenter: the user's real reference photo, animated by code.
// Animated: breathing, head sway/nod (whole-image tilt about the torso), blinks (skin-coloured lids), and a lip-synced jaw/mouth
// (vertical-strip warp of the lower face + painted mouth interior and teeth) driven by engine/lipsync.js.
// NOT animated: arms, hands, body, a head turn: a single photo has no such pixels. Use the illustrated Mentor (mentor2d.js) for those shots.
// Photo + landmarks: project override /project/assets/{mentor-landmarks.json, <image>} else the studio default assets/mentor/.
import { E, V, clamp, noise } from './core.js';
import { mouthAt, emphasisAt } from './lipsync.js';

const loadImg = (src) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('missing ' + src)); i.src = src; });
const getJSON = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(u); return r.json(); };
let LM, IMG;
try { LM = await getJSON('/project/assets/mentor-landmarks.json'); IMG = await loadImg('/project/assets/' + LM.image); }
catch { LM = await getJSON('/assets/mentor/landmarks.json'); IMG = await loadImg('/assets/mentor/' + LM.image); }

const mk = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
const sm = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
// colour of a small patch of the photo (for eyelids)
function patch(x, y, r) { const c = mk(2 * r, 2 * r), x2 = c.getContext('2d'); x2.drawImage(IMG, x - r, y - r, 2 * r, 2 * r, 0, 0, 2 * r, 2 * r); const d = x2.getImageData(0, 0, 2 * r, 2 * r).data; let R = 0, G = 0, B = 0, n = 0; for (let i = 0; i < d.length; i += 4) { R += d[i]; G += d[i + 1]; B += d[i + 2]; n++; } return [R / n, G / n, B / n]; }
const css = (c, k = 1) => `rgb(${Math.round(c[0] * k)},${Math.round(c[1] * k)},${Math.round(c[2] * k)})`;
const EYES = [LM.eyeL, LM.eyeR].map(([cx, cy, hw, hh]) => ({ cx, cy, hw, hh, up: patch(cx, cy - hh * 2.4, 9), low: patch(cx, cy + hh * 2.3, 9) }));
let BG = null, LAYER = null;
const hash = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
function blinkAt(t, seed = 0) { const P = 3.1, slot = Math.floor(t / P), off = 0.25 + 2.3 * hash(slot + seed * 13); const f = (l) => (l > 0 && l < 0.17 ? Math.sin((l / 0.17) * Math.PI) : 0); let b = f(t - slot * P - off); if (hash(slot * 3 + seed) > 0.82) b = Math.max(b, f(t - slot * P - off - 0.3)); return b; }

// o: { t, globalT, speak, intensity, s, fx, fy, dy, lean, idle, blink, seed, dim, debug }
export function drawPhotoMentor(g, o = {}) {
  const t = o.t ?? 0, gT = o.globalT ?? 0, seed = o.seed ?? 0, idle = o.idle !== false, W = E.W, H = E.H;
  const m = o.speak ? mouthAt(gT, { intensity: o.intensity ?? 1 }) : { open: 0, wide: 0, round: 0, tongue: 0, teeth: 0 };
  const emph = o.speak ? emphasisAt(gT) : 0;
  const s = (o.s ?? V(H / 1150, (W / LM.size[0]) * 1.12)) * (1 + 0.05 * (o.lean ?? 0));
  const ox = (o.fx ?? 0.5) * W - LM.face[0] * s, oy = (o.fy ?? V(0.47, 0.4)) * H - LM.face[1] * s + (o.dy ?? 0);
  const imgW = LM.size[0] * s;
  // blurred, dimmed copy of the photo fills the sides of wide frames
  if (imgW < W - 1) {
    if (!BG) { BG = mk(120, 120 * LM.size[1] / LM.size[0]); const b = BG.getContext('2d'); b.filter = 'blur(5px)'; b.drawImage(IMG, -6, -6, BG.width + 12, BG.height + 12); }
    const bw = W, bh = W * LM.size[1] / LM.size[0], by = (o.fy ?? V(0.47, 0.4)) * H - (LM.face[1] / LM.size[1]) * bh;
    g.drawImage(BG, 0, by, bw, bh); g.fillStyle = 'rgba(6,8,12,.45)'; g.fillRect(0, 0, W, H);
  }
  const PX = E.PX; if (!LAYER || LAYER.width !== Math.round(W * PX)) LAYER = mk(W * PX, H * PX);
  const L = LAYER.getContext('2d'); L.setTransform(1, 0, 0, 1, 0, 0); L.clearRect(0, 0, LAYER.width, LAYER.height); L.setTransform(PX, 0, 0, PX, 0, 0);
  // whole-image motion about a pivot low in the torso, so the head moves most and the shoulders barely
  const px = ox + LM.face[0] * s, py = oy + 1750 * s;
  const ang = idle ? noise(t * 0.4 + seed, 3) * 0.0065 + (o.speak ? noise(t * 0.8 + seed, 9) * 0.004 : 0) + emph * 0.005 : 0;
  const br = idle ? 1 + Math.sin(t * 1.9 + seed) * 0.0022 : 1;
  L.save(); L.translate(px, py + emph * 2.5); L.rotate(ang); L.scale(br, br); L.translate(-px, -py);
  L.translate(ox, oy); L.scale(s, s);
  L.drawImage(IMG, 0, 0);
  // lip-synced jaw: the lower face is redrawn in thin vertical strips shifted down, the gap becomes mouth interior
  const [mx, my, mhw] = LM.mouth, d = clamp(m.open + (o.jaw ?? 0), 0, 1.1) * 26;
  if (d > 1.4) {
    const yb = my + 190, step = 2, SEAM = 58;
    const lens = (x) => { const u = Math.abs(x - mx) / (mhw * (0.94 + 0.05 * m.wide - 0.12 * m.round)); return u >= 1 ? 0 : d * Math.pow(1 - u * u, 0.8); };   // lip corners stay pinned
    const jaw = (x) => d * 0.86 * sm(1 - (Math.abs(x - mx) - 40) / 125);                                                                                  // chin and jaw follow more broadly
    // 1. mouth interior inside the lens
    L.save(); L.beginPath(); L.moveTo(mx - mhw, my);
    for (let x = mx - mhw; x <= mx + mhw; x += 2) L.lineTo(x, my + lens(x) + 0.8);
    L.lineTo(mx + mhw, my); L.closePath(); L.clip();
    const ig = L.createLinearGradient(0, my, 0, my + d); ig.addColorStop(0, '#120708'); ig.addColorStop(1, '#3a1517'); L.fillStyle = ig; L.fillRect(mx - mhw, my - 2, mhw * 2, d + 4);
    const tw = mhw * (0.52 + 0.1 * m.wide - 0.14 * m.round);
    if (m.teeth >= 1 && d > 6) { const th = Math.min(d * 0.45, 9), tw2 = tw * 0.82, tg = L.createLinearGradient(0, my, 0, my + th); tg.addColorStop(0, '#cfc4b4'); tg.addColorStop(1, '#8f8576'); L.fillStyle = tg; L.beginPath(); L.roundRect(mx - tw2, my - 1, tw2 * 2, th + 1, [0, 0, 6, 6]); L.fill(); }
    if (m.teeth === 2 && d > 10) { L.fillStyle = '#9a8f80'; L.beginPath(); L.roundRect(mx - tw * 0.8, my + d - 7, tw * 1.6, 8, [4, 4, 0, 0]); L.fill(); }
    if (m.tongue > 0.4 || d > 12) { L.fillStyle = '#7a3436'; L.beginPath(); L.ellipse(mx, my + d - 2, tw * 0.85, 5 + m.tongue * 3, 0, 0, 7); L.fill(); }
    L.restore();
    // 2. lower face redrawn in thin strips: lip piece (lens shift, corners pinned) + jaw piece (broad shift), continuous at the seam
    for (let x = mx - 175; x < mx + 175; x += step) {
      const sa = lens(x), sb = jaw(x); if (sa < 0.3 && sb < 0.3) continue;
      L.drawImage(IMG, x, my, step + 0.7, SEAM, x, my + sa, step + 0.7, SEAM + sb - sa);
      L.drawImage(IMG, x, my + SEAM, step + 0.7, yb - my - SEAM, x, my + SEAM + sb, step + 0.7, yb - my - SEAM - sb);
    }
  }
  // blinks: skin-coloured lid sweeps down, lash line on its edge
  const b = o.blink ?? (idle ? blinkAt(t, seed) : 0);
  if (b > 0.04) for (const e of EYES) {
    const top = e.cy - e.hh * 1.5, lidY = top + b * (e.hh * 2.75);
    L.save(); L.beginPath(); L.ellipse(e.cx, e.cy, e.hw * 1.08, e.hh * 1.45, 0, 0, 7); L.clip();
    const gr = L.createLinearGradient(0, top, 0, e.cy + e.hh * 1.2); gr.addColorStop(0, css(e.up, 0.95)); gr.addColorStop(1, css(e.low, 1.02)); L.fillStyle = gr; L.fillRect(e.cx - e.hw * 1.3, top - 4, e.hw * 2.6, lidY - top + 4);
    L.strokeStyle = 'rgba(12,8,8,.85)'; L.lineWidth = 3; L.lineCap = 'round'; L.beginPath(); L.moveTo(e.cx - e.hw, lidY - 1); L.quadraticCurveTo(e.cx, lidY + 3 + b * 2, e.cx + e.hw, lidY - 1); L.stroke(); L.restore();
  }
  if (o.debug) { L.fillStyle = 'rgba(0,255,255,.7)'; for (const e of EYES) L.fillRect(e.cx - 4, e.cy - 4, 8, 8); L.fillStyle = 'rgba(255,0,255,.8)'; L.fillRect(mx - 4, my - 4, 8, 8); }
  L.restore();
  if (imgW < W - 1) {                       // feather the photo's left/right edges into the blurred fill
    L.setTransform(1, 0, 0, 1, 0, 0); L.globalCompositeOperation = 'destination-in';
    const a = ox * PX, w = imgW * PX, f = Math.min(110 * PX, w / 3), gr = L.createLinearGradient(a, 0, a + w, 0);
    gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(f / w, 'rgba(0,0,0,1)'); gr.addColorStop(1 - f / w, 'rgba(0,0,0,1)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    L.fillStyle = gr; L.fillRect(0, 0, LAYER.width, LAYER.height); L.globalCompositeOperation = 'source-over';
  }
  g.save(); if (o.dim) g.globalAlpha *= 1 - o.dim; g.drawImage(LAYER, 0, 0, W, H); g.restore();
}
export const PHOTO = { get size() { return LM.size; }, landmarks: LM };
