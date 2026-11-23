// engine/mentor2d.js — THE YOUNG WISE MENTOR: one fixed, consistent, code-drawn character (2D canvas).
// ~25-year-old man, short neat dark hair, clean-shaven, warm skin, plain dark hoodie, calm eyes.
// Local space: feet on y=0, up is -y, base height ~ 290 units (s = 1). Front view with yaw -1..1 (0 = at camera, ±0.6 = 3/4, ±1 = near profile).
// The look lives in LOOK below and never changes between shots, that is the consistency guarantee.
import { E, S, clamp, lerp, mixVal, shade, mix, alpha, ease, noise, linGrad, radGrad } from './core.js';
import { mouthAt, speakingAt, emphasisAt } from './lipsync.js';

export const LOOK = {
  skin: '#c8946f', skinShade: '#a5705a', skinLight: '#dcad88', lip: '#a9655b', lipDark: '#8a4a45', mouthIn: '#3b1820', teeth: '#f3f0e8', tongue: '#c4616b',
  hair: '#1a1a21', hairHi: '#41424f', brow: '#17171c', iris: '#4b3527', sclera: '#f2efe9',
  hoodie: '#272a33', hoodieShade: '#191b22', hoodieLight: '#3b3f4c', cord: '#d9d6cf',
  jeans: '#2e3646', shoe: '#ecebe6', sole: '#b4b2ab',
};
const D = { headY: -254, rx: 24, ry: 29, neckY: -224, shY: -208, hipY: -120, upper: 52, fore: 50 };
export const HEIGHT = 290;
const hash = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };

// ---------------------------------------------------------------- expressions
// browY: -1 low .. +1 high · browIn: -1 inner lowered (angry/serious) .. +1 inner raised (sad/regret) · browAsym: raise one brow
// lid: eye openness (1 normal) · squint · smile: -1 frown .. +1 broad · smirk · jaw: base jaw opening · gaze: optional [x,y] override
export const EXPRESSIONS = {
  neutral:      { browY: 0.1, browIn: 0, browAsym: 0, lid: 0.92, squint: 0, smile: 0.12, smirk: 0, jaw: 0 },
  calm:         { browY: 0.1, browIn: 0.05, browAsym: 0, lid: 0.9, squint: 0, smile: 0.18, smirk: 0, jaw: 0 },
  explaining:   { browY: 0.25, browIn: 0.1, browAsym: 0, lid: 0.97, squint: 0, smile: 0.25, smirk: 0, jaw: 0 },
  direct:       { browY: -0.1, browIn: -0.25, browAsym: 0, lid: 0.95, squint: 0, smile: 0, smirk: 0, jaw: 0 },
  serious:      { browY: -0.3, browIn: -0.55, browAsym: 0, lid: 0.9, squint: 0.1, smile: -0.12, smirk: 0, jaw: 0 },
  warning:      { browY: -0.4, browIn: -0.75, browAsym: 0, lid: 0.86, squint: 0.2, smile: -0.22, smirk: 0, jaw: 0 },
  confident:    { browY: 0.15, browIn: 0, browAsym: 0, lid: 0.95, squint: 0.05, smile: 0.5, smirk: 0.15, jaw: 0 },
  encouraging:  { browY: 0.4, browIn: 0.2, browAsym: 0, lid: 1.0, squint: 0.1, smile: 0.7, smirk: 0, jaw: 0 },
  reassuring:   { browY: 0.25, browIn: 0.4, browAsym: 0, lid: 0.9, squint: 0.1, smile: 0.55, smirk: 0, jaw: 0 },
  regret:       { browY: 0.0, browIn: 0.85, browAsym: 0, lid: 0.78, squint: 0, smile: -0.35, smirk: 0, jaw: 0 },
  amused:       { browY: 0.2, browIn: 0, browAsym: 0.3, lid: 0.88, squint: 0.3, smile: 0.6, smirk: 0.6, jaw: 0 },
  frustrated:   { browY: -0.4, browIn: -0.65, browAsym: 0, lid: 0.8, squint: 0.2, smile: -0.55, smirk: 0, jaw: 0.05 },
  tired:        { browY: -0.1, browIn: 0.5, browAsym: 0, lid: 0.5, squint: 0, smile: -0.15, smirk: 0, jaw: 0 },
  surprised:    { browY: 1.0, browIn: 0.25, browAsym: 0, lid: 1.3, squint: 0, smile: -0.05, smirk: 0, jaw: 0.5 },
  shocked:      { browY: 1.0, browIn: 0.5, browAsym: 0, lid: 1.4, squint: 0, smile: -0.2, smirk: 0, jaw: 0.65 },
  thinking:     { browY: 0.35, browIn: 0.1, browAsym: 0.6, lid: 0.85, squint: 0.1, smile: 0, smirk: 0.2, jaw: 0, gaze: [0.5, -0.5] },
  sad:          { browY: -0.1, browIn: 0.9, browAsym: 0, lid: 0.7, squint: 0, smile: -0.5, smirk: 0, jaw: 0 },
  determined:   { browY: -0.25, browIn: -0.5, browAsym: 0, lid: 0.92, squint: 0.15, smile: 0.05, smirk: 0.2, jaw: 0 },
};
const EXPR_KEYS = EXPRESSIONS.neutral;
export const expr = (e) => ({ gaze: null, ...EXPR_KEYS, ...(typeof e === 'string' ? EXPRESSIONS[e] || EXPRESSIONS.neutral : e || {}) });

