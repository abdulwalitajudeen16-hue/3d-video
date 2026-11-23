// tools/lipsync_curve.mjs — print the mouth-open curve the renderer will use (50 samples/s) as JSON.
//   node tools/lipsync_curve.mjs projects/<slug>  ->  {"fps":50,"open":[…],"speaking":[…]}
// Runs the real engine/lipsync.js in Node (no browser needed), so lipsync_check.py compares exactly what gets drawn.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const proj = path.resolve(process.argv[2] || '.');
const w = JSON.parse(fs.readFileSync(path.join(proj, 'timeline', 'words.json'), 'utf8'));
globalThis.document = globalThis.document || { createElement: () => ({ getContext: () => ({}) }) };
const { E } = await import(pathToFileURL(path.join(ROOT, 'engine', 'core.js')).href);
const { mouthAt, speakingAt } = await import(pathToFileURL(path.join(ROOT, 'engine', 'lipsync.js')).href);
E.words = w.words || w;
const dur = (E.words.at(-1)?.end ?? 0) + 1, fps = 50, open = [], speaking = [];
for (let i = 0; i < dur * fps; i++) { const t = i / fps, m = mouthAt(t); open.push(+Math.max(0, m.open).toFixed(3)); speaking.push(speakingAt(t) ? 1 : 0); }
console.log(JSON.stringify({ fps, open, speaking }));
