// engine/lipsync.js — word timestamps -> mouth shapes (visemes), deterministic, no audio analysis at render time.
// Input: E.words = [{word, start, end}] (global seconds, from Whisper or the user's timestamped script).
// Method: each word is split into phoneme-like units by spelling rules, units share the word's duration
// (vowels longer than consonants), mouth shapes are keyed at unit centres (leading the sound by ~40 ms)
// and smoothly interpolated. Gaps between words close the mouth. Accuracy is "good animation", not
// phoneme-perfect: it follows the real word timing, so the mouth stops when the voice stops.
import { E, clamp, lerp, ease } from './core.js';

// open: jaw (0..1) · wide: -1 pursed … +1 spread · round: lip rounding 0..1 · teeth: 0 none,1 upper,2 both,3 lower-lip-tucked (F/V) · tongue 0..1
export const VISEMES = {
  REST: { open: 0.0, wide: 0.0, round: 0.0, teeth: 0, tongue: 0 },
  MBP:  { open: 0.0, wide: -0.2, round: 0.0, teeth: 0, tongue: 0, press: 1 },
  FV:   { open: 0.14, wide: 0.1, round: 0.0, teeth: 3, tongue: 0 },
  TH:   { open: 0.18, wide: 0.2, round: 0.0, teeth: 1, tongue: 1 },
  S:    { open: 0.1, wide: 0.55, round: 0.0, teeth: 2, tongue: 0 },
  TD:   { open: 0.2, wide: 0.25, round: 0.0, teeth: 1, tongue: 0.6 },
  K:    { open: 0.32, wide: 0.1, round: 0.0, teeth: 0, tongue: 0.2 },
  L:    { open: 0.3, wide: 0.2, round: 0.0, teeth: 1, tongue: 1 },
  R:    { open: 0.26, wide: -0.1, round: 0.4, teeth: 0, tongue: 0.1 },
  W:    { open: 0.2, wide: -0.5, round: 1.0, teeth: 0, tongue: 0 },
  U:    { open: 0.3, wide: -0.4, round: 0.9, teeth: 0, tongue: 0 },
  O:    { open: 0.72, wide: -0.3, round: 0.75, teeth: 0, tongue: 0 },
  OW:   { open: 0.58, wide: -0.1, round: 0.5, teeth: 0, tongue: 0 },
  AA:   { open: 1.0, wide: 0.15, round: 0.0, teeth: 1, tongue: 0.1 },
  E:    { open: 0.55, wide: 0.5, round: 0.0, teeth: 1, tongue: 0.1 },
  I:    { open: 0.4, wide: 0.7, round: 0.0, teeth: 1, tongue: 0.1 },
  EE:   { open: 0.28, wide: 1.0, round: 0.0, teeth: 2, tongue: 0 },
  SH:   { open: 0.25, wide: -0.15, round: 0.65, teeth: 2, tongue: 0 },
};

// spelling rules, longest match first
const RULES = [
  ['tion', ['SH', 'U']], ['sion', ['SH', 'U']], ['ough', ['OW', 'FV']], ['igh', ['AA', 'EE']],
  ['th', ['TH']], ['sh', ['SH']], ['ch', ['SH']], ['ph', ['FV']], ['wh', ['W']], ['ck', ['K']], ['ng', ['K']], ['qu', ['K', 'W']],
  ['oo', ['U']], ['ou', ['OW']], ['ow', ['OW']], ['oi', ['O', 'EE']], ['oy', ['O', 'EE']], ['ee', ['EE']], ['ea', ['EE']], ['ie', ['EE']],
  ['ai', ['E', 'EE']], ['ay', ['E', 'EE']], ['oa', ['O']], ['ew', ['U']], ['au', ['O']], ['aw', ['O']], ['ey', ['E']],
  ['a', ['AA']], ['e', ['E']], ['i', ['I']], ['o', ['O']], ['u', ['U']], ['y', ['EE']],
  ['m', ['MBP']], ['b', ['MBP']], ['p', ['MBP']], ['f', ['FV']], ['v', ['FV']], ['w', ['W']],
  ['l', ['L']], ['r', ['R']], ['s', ['S']], ['z', ['S']], ['x', ['K', 'S']], ['j', ['SH']],
  ['t', ['TD']], ['d', ['TD']], ['n', ['TD']], ['k', ['K']], ['g', ['K']], ['c', ['K']], ['h', ['K']], ['q', ['K']],
];
const VOWELS = new Set(['AA', 'E', 'I', 'O', 'OW', 'U', 'EE']);
const cache = new Map();