// ---------------------------------------------------------------- gestures
// hand targets L (screen-left hand) and R (screen-right hand) relative to the body root: [x, y, z]; z 0..1 = reaching toward the camera (hand grows, arm foreshortens)
// elbow flare eL/eR -1..1 · hsL/hsR hand shape: relaxed | open | fist | point | flat | grip · sh shoulder raise · lean -1..1 (forward +) · tilt radians · turn: head yaw offset
const G0 = { L: [-41, -104, 0], R: [41, -104, 0], eL: 0, eR: 0, hsL: 'relaxed', hsR: 'relaxed', sh: 0, lean: 0, tilt: 0, turn: 0, nodBase: 0 };
const g_ = (o) => ({ ...G0, ...o });
export const GESTURES = {
  rest:         g_({}),
  relaxed:      g_({ L: [-43, -110, 0], R: [43, -110, 0] }),
  openHands:    g_({ L: [-62, -164, 0.15], R: [62, -164, 0.15], eL: 0.5, eR: 0.5, hsL: 'open', hsR: 'open' }),
  openOne:      g_({ R: [66, -170, 0.15], eR: 0.4, hsR: 'open' }),
  openOneLeft:  g_({ L: [-66, -170, 0.15], eL: 0.4, hsL: 'open' }),
  palmsUp:      g_({ L: [-52, -150, 0.1], R: [52, -150, 0.1], eL: 0.2, eR: 0.2, hsL: 'open', hsR: 'open', lean: 0.2 }),
  pointAtViewer: g_({ R: [30, -200, 0.95], eR: 0.2, hsR: 'point', lean: 0.5 }),
  pointUp:      g_({ R: [52, -262, 0.2], eR: 0.3, hsR: 'point' }),
  chop:         g_({ R: [36, -168, 0.2], eR: 0.2, hsR: 'flat' }),
  presenting:   g_({ L: [-70, -158, 0.1], eL: 0.4, hsL: 'flat', R: [26, -132, 0] }),
  holdFront:    g_({ L: [-16, -158, 0.2], R: [16, -160, 0.2], hsL: 'relaxed', hsR: 'relaxed' }),
  fistClench:   g_({ L: [-22, -170, 0.3], R: [22, -170, 0.3], hsL: 'fist', hsR: 'fist', lean: 0.3 }),
  clasped:      g_({ L: [-8, -146, 0.1], R: [8, -146, 0.1], hsL: 'relaxed', hsR: 'relaxed' }),
  shrug:        g_({ L: [-66, -184, 0.1], R: [66, -184, 0.1], eL: 0.7, eR: 0.7, hsL: 'open', hsR: 'open', sh: 1 }),
  thinkChin:    g_({ R: [14, -236, 0.3], eR: -0.2, hsR: 'fist', L: [-20, -160, 0], hsL: 'relaxed', tilt: 0.05 }),
  crossArms:    g_({ L: [30, -166, 0], R: [-30, -160, 0], eL: -0.3, eR: -0.3, hsL: 'fist', hsR: 'fist' }),
  handsOnHead:  g_({ L: [-30, -270, 0.2], R: [30, -270, 0.2], eL: 0.8, eR: 0.8, hsL: 'open', hsR: 'open' }),
  facepalm:     g_({ R: [8, -250, 0.6], eR: 0.2, hsR: 'open', tilt: 0.12, lean: 0.2 }),
  rubTemples:   g_({ R: [28, -262, 0.2], L: [-28, -262, 0.2], eL: 0.7, eR: 0.7, hsL: 'open', hsR: 'open', tilt: 0.05 }),
  phoneHold:    g_({ R: [24, -176, 0.25], eR: 0.1, hsR: 'grip', L: [-40, -116, 0], lean: 0.15 }),
  phoneBoth:    g_({ L: [-14, -172, 0.2], R: [16, -172, 0.2], hsL: 'grip', hsR: 'grip', lean: 0.2 }),
  handOnChest:  g_({ R: [10, -190, 0.1], hsR: 'open', eR: 0.1 }),
  countOne:     g_({ R: [48, -200, 0.2], hsR: 'point', eR: 0.3 }),
  wave:         g_({ R: [56, -250, 0.1], hsR: 'open', eR: 0.6 }),
};
export const gesture = (g) => ({ ...G0, ...(typeof g === 'string' ? GESTURES[g] || GESTURES.rest : g || {}) });

// pose helpers: hold each key then blend into the next over `blend` seconds. keys: [[t, 'name' | {…overrides}], …]
export function gestureAt(t, keys, blend = 0.45) {
  let cur = gesture(keys[0][1]);
  for (let i = 1; i < keys.length; i++) {
    const [ti, gi] = keys[i]; if (t < ti) break;
    const k = clamp((t - ti) / blend); const nxt = gesture(gi);
    cur = k >= 1 ? nxt : mixVal(cur, nxt, ease.inOut(k)); if (k < 1) return cur;
  }
  return cur;
}
export function exprAt(t, keys, blend = 0.35) {
  let cur = expr(keys[0][1]);
  for (let i = 1; i < keys.length; i++) {
    const [ti, ei] = keys[i]; if (t < ti) break;
    const k = clamp((t - ti) / blend); const nxt = expr(ei);
    cur = k >= 1 ? nxt : mixVal({ ...cur, gaze: cur.gaze || [0, 0] }, { ...nxt, gaze: nxt.gaze || [0, 0] }, ease.inOut(k)); if (k < 1) return cur;
  }
  return cur;
}

// ---------------------------------------------------------------- idle life
function blinkAt(t, seed = 0) {
  const P = 3.1, slot = Math.floor(t / P), off = 0.25 + 2.3 * hash(slot + seed * 13);
  const tryBlink = (loc) => (loc > 0 && loc < 0.17 ? Math.sin((loc / 0.17) * Math.PI) : 0);
  let b = tryBlink(t - slot * P - off);
  if (hash(slot * 3 + seed) > 0.82) b = Math.max(b, tryBlink(t - slot * P - off - 0.3));
  return b;
}

