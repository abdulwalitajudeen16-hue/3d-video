// shots/01_demo.js — 7 shots that show the Mentor's two modes: PRESENTER (s001, s007) and STORY (s002–s006).
// Rule of thumb: speak:true + globalT = lip-sync from real word timings; gaze:'cam' = looks into the lens.
import { E, V, registerShot, layer, ease, key, lerp, wordTime, glow, alpha } from '/engine/core.js';
import { drawMentor, drawMentorBust, gestureAt, exprAt, headPos } from '/engine/mentor2d.js';
import * as FX from '/engine/fx2d.js';
import { studio, bedroom, deskRoom } from '../sets/rooms.js';

const T = (w, after = 0, fb = 0) => wordTime(w, after) ?? fb;   // global time of a spoken word

// s001 PRESENTER hook — direct to camera, serious, gestures timed to words, slow push-in
registerShot('s001', { draw(g, t, info) {
  const gt = info.globalT, p = info.p ?? t / info.dur;
  const cam = { z: 1 + 0.07 * ease.inOut(t / info.dur), y: -10 * p };
  const { GY, M } = studio(g, t, cam);
  const a = T('stealing', 0, 2.0) - info.shot.start, b = T('future', 0, 4.4) - info.shot.start;
  layer(g, cam, 1, g => drawMentor(g, { x: E.W / 2, y: E.H * V(1.22, 0.98), s: V(3.1, 4.1), speak: true, globalT: gt, t,
    pose: gestureAt(t, [[0, 'rest'], [0.5, 'openHands'], [a - 0.2, 'openOne'], [b - 0.1, 'pointAtViewer'], [b + 1.6, 'palmsUp']], 0.5),
    expr: exprAt(t, [[0, 'direct'], [a - 0.3, 'serious'], [b - 0.3, 'warning']]), rim: { color: M.rim, dir: [-0.8, -0.5], w: 4 } }));
  FX.dust(g, t, { count: 26, color: '#ffe2bd', a: 0.25 });
} });

// s002 STORY — wakes up: lies in bed, then sits up (rot animates the whole body about the hips)
registerShot('s002', { draw(g, t, info) {
  const cam = { z: 1.02 + 0.03 * (t / info.dur), x: 20 };
  const { GY, M, bed } = bedroom(g, t, cam);
  const sc = V(2.1, 1.9), up = ease.inOut((t - 0.9) / 0.9), hipY = GY - 140;        // hip rests on the mattress; root y follows from the pose
  layer(g, cam, 1, g => drawMentor(g, { x: lerp(bed.x + 300, bed.x + bed.w * 0.8, up), y: hipY + (120 - 42 * up) * sc, s: sc, rot: -Math.PI / 2 * (1 - up), posture: up > 0.5 ? 'sit' : 'stand', t, shadow: false,
    pose: 'rest', expr: 'tired', blink: t < 0.7 ? 1 : undefined, rim: { color: M.rim, dir: [0.6, -0.6], w: 3 } }));
} });

// s003 STORY — sits on the bed edge, picks up the phone (prop attaches to the hand)
registerShot('s003', { draw(g, t, info) {
  const cam = { z: 1.06, x: 10 }; const { GY, M, bed } = bedroom(g, t, cam);
  layer(g, cam, 1, g => drawMentor(g, { x: bed.x + bed.w * 0.8, y: GY + 8, s: V(2.1, 1.9), posture: 'sit', t, shadow: false,
    pose: gestureAt(t, [[0, 'rest'], [0.5, 'phoneHold']], 0.6), prop: t > 0.9 ? { type: 'phone', hand: 'R', glow: '#9fd8ff' } : null, gaze: [0.1, t > 0.9 ? 0.8 : 0], expr: 'calm', yaw: 0.15, rim: { color: M.rim, dir: [0.6, -0.6], w: 3 } }));
} });

// s004 STORY — scrolling: screen glow on the face, eyes down, small scroll motion
registerShot('s004', { draw(g, t, info) {
  const cam = { z: 1.14 + 0.05 * (t / info.dur), x: 40 }; const { GY, M, bed } = bedroom(g, t, cam);
  layer(g, cam, 1, g => drawMentor(g, { x: bed.x + bed.w * 0.8, y: GY + 8, s: V(2.1, 1.9), posture: 'sit', t, shadow: false, faceGlow: '#9fd8ff',
    pose: { ...gestureAt(t, [[0, 'phoneHold']]), R: [24, -176 + Math.sin(t * 5) * 3, 0.25] }, prop: { type: 'phone', hand: 'R', glow: '#9fd8ff', tilt: 0.08 }, gaze: [0.1, 0.85], expr: 'calm', yaw: 0.2, rim: { color: '#9fd8ff', dir: [-0.6, -0.4], w: 3 } }));
} });

// s005 STORY — the wall clock spins; he looks up in surprise, hands to head
registerShot('s005', { draw(g, t, info) {
  const cam = { z: 1.04 + 0.04 * ease.inOut(t / info.dur) };
  const { GY, M, desk } = deskRoom(g, t, cam, { clockT: t * 2400 });
  layer(g, cam, 1, g => drawMentor(g, { x: E.W / 2 - V(220, 0), y: GY, s: V(2.1, 1.9), t, posture: 'sit',
    pose: gestureAt(t, [[0, 'rest'], [0.9, 'handsOnHead']], 0.4), expr: exprAt(t, [[0, 'calm'], [0.8, 'surprised']], 0.25), gaze: t < 0.8 ? [0.2, 0.2] : [0.6, -0.6], yaw: 0.25, rim: { color: M.rim, dir: [-0.8, -0.5], w: 4 } }));
  desk();
} });

// s006 STORY — at the desk, frustrated, rubs temples; slow push-in
registerShot('s006', { draw(g, t, info) {
  const cam = { z: 1.05 + 0.08 * ease.inOut(t / info.dur) };
  const { GY, M, desk } = deskRoom(g, t, cam, { clockT: 5400 });
  layer(g, cam, 1, g => drawMentor(g, { x: E.W / 2 - V(180, 0), y: GY, s: V(2.1, 1.9), t, posture: 'sit',
    pose: gestureAt(t, [[0, 'rest'], [0.4, 'rubTemples']], 0.5), expr: 'frustrated', gaze: [0, 0.5], rim: { color: M.rim, dir: [-0.8, -0.5], w: 4 } }));
  desk();
} });

// s007 PRESENTER CTA — tight bust, direct to camera, reassuring
registerShot('s007', { draw(g, t, info) {
  const gt = info.globalT, cam = { z: 1 + 0.05 * (t / info.dur) };
  const { GY, M } = studio(g, t, cam);
  layer(g, cam, 1, g => drawMentorBust(g, E.W / 2, E.H * V(0.44, 0.42), { s: V(5.2, 4.6), speak: true, globalT: gt, t,
    pose: 'rest', expr: exprAt(t, [[0, 'reassuring'], [2.2, 'encouraging']]), rim: { color: M.rim, dir: [-0.8, -0.5], w: 5 } }));
} });