export function wordToVisemes(word) {
  const w = word.toLowerCase().replace(/[^a-z]/g, '');
  if (!w) return [];
  if (cache.has(w)) return cache.get(w);
  const out = []; let i = 0;
  while (i < w.length) {
    // silent trailing 'e' (make, time) and doubled letters
    if (i === w.length - 1 && w[i] === 'e' && w.length > 2 && !'aeiou'.includes(w[i - 1])) { i++; continue; }
    if (i > 0 && w[i] === w[i - 1] && !'aeiou'.includes(w[i])) { i++; continue; }
    let hit = null;
    for (const [pat, vs] of RULES) if (w.startsWith(pat, i)) { hit = [pat, vs]; break; }
    if (!hit) { i++; continue; }
    out.push(...hit[1]); i += hit[0].length;
  }
  // collapse immediate repeats
  const res = out.filter((v, k) => v !== out[k - 1]);
  cache.set(w, res);
  return res;
}

let built = null, builtFor = null;
function build() {
  if (built && builtFor === E.words) return built;
  const keys = [{ t: -10, v: 'REST' }]; // keyframes {t, v, weight}
  const words = E.words || [];
  for (let wi = 0; wi < words.length; wi++) {
    const { word, start, end } = words[wi];
    const vs = wordToVisemes(word);
    const lead = 0.04, dur = Math.max(0.06, end - start);
    if (!vs.length) continue;
    const weights = vs.map(v => (VOWELS.has(v) ? 2.2 : v === 'MBP' || v === 'TD' ? 0.6 : 0.9));
    const total = weights.reduce((a, b) => a + b, 0);
    let acc = start - lead;
    vs.forEach((v, k) => {
      const d = (dur * weights[k]) / total;
      keys.push({ t: acc + d / 2, v, w: Math.min(1, 0.55 + d * 5) });
      acc += d;
    });
    const next = words[wi + 1];
    const gap = next ? next.start - end : 9;
    if (gap > 0.14) { keys.push({ t: end + 0.04, v: 'REST' }); if (next) keys.push({ t: next.start - 0.08, v: 'REST' }); }
  }
  keys.sort((a, b) => a.t - b.t);
  built = keys; builtFor = E.words;
  return keys;
}

const NUM = ['open', 'wide', 'round', 'tongue'];
function pick(key) { const v = VISEMES[key.v]; const k = key.w ?? 1; return { open: v.open * k, wide: v.wide * k, round: v.round * k, tongue: v.tongue, teeth: v.teeth, press: v.press || 0 }; }

// mouth parameters at a global time
export function mouthAt(globalT, o = {}) {
  const keys = build(), amp = o.intensity ?? 1;
  if (!E.words || !E.words.length) return { ...VISEMES.REST, press: 0, speaking: false };
  let lo = 0, hi = keys.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (keys[m].t <= globalT) lo = m; else hi = m; }
  const a = keys[lo], b = keys[hi];
  const pa = pick(a), pb = pick(b), k = ease.sine(clamp((globalT - a.t) / Math.max(1e-3, b.t - a.t)));
  const m = {}; for (const n of NUM) m[n] = lerp(pa[n], pb[n], k);
  m.teeth = k < 0.5 ? pa.teeth : pb.teeth; m.press = lerp(pa.press, pb.press, k);
  m.open *= amp; m.speaking = !(a.v === 'REST' && b.v === 'REST') && globalT > keys[1]?.t - 0.2;
  return m;
}

export function speakingAt(globalT) {
  return (E.words || []).some(w => globalT >= w.start - 0.05 && globalT <= w.end + 0.08);
}

// pulse 0..1 on stressed words (long words, words before a pause, sentence ends) -> use for nods, brow flashes, gesture beats
export function emphasisAt(globalT) {
  const ws = E.words || []; let best = 0;
  for (let i = 0; i < ws.length; i++) {
    const w = ws[i]; if (w.start > globalT) break; if (globalT - w.start > 0.5) continue;
    const gap = ws[i + 1] ? ws[i + 1].start - w.end : 1;
    const stressed = w.word.replace(/[^a-z]/gi, '').length >= 6 || gap > 0.3 || /[.!?]$/.test(w.word);
    if (!stressed) continue;
    const u = (globalT - w.start) / 0.5; best = Math.max(best, Math.exp(-3.2 * u) * Math.sin(Math.min(1, u * 4) * Math.PI * 0.5));
  }
  return best;
}

// time of the next pause (>= minGap s) after globalT, or null — handy for ending a gesture on a breath
export function nextPause(globalT, minGap = 0.25) {
  const ws = E.words || [];
  for (let i = 0; i < ws.length - 1; i++) if (ws[i].end >= globalT && ws[i + 1].start - ws[i].end >= minGap) return ws[i].end;
  return null;
}