// ---------------------------------------------------------------- drawing
let FLAT = null;                        // when set, everything is drawn in this one colour (rim-light silhouette pass)
const K = (c) => FLAT || c;
const poly2 = (g, pts, col) => { g.fillStyle = K(col); g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); g.closePath(); g.fill(); };
const stroke = (g, pts, w, col, cap = 'round') => { g.strokeStyle = K(col); g.lineWidth = w; g.lineCap = cap; g.lineJoin = 'round'; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); g.stroke(); };
const ell = (g, x, y, rx, ry, col, rot = 0) => { g.fillStyle = K(col); g.beginPath(); g.ellipse(x, y, Math.max(0.01, rx), Math.max(0.01, ry), rot, 0, Math.PI * 2); g.fill(); };
const grow = (w) => (FLAT ? w + FLAT_GROW : w);
let FLAT_GROW = 0;

function ik(S0, T, L1, L2, side, flare) {
  const dx = T[0] - S0[0], dy = T[1] - S0[1]; let d = Math.hypot(dx, dy); const max = L1 + L2 - 0.5; if (d > max) { const k = max / d; T = [S0[0] + dx * k, S0[1] + dy * k]; d = max; }
  d = Math.max(d, Math.abs(L1 - L2) + 0.5);
  const a = (L1 * L1 - L2 * L2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, L1 * L1 - a * a));
  const ux = (T[0] - S0[0]) / d, uy = (T[1] - S0[1]) / d, mx = S0[0] + ux * a, my = S0[1] + uy * a;
  const c1 = [mx - uy * h, my + ux * h], c2 = [mx + uy * h, my - ux * h];
  const sc = (c) => (c[1] - S0[1]) + side * (c[0] - S0[0]) * (0.6 + flare * 1.2);   // prefer the elbow low and (with flare) out
  return { el: sc(c1) > sc(c2) ? c1 : c2, wr: T };
}

function hand(g, x, y, ang, shape, side, z, sdIn) {
  const s = 1 + 0.75 * z, skin = LOOK.skin, sh = LOOK.skinShade;
  g.save(); g.translate(x, y); g.rotate(ang + Math.PI / 2); g.scale(s, s);
  const sd = sdIn ?? side;                      // thumb side
  const fing = (a, len, w = 3.5, curl = 0) => { const x0 = Math.sin(a) * 3, ex = Math.sin(a) * len + curl * Math.sign(a || 1), ey = -15 - Math.cos(a) * len; stroke(g, [[x0 * 0.6 + a * 4, -14], [ex, ey]], grow(w), skin); };
  ell(g, 0, -8, 7.2, 8.6, skin);
  switch (shape) {
    case 'open': {
      [-0.3, -0.1, 0.1, 0.3].forEach((a, i) => fing(a, [10, 13, 13.5, 11][i] + 1, 3.4));
      stroke(g, [[-sd * 5, -6], [-sd * 11, -14], [-sd * 12.5, -20]], grow(3.8), skin);
      if (!FLAT) { stroke(g, [[-0.5, -12], [0, -2]], 0.8, sh); stroke(g, [[3, -12], [3.5, -3]], 0.7, alpha(sh, 0.6)); }
      break; }
    case 'flat': {
      poly2(g, [[-6.4, -12], [6.4, -12], [5.6, -29], [-5.6, -29]], skin); ell(g, 0, -29, 5.8, 2.4, skin);
      stroke(g, [[-sd * 5, -6], [-sd * 9, -13], [-sd * 9, -19]], grow(3.8), skin);
      if (!FLAT) { stroke(g, [[-2, -29], [-2, -14]], 0.7, sh); stroke(g, [[2, -29], [2, -14]], 0.7, sh); }
      break; }
    case 'fist': {
      ell(g, 0, -12, 7.6, 7.2, skin);
      if (!FLAT) { for (const x0 of [-3.8, 0, 3.8]) stroke(g, [[x0, -17], [x0, -10]], 0.8, sh); }
      stroke(g, [[sd * 6, -6], [sd * 5, -14], [sd * 1, -16]], grow(4), skin);
      break; }
    case 'point': {
      ell(g, 0, -10, 7, 6.8, skin);
      stroke(g, [[-2.2, -13], [-2.2, -31]], grow(3.8), skin);
      if (!FLAT) { for (const x0 of [0.8, 3.2]) stroke(g, [[x0, -14], [x0, -9]], 0.8, sh); }
      stroke(g, [[sd * 6, -6], [sd * 5.5, -14], [sd * 2.5, -15]], grow(3.8), skin);
      break; }
    case 'grip': {
      ell(g, 0, -10, 7.8, 8.4, skin);
      if (!FLAT) { for (const y0 of [-12, -8, -4]) stroke(g, [[-6.8, y0], [-8.6, y0 + 1]], 2.4, skin); }
      stroke(g, [[sd * 5, -4], [sd * 8, -14], [sd * 4, -22]], grow(4), skin);
      break; }
    default: { // relaxed
      ell(g, 0, -9, 6.8, 8.2, skin);
      [-3.2, -1, 1.2, 3.4].forEach((x0, i) => stroke(g, [[x0, -14], [x0 * 1.15 + 0.6, -14 - [6, 8, 8, 6.5][i]]], grow(3.2), skin));
      stroke(g, [[sd * 5.4, -6], [sd * 8, -11], [sd * 7.4, -16]], grow(3.6), skin);
    }
  }
  g.restore();
}

function prop(g, p, wx, wy, ang, side) {
  if (!p || FLAT) return;
  g.save(); g.translate(wx, wy); g.rotate(ang + Math.PI / 2);
  if (p.type === 'phone') {
    const w = 15, h = 29; g.translate(side * -1, -16); g.rotate(p.tilt || 0);
    g.fillStyle = '#0c0d12'; g.beginPath(); g.roundRect(-w / 2, -h / 2, w, h, 2.6); g.fill();
    g.fillStyle = p.screen === false ? '#12141a' : linGrad(g, 0, -h / 2, 0, h / 2, [mix(p.glow || '#9fd8ff', '#ffffff', 0.25), p.glow || '#9fd8ff']); g.beginPath(); g.roundRect(-w / 2 + 1, -h / 2 + 1.2, w - 2, h - 2.4, 1.8); g.fill();
    if (p.screen !== false) { g.globalAlpha = 0.45; for (let i = 0; i < 4; i++) { g.fillStyle = '#ffffff'; g.fillRect(-w / 2 + 3, -h / 2 + 4 + i * 6, w - 6, 2.2); } g.globalAlpha = 1; }
  } else if (p.type === 'mug') {
    g.translate(0, -14); g.fillStyle = p.color || '#e8e2d4'; g.beginPath(); g.roundRect(-8, -9, 16, 17, 3); g.fill(); g.strokeStyle = p.color || '#e8e2d4'; g.lineWidth = 2.4; g.beginPath(); g.arc(9, 0, 4.4, -1.2, 1.2); g.stroke();
  } else if (p.type === 'pen') { stroke(g, [[0, -4], [0, -30]], 2.2, '#2c5fd0'); }
  g.restore();
}

// ---------------------------------------------------------------- head
function drawHead(g, st, C) {
  const { yaw, e, m, gaze, blink, glow } = st, rx = D.rx, ry = D.ry;
  const fx = yaw * rx * 0.55, nearSign = Math.sign(yaw) || 1, ay = Math.abs(yaw);
  // ears
  for (const side of [-1, 1]) {
    const lead = side * yaw > 0; if (lead && ay > 0.45) continue;
    const ex = side * (rx - 0.5) * (lead ? 1 : 1 - 0.8 * ay) + (lead ? 0 : -side * 0 );
    ell(g, ex, 2, 4.3 * (1 - 0.1 * ay), 6.4, C.skin); if (!FLAT) ell(g, ex + side * 0.6, 2.4, 2, 3.6, C.skinShade);
  }
  // head shape (egg with a defined jaw)
  const head = () => { g.beginPath(); g.moveTo(0, -ry); g.bezierCurveTo(rx * 0.95, -ry, rx, -ry * 0.35, rx * 0.97, 2); g.bezierCurveTo(rx * 0.94, 14, rx * 0.64, ry * 0.8, rx * 0.26, ry * 0.97); g.quadraticCurveTo(0, ry * 1.04, -rx * 0.26, ry * 0.97); g.bezierCurveTo(-rx * 0.64, ry * 0.8, -rx * 0.94, 14, -rx * 0.97, 2); g.bezierCurveTo(-rx, -ry * 0.35, -rx * 0.95, -ry, 0, -ry); g.closePath(); };
  g.fillStyle = K(C.skin); head(); g.fill();
  if (FLAT) { hairShape(g, st, C); return; }
  g.save(); head(); g.clip();
  g.fillStyle = linGrad(g, -rx * st.lightX, 0, rx * st.lightX, 0, [alpha(C.skinShade, 0), alpha(C.skinShade, 0.0), alpha(C.skinShade, 0.42)]); g.fillRect(-rx - 2, -ry - 2, rx * 2 + 4, ry * 2 + 4);
  g.fillStyle = linGrad(g, 0, -ry, 0, -ry * 0.1, [alpha('#000', 0.28), alpha('#000', 0)]); g.fillRect(-rx, -ry, rx * 2, ry);
  g.fillStyle = linGrad(g, 0, ry * 0.45, 0, ry, [alpha(C.skinShade, 0), alpha(C.skinShade, 0.4)]); g.fillRect(-rx, ry * 0.4, rx * 2, ry * 0.7);
  if (glow) { g.fillStyle = radGrad(g, 0, ry * 0.9, 2, rx * 1.6, [alpha(glow, 0.38), alpha(glow, 0)]); g.fillRect(-rx, -ry, rx * 2, ry * 2.2); }
  g.restore();
  // cheeks
  ell(g, -fx * 0 + -9.5 + fx * 0.8, 10, 4.2, 2.6, alpha('#d77a6a', 0.14 + 0.1 * Math.max(0, e.smile))); ell(g, 9.5 + fx * 0.8, 10, 4.2, 2.6, alpha('#d77a6a', 0.14 + 0.1 * Math.max(0, e.smile)));
  // eyes
  const dEye = 9.6 * (1 - 0.28 * ay), ey = -2 + (e.lid > 1.1 ? -0.6 : 0);
  const lid = clamp(e.lid * (1 - blink), 0, 1.4);
  for (const side of [-1, 1]) {
    const lead = side * yaw > 0, wS = lead ? 1 - 0.5 * ay : 1 + 0.04 * ay, x = fx + side * dEye * (lead ? 1 - 0.1 * ay : 1);
    const ew = 5.5 * wS, eh = Math.max(0.3, 3.9 * Math.min(lid, 1.25) * (1 - 0.18 * e.squint));
    if (lid < 0.28) { stroke(g, [[x - ew, ey + 0.4], [x, ey + 1.5], [x + ew, ey + 0.4]], 1.9, C.brow); continue; }
    ell(g, x, ey, ew, eh, C.sclera);
    g.save(); g.beginPath(); g.ellipse(x, ey, ew, eh, 0, 0, Math.PI * 2); g.clip();
    const gx = clamp(gaze[0], -1, 1), gy = clamp(gaze[1], -1, 1), ix = x + gx * ew * 0.5, iy = ey + gy * eh * 0.45;
    ell(g, ix, iy, 3.0 * wS, 3.0, C.iris); ell(g, ix, iy, 1.45 * wS, 1.45, '#0a0808'); ell(g, ix - 0.9, iy - 1.0, 0.8, 0.8, '#ffffff');
    g.fillStyle = linGrad(g, 0, ey - eh, 0, ey - eh * 0.2, [alpha('#000', 0.3), alpha('#000', 0)]); g.fillRect(x - ew, ey - eh, ew * 2, eh);
    g.restore();
    stroke(g, [[x - ew - 0.2, ey + 0.2], [x - ew * 0.5, ey - eh * 1.02], [x + ew * 0.5, ey - eh * 1.02], [x + ew + 0.2, ey + 0.2]], 1.55, C.brow);
    stroke(g, [[x - ew * 0.8, ey + eh * 0.9], [x, ey + eh * 1.15 - 0.6 * e.squint], [x + ew * 0.8, ey + eh * 0.9]], 0.8, alpha(C.skinShade, 0.7));
    // brows
    const bx0 = fx + side * dEye * 0.42, bx1 = fx + side * dEye * 1.55 * (lead ? 1 - 0.18 * ay : 1);
    const asym = side > 0 ? e.browAsym * 3.2 : 0, base = ey - 8.4 - e.browY * 3.4 - asym;
    const inY = base - e.browIn * 3.1, outY = base + e.browIn * 1.3 + (e.browIn < 0 ? e.browIn * 1.4 : 0);
    g.strokeStyle = K(C.brow); g.lineCap = 'round'; g.lineWidth = 2.9 * (lead ? 1 - 0.25 * ay : 1);
    g.beginPath(); g.moveTo(bx0, inY); g.quadraticCurveTo((bx0 + bx1) / 2, Math.min(inY, outY) - 1.7, bx1, outY); g.stroke();
  }
  // nose
  const nx = fx * 1.15, ny = 6.5;
  if (ay > 0.55) { const dir = nearSign; g.fillStyle = C.skin; g.beginPath(); g.moveTo(nx + dir * 1, ny - 8); g.quadraticCurveTo(nx + dir * 8.5, ny + 1, nx + dir * 3, ny + 4.2); g.lineTo(nx - dir * 1, ny + 3); g.closePath(); g.fill(); stroke(g, [[nx + dir * 3, ny + 3.6], [nx + dir * 0.6, ny + 4.4]], 1, alpha(C.skinShade, 0.9)); }
  else {
    stroke(g, [[nx - nearSign * 2.2, -3], [nx - nearSign * 2.8, ny - 1.4]], 1.4, alpha(C.skinShade, 0.4));
    g.strokeStyle = K(alpha(C.skinShade, 0.9)); g.lineWidth = 1.2; g.lineCap = 'round';
    g.beginPath(); g.moveTo(nx - 3.8, ny + 0.6); g.quadraticCurveTo(nx - 4.6, ny + 3.8, nx - 1.6, ny + 3.8); g.stroke();
    g.beginPath(); g.moveTo(nx + 3.8, ny + 0.6); g.quadraticCurveTo(nx + 4.6, ny + 3.8, nx + 1.6, ny + 3.8); g.stroke();
    ell(g, nx + 0.6, ny - 0.8, 1.6, 1.1, alpha('#ffffff', 0.16));
  }
  drawMouth(g, fx * 1.05, 16.4, m, e, yaw, C);
  hairShape(g, st, C);
}

function hairShape(g, st, C) {
  const rx = D.rx, ry = D.ry, fx = st.yaw * rx * 0.28, ay = Math.abs(st.yaw);
  g.fillStyle = K(C.hair); g.beginPath();
  g.moveTo(-rx - 0.6, -7); g.bezierCurveTo(-rx - 3.5, -ry - 2, -rx * 0.55, -ry - 9, fx * 0.5 + 3, -ry - 8);
  g.bezierCurveTo(rx * 0.7, -ry - 7.5, rx + 4, -ry - 1, rx + 0.6, -7);
  g.lineTo(rx - 2.2, -13 - ay * 1.5); g.quadraticCurveTo(rx * 0.5, -22.5, fx + rx * 0.02, -23);   // side-swept front hairline (higher: real forehead)
  g.quadraticCurveTo(-rx * 0.45, -21.5, -rx * 0.8, -13.5); g.lineTo(-rx + 2.2, -9); g.closePath(); g.fill();
  if (FLAT) return;
  g.strokeStyle = alpha(C.hairHi, 0.4); g.lineWidth = 1.1; g.lineCap = 'round';
  for (const [a, b, c, d] of [[-15, -ry - 3, -3, -ry - 6.5], [-4, -ry - 5, 8, -ry - 5.5], [6, -ry - 4, 17, -ry + 0], [-21, -ry + 4, -13, -ry - 2]]) { g.beginPath(); g.moveTo(a + fx * 0.4, b); g.quadraticCurveTo((a + c) / 2 + fx * 0.4, Math.min(b, d) - 1.6, c + fx * 0.4, d); g.stroke(); }
  g.fillStyle = alpha('#000', 0.16); g.beginPath(); g.ellipse(fx, -23.4, rx * 0.72, 2.6, 0, 0, Math.PI); g.fill();
}

function drawMouth(g, hx, my, m, e, yaw, C) {
  const ay = Math.abs(yaw), open = clamp(m.open + (e.jaw || 0), 0, 1.15);
  const w = 9.2 * (1 + 0.34 * clamp(m.wide + e.smile * 0.45, -1, 1)) * (1 - 0.42 * m.round) * (1 - 0.22 * ay);
  const lift = e.smile * 4.4 * (1 - 0.7 * m.round), sm = e.smirk || 0;
  const cL = [hx - w, my - lift + sm * 0.4], cR = [hx + w, my - lift - sm * 2.6];
  if (FLAT) return;
  if (open < 0.07) {
    const press = m.press ? 0.5 : 0;
    ell(g, hx, my + 3 + press * 0.3, w * 0.62, 2.1, alpha(C.lip, 0.95));
    g.strokeStyle = C.lipDark; g.lineWidth = 1.7; g.lineCap = 'round'; g.beginPath(); g.moveTo(cL[0], cL[1]); g.quadraticCurveTo(hx, my + 0.9 + press - e.smile * 0.6, cR[0], cR[1]); g.stroke();
    ell(g, hx, my - 2.2 + press * 0.4, w * 0.52, 1.5, alpha(C.lip, 0.6));
    return;
  }
  const top = my - 1.2 - open * 0.3, bot = my + 3 + open * 11;
  g.save(); g.beginPath(); g.moveTo(cL[0], cL[1]); g.quadraticCurveTo(hx, top - 1.5, cR[0], cR[1]); g.quadraticCurveTo(hx, bot + 2, cL[0], cL[1]); g.closePath();
  g.fillStyle = C.mouthIn; g.fill(); g.clip();
  const tdepth = m.teeth === 0 ? 0 : (m.teeth === 3 ? 4.4 : Math.min(5.2, 2 + open * 5));
  if (m.teeth >= 1 && tdepth > 0) { g.fillStyle = C.teeth; g.beginPath(); g.roundRect(hx - w * 0.82, top - 1.5, w * 1.64, tdepth + 1.5, 1.6); g.fill(); }
  if (m.teeth === 2 && open > 0.12) { g.fillStyle = C.teeth; g.beginPath(); g.roundRect(hx - w * 0.74, bot - 3.4, w * 1.48, 3.8, 1.4); g.fill(); }
  if (open > 0.28 || m.tongue > 0.5) { g.fillStyle = C.tongue; g.beginPath(); g.ellipse(hx, bot - 1.2 - (m.tongue > 0.5 ? open * 3 : 0), w * 0.5, 2.2 + m.tongue * 2.2, 0, 0, Math.PI * 2); g.fill(); }
  g.restore();
  g.strokeStyle = C.lip; g.lineCap = 'round'; g.lineWidth = 2.5; g.beginPath(); g.moveTo(cL[0], cL[1]); g.quadraticCurveTo(hx, top - 2.6, cR[0], cR[1]); g.stroke();
  g.lineWidth = 3.3; g.beginPath(); g.moveTo(cL[0] + 1, cL[1] + 0.8); g.quadraticCurveTo(hx, bot + (m.teeth === 3 ? -1.2 : 4.2), cR[0] - 1, cR[1] + 0.8); g.stroke();
  if (m.teeth === 3) { g.fillStyle = alpha(C.lip, 0.95); g.beginPath(); g.ellipse(hx, top + 6.2, w * 0.78, 2.2, 0, 0, Math.PI * 2); g.fill(); }
  ell(g, hx, bot + 6.2, w * 0.4, 1.4, alpha(C.skinShade, 0.45));
}

// ---------------------------------------------------------------- the figure
// o: { x, y, s, facing, pose|gesture, expr, yaw, gaze:'cam'|[x,y], t, globalT, speak, idle, intensity, rim, shadow, prop:{type:'phone'|'mug'|'pen', hand:'L'|'R', glow, tilt, screen}, faceGlow, posture:'stand'|'sit', walk:{phase, amp}, rot, bust, seed, dim, alpha }
export function drawMentor(g, o) {
  const s = o.s ?? 1, f = o.facing ?? 1, t = o.t ?? 0, gT = o.globalT ?? 0, seed = o.seed ?? 0;
  const pose = gesture(o.pose), e = { ...expr(o.expr) };
  const speak = !!o.speak && speakingAt(gT);
  const m = o._mouth || (o.speak ? mouthAt(gT, { intensity: o.intensity ?? 1 }) : { open: 0, wide: 0, round: 0, tongue: 0, teeth: 0, press: 0 });
  const emph = o.speak ? emphasisAt(gT) : 0, idle = o.idle !== false;
  // idle motion
  const breath = idle ? Math.sin(t * 1.9 + seed) * 1.3 : 0, sway = idle ? noise(t * 0.35 + seed, 3) * 1.6 : 0;
  const tiltIdle = idle ? noise(t * 0.5 + seed, 7) * (speak ? 0.035 : 0.018) : 0;
  const blink = o.blink ?? (idle ? blinkAt(t, seed) : 0);
  const yaw = clamp((o.yaw ?? 0) + (pose.turn || 0) + (idle && speak ? noise(t * 0.6 + seed, 11) * 0.05 : 0), -1, 1);
  let gaze = o.gaze === 'cam' || o.gaze == null ? [(e.gaze ? e.gaze[0] : -yaw * 0.9), e.gaze ? e.gaze[1] : 0.05] : o.gaze;
  if (idle) gaze = [gaze[0] + noise(t * 0.9 + seed, 21) * 0.07, gaze[1] + noise(t * 1.3 + seed, 22) * 0.05];
  e.browY += emph * 0.45;
  const lightX = (o.rim?.dir?.[0] ?? -0.8) <= 0 ? 1 : -1;
  const rimC = o.rim === false ? null : { color: '#ffd9a8', dir: [-0.8, -0.5], w: 4, ...(o.rim || {}) };
  const sit = o.posture === 'sit', seatDrop = sit ? 42 : 0, ay = Math.abs(yaw), bodyW = 1 - 0.28 * ay;
  const st = { yaw, e, m, gaze, blink, glow: o.faceGlow, lightX };
  const nod = emph * 2.4 + pose.nodBase;
  const walk = o.walk ? { p: o.walk.phase, a: o.walk.amp ?? 1 } : null;

  const body = (flat, grew) => {
    FLAT = flat || null; FLAT_GROW = grew || 0;
    const C = LOOK;
    g.save(); g.translate(o.x + (flat ? rimC.dir[0] * rimC.w : 0), o.y + (flat ? rimC.dir[1] * rimC.w : 0)); g.scale(f * s, s);
    if (o.rot) { g.translate(0, D.hipY); g.rotate(o.rot); g.translate(0, -D.hipY); }
    const bob = walk ? Math.abs(Math.sin(walk.p)) * -3 * walk.a : 0;
    g.translate(sway * 0.4, bob);
    // legs
    const hipY = D.hipY + seatDrop, swing = walk ? Math.sin(walk.p) * 26 * walk.a * clamp(ay * 1.3, 0.2, 1) : 0;
    const legs = () => {
      for (const side of [-1, 1]) {
        const hx = side * 12 * bodyW, sw = swing * side;
        const knee = sit ? [side * 19, hipY + 6] : [side * 12 * bodyW + sw * 0.5, -62 - Math.abs(sw) * 0.15], ank = sit ? [side * 21, -8] : [side * 13 * bodyW + sw, -8 - Math.max(0, -sw * side) * 0.4];
        stroke(g, [[hx, hipY], knee], grow(sit ? 27 : 26), C.jeans); stroke(g, [knee, ank], grow(sit ? 22 : 23), C.jeans);
        const toeDir = ay > 0.5 ? Math.sign(yaw) : 0; ell(g, ank[0] + toeDir * 6 + side * 2 * (1 - ay), -5, 15 + ay * 4, 7.4, C.shoe); if (!FLAT) { ell(g, ank[0] + toeDir * 6 + side * 2 * (1 - ay), -1.6, 15.4 + ay * 4, 2.6, C.sole); }
      }
    };
    if (!o.bust) legs();
    if (o.bust) { g.beginPath(); g.rect(-120, -500, 240, 500 + D.shY + 72); g.clip(); }
    // upper body group (lean + sit drop)
    g.save(); g.translate(0, seatDrop + breath * 0.4); g.translate(0, D.hipY); g.scale(1 + 0.05 * pose.lean, 1 + 0.03 * pose.lean); g.translate(0, -D.hipY);
    g.save(); g.scale(bodyW, 1);
    // hood roll behind neck
    ell(g, 0, D.shY - 7, 33, 15, C.hoodieShade);
    // torso
    const sy = D.shY + (pose.sh ? -4 * pose.sh : 0), hy = D.hipY + 14;
    const torso = () => { g.beginPath(); g.moveTo(-20, sy - 8); g.quadraticCurveTo(-39, sy - 4, -41, sy + 18); g.lineTo(-37, hy - 6); g.quadraticCurveTo(-37, hy + 8, -31, hy + 8); g.lineTo(31, hy + 8); g.quadraticCurveTo(37, hy + 8, 37, hy - 6); g.lineTo(41, sy + 18); g.quadraticCurveTo(39, sy - 4, 20, sy - 8); g.quadraticCurveTo(0, sy + 4, -20, sy - 8); g.closePath(); };
    g.fillStyle = K(C.hoodie); torso(); g.fill();
    if (!FLAT) {
      g.save(); torso(); g.clip();
      g.fillStyle = linGrad(g, -lightX * 40, 0, lightX * 40, 0, [alpha('#fff', 0.07), alpha('#000', 0), alpha('#000', 0.3)]); g.fillRect(-46, sy - 10, 92, hy - sy + 20);
      g.restore();
      // neck + V opening
      poly2(g, [[-9, D.neckY], [9, D.neckY], [10, sy - 4], [-10, sy - 4]], C.skin); ell(g, 0, sy - 5, 12.5, 6.5, C.skin);
      ell(g, 0, sy - 12, 10, 7, alpha(C.skinShade, 0.55));
      g.strokeStyle = C.hoodieShade; g.lineWidth = 5; g.lineCap = 'round'; g.beginPath(); g.moveTo(-20, sy - 10); g.quadraticCurveTo(-18, sy + 12, 0, sy + 14); g.quadraticCurveTo(18, sy + 12, 20, sy - 10); g.stroke();
      g.strokeStyle = C.hoodieLight; g.lineWidth = 1.2; g.beginPath(); g.moveTo(-22, sy - 8); g.quadraticCurveTo(-19, sy + 14, 0, sy + 16.5); g.quadraticCurveTo(19, sy + 14, 22, sy - 8); g.stroke();
      // drawstrings
      for (const sd of [-1, 1]) { stroke(g, [[sd * 5, sy + 13], [sd * 7.5, sy + 30], [sd * 6, sy + 44]], 1.8, C.cord); ell(g, sd * 6, sy + 46, 1.5, 3, C.cord); }
      // pocket + hem
      g.fillStyle = alpha(C.hoodieShade, 0.55); g.beginPath(); g.moveTo(-23, hy - 30); g.lineTo(23, hy - 30); g.lineTo(30, hy + 2); g.lineTo(-30, hy + 2); g.closePath(); g.fill();
      stroke(g, [[-23, hy - 30], [-30, hy + 2]], 1.2, C.hoodieLight); stroke(g, [[23, hy - 30], [30, hy + 2]], 1.2, C.hoodieLight);
      g.fillStyle = alpha('#000', 0.35); g.beginPath(); g.roundRect(-33, hy + 2, 66, 8, 3); g.fill();
      // soft fabric folds
      for (const [x1, y1, x2, y2] of [[-30, sy + 40, -22, sy + 74], [28, sy + 36, 22, sy + 70], [-4, hy - 40, -2, hy - 32]]) stroke(g, [[x1, y1], [x2, y2]], 1.4, alpha('#000', 0.22));
    }
    g.restore();
    // arms
    const shoulders = { L: [-32 * bodyW, sy + 10], R: [32 * bodyW, sy + 10] };
    const arms = {};
    for (const [key, side] of [['L', -1], ['R', 1]]) {
      const tgt = pose[key], z = tgt[2] || 0, flare = pose['e' + key] || 0;
      let hx = tgt[0] * (1 - 0.18 * ay) + (walk ? 0 : 0), hy2 = tgt[1] + (emph > 0 && (pose['hs' + key] !== 'relaxed' || Math.abs(tgt[1] + 116) > 20) ? -emph * 4 : 0) + (idle ? breath * 0.3 : 0);
      let wp = [hx, hy2];
      if (walk && tgt[1] > -130) { const sw = Math.sin(walk.p + (side > 0 ? Math.PI : 0)) * 26 * walk.a * clamp(ay * 1.3, 0.2, 1); wp = [side * 40 * bodyW + sw, -112]; }
      arms[key] = { ...ik(shoulders[key], wp, D.upper * (1 - 0.3 * z), D.fore * (1 - 0.4 * z), side, flare), z, side, hs: pose['hs' + key], over: wp[1] < D.shY - 18 - (D.shY > -208 ? 0 : 0) };
    }
    const drawArm = (key) => {
      const a = arms[key], S0 = shoulders[key], side = a.side;
      stroke(g, [S0, a.el], grow(21), C.hoodie); stroke(g, [a.el, a.wr], grow(18.5), C.hoodie);
      if (!FLAT) { stroke(g, [[a.el[0] - side * 5, a.el[1] - 1], [a.el[0] + side * 3, a.el[1] + 5]], 1.3, alpha('#000', 0.3)); }
      const ang = Math.atan2(a.wr[1] - a.el[1], a.wr[0] - a.el[0]);
      const cx = a.wr[0] - Math.cos(ang) * 1, cy = a.wr[1] - Math.sin(ang) * 1;
      if (!FLAT) { g.save(); g.translate(cx, cy); g.rotate(ang); g.fillStyle = C.hoodieShade; g.beginPath(); g.roundRect(-5, -9.6, 7, 19.2, 3); g.fill(); g.restore(); }
      hand(g, a.wr[0] + Math.cos(ang) * 4, a.wr[1] + Math.sin(ang) * 4, ang, a.hs, side, a.z, a.hs === 'open' ? -side : side);
      if (o.prop && (o.prop.hand || 'R') === key) prop(g, o.prop, a.wr[0] + Math.cos(ang) * 3, a.wr[1] + Math.sin(ang) * 3, ang, side);
    };
    const under = ['L', 'R'].filter(k => !arms[k].over), over = ['L', 'R'].filter(k => arms[k].over);
    under.forEach(drawArm);
    g.restore(); // bodyW scale
    // head (not scaled by bodyW)
    g.save(); g.translate(yaw * 3 + sway * 0.6, D.headY + nod * 1.2 + (sit ? 0 : 0) + breath * 0.5 + (pose.sh ? -3 * pose.sh : 0) + (1 - (1 + 0.03 * pose.lean)) * 0);
    g.rotate(pose.tilt + tiltIdle + nod * 0.012);
    drawHead(g, st, C);
    g.restore();
    g.save(); g.scale(bodyW, 1); over.forEach(drawArm); g.restore();
    g.restore(); // upper group
    g.restore();
    FLAT = null; FLAT_GROW = 0;
  };

  g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha;
  if (o.shadow !== false && !o.rot && !o.bust) { g.fillStyle = 'rgba(0,0,0,.3)'; g.beginPath(); g.ellipse(o.x, o.y + 3, 46 * s, 8 * s, 0, 0, Math.PI * 2); g.fill(); }
  if (rimC) body(rimC.color, 2.4);
  if (o.dim) g.filter = `brightness(${1 - o.dim})`;
  body(null, 0);
  g.restore();
}

// stage position of the head centre + radius (for glows, bubbles, captions)
export function headPos(o) { const s = o.s ?? 1; return [o.x + (o.yaw || 0) * 3 * s * (o.facing ?? 1), o.y + D.headY * s + (o.posture === 'sit' ? 42 * s : 0), D.ry * s]; }

// head-and-shoulders close-up: places the head centre at (cx, cy); scale 1 ≈ 3.4 px per unit at 1080p works for a tight shot
export function drawMentorBust(g, cx, cy, o = {}) {
  const s = o.s ?? 3.4;
  drawMentor(g, { ...o, bust: true, shadow: false, x: cx, y: cy - (D.headY + (o.posture === 'sit' ? 42 : 0)) * s, s });
}

// reference sheet used by /mentor-character: turnaround + expressions + mouth shapes on one canvas
export function drawCharacterSheet(g, W, H, t = 0) {
  g.fillStyle = '#15171d'; g.fillRect(0, 0, W, H);
  const lab = (txt, x, y, size = 22) => { g.fillStyle = '#9aa3b5'; g.font = `600 ${size}px sans-serif`; g.textAlign = 'center'; g.fillText(txt, x, y); };
  lab('THE YOUNG WISE MENTOR · character reference', W / 2, H * 0.05, 30);
  const sc = (H * 0.42) / HEIGHT, baseY = H * 0.5;
  [['front', 0], ['3/4', 0.6], ['side', 1], ['3/4 (other way)', -0.6]].forEach(([name, yaw], i) => {
    const x = W * (0.14 + i * 0.24);
    drawMentor(g, { x, y: baseY, s: sc, yaw, pose: 'rest', expr: 'calm', idle: false, rim: { color: '#9fb6ff', dir: [-0.8, -0.4], w: 3 } }); lab(name, x, baseY + 32);
  });
  const names = ['calm', 'explaining', 'serious', 'warning', 'confident', 'encouraging', 'regret', 'amused', 'frustrated', 'surprised'];
  names.forEach((n, i) => { const x = W * (0.07 + i * 0.096), y = H * 0.665; drawMentorBust(g, x, y, { s: 1.15, expr: n, pose: 'rest', idle: false, rim: false }); lab(n, x, y + 122, 17); });
  const vis = ['REST', 'MBP', 'FV', 'TH', 'S', 'TD', 'K', 'L', 'R', 'W', 'U', 'O', 'OW', 'AA', 'E', 'I', 'EE', 'SH'];
  vis.forEach((n, i) => { const x = W * (0.055 + i * 0.0525), y = H * 0.88; drawMentorBust(g, x, y, { s: 0.8, idle: false, rim: false, expr: 'calm', blink: 0, _mouth: VIS_PREVIEW(n) }); lab(n, x, y + 74, 14); });
}
import { VISEMES } from './lipsync.js';
function VIS_PREVIEW(n) { const v = VISEMES[n]; return { open: v.open, wide: v.wide, round: v.round, tongue: v.tongue, teeth: v.teeth, press: v.press || 0 }; }
