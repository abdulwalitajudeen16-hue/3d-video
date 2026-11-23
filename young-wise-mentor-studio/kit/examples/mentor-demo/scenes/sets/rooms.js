// sets/rooms.js — three reusable rooms for the Mentor: studio (presenter backdrop), bedroom, desk room.
// Every set anchors to GY (floor line) and CX, extends walls/floor past the frame, and takes colours from mood().
import { E, V, mood, layer, rr, seg, circle, ring, linGrad, radGrad, glow, alpha, shade, rng } from '/engine/core.js';
import * as FX from '/engine/fx2d.js';

export const GY = () => E.H * V(0.94, 0.8);

function wallAndFloor(g, cam, M, GYv) {
  layer(g, cam, 0.35, (g) => {
    g.fillStyle = linGrad(g, 0, -E.H, 0, GYv, [M.dark, M.wall]); g.fillRect(-E.W, -E.H, E.W * 3, GYv + E.H);
    g.fillStyle = alpha('#000', 0.18); g.fillRect(-E.W, GYv - 26, E.W * 3, 26);         // skirting
  });
  layer(g, cam, 0.7, (g) => {
    g.fillStyle = linGrad(g, 0, GYv - 26, 0, GYv + 600, [shade(M.floor, 0.08), M.dark]); g.fillRect(-E.W, GYv - 26, E.W * 3, E.H * 2);
    FX.floorLines(g, GYv, GYv + 400, 'rgba(0,0,0,.18)');
  });
}

// presenter backdrop, after the reference photo: warm plaster wall on the left, dark centre panel, bookshelf, plant, cool window edge on the right
export function studio(g, t, cam, o = {}) {
  const M = mood(o.mood || 'interiorWarm'), G = GY(), CX = E.W / 2;
  wallAndFloor(g, cam, M, G);
  layer(g, cam, 0.4, (g) => {
    const lw = V(520, 260), top = G - V(1000, 1500);
    g.fillStyle = linGrad(g, 0, top, 0, G, ['#7a5236', '#4a2f1e', '#2a1a12']); g.fillRect(CX - V(1100, 700) - 200, top, lw + 200, G - top);         // warm plaster wall
    const r = rng(4); for (let i = 0; i < 40; i++) { g.fillStyle = alpha(r() > 0.5 ? '#ffd2a0' : '#000', 0.05 + r() * 0.05); g.beginPath(); g.ellipse(CX - V(1100, 700) + r() * lw, top + r() * (G - top), 40 + r() * 90, 30 + r() * 70, 0, 0, 7); g.fill(); }
    glow(g, CX - V(900, 560), G - V(520, 700), 420, '#ffb070', 0.22);
    const px = CX - V(560, 240), pw = V(420, 280), ph = V(520, 760), py = G - V(820, 1160);                                                              // dark panel + bookshelf
    g.fillStyle = '#0b0d12'; g.fillRect(px - 40, top, pw + V(1500, 900), G - top);
    for (let i = 0; i < 3; i++) { const y = py + 50 + i * (ph / 3.1); g.fillStyle = '#3a2618'; g.fillRect(px, y, pw, 7); const rr2 = rng(i + 7); let x = px + 8; while (x < px + pw - 30) { const w = 18 + rr2() * 28, h = 40 + rr2() * 56; g.fillStyle = shade('#3b2a22', -0.1 + rr2() * 0.35); g.fillRect(x, y - h, w, h); x += w + 3 + rr2() * 5; } }
    glow(g, px + pw / 2, py + ph * 0.55, 230, '#ffb878', 0.16);
  });
  layer(g, cam, 0.8, (g) => {                                                                                                                              // plant + window light, right
    const x0 = CX + V(560, 260); const r = rng(11);
    for (let i = 0; i < 22; i++) { const a = -Math.PI / 2 + (r() - 0.5) * 2.2, len = V(120, 200) + r() * V(200, 240); g.strokeStyle = alpha('#1d3326', 0.9); g.lineWidth = 16 + r() * 10; g.lineCap = 'round'; g.beginPath(); g.moveTo(x0, G - 40); g.quadraticCurveTo(x0 + Math.cos(a) * len * 0.5, G - 40 + Math.sin(a) * len * 0.5 - 40, x0 + Math.cos(a) * len, G - 40 + Math.sin(a) * len); g.stroke(); }
    g.fillStyle = linGrad(g, 0, 0, E.W, 0, ['rgba(120,150,190,0)', 'rgba(150,175,215,.32)']); g.fillRect(CX + V(760, 340), G - V(1100, 1500), V(300, 200), V(1100, 1500));
  });
  return { GY: G, M };
}

// bedroom at night: window with moon, bed, nightstand + lamp
export function bedroom(g, t, cam, o = {}) {
  const M = mood(o.mood || 'night'), G = GY(), CX = E.W / 2;
  wallAndFloor(g, cam, M, G);
  layer(g, cam, 0.4, (g) => {
    FX.windowFrame(g, { x: CX + V(280, 90), y: G - V(760, 1160), w: V(420, 340), h: V(420, 560), cols: 2, frame: shade(M.wall, -0.5), bar: 8, blinds: 0 }, (g, x, y, w, h) => {
      g.fillStyle = linGrad(g, 0, y, 0, y + h, M.sky); g.fillRect(x, y, w, h); FX.stars(g, { area: [x, y, w, h * 0.7], count: 22, seed: 5, t });
      circle(g, x + w * 0.72, y + h * 0.25, 22, '#f4f1e4'); glow(g, x + w * 0.72, y + h * 0.25, 120, '#cfd8ff', 0.3);
    });
  });
  layer(g, cam, 0.95, (g) => {
    const bx = CX - V(760, 520), bw = V(900, 760), top = G - 92;
    g.fillStyle = shade(M.wall, -0.5); g.fillRect(bx - 18, G - 250, 26, 250); g.fillRect(bx, top, bw, 92);
    rr(g, bx + 8, top - 40, bw - 8, 52, 14); g.fillStyle = '#4b4f78'; g.fill();           // mattress + blanket
    rr(g, bx + 18, top - 66, 150, 40, 18); g.fillStyle = '#d9d6e6'; g.fill();             // pillow
    const nx = bx + bw + 40; rr(g, nx, G - 130, 130, 130, 6); g.fillStyle = shade(M.wall, -0.4); g.fill();
    seg(g, [[nx + 65, G - 130], [nx + 65, G - 190]], 5, '#222'); g.fillStyle = M.practical; g.beginPath(); g.moveTo(nx + 36, G - 190); g.lineTo(nx + 94, G - 190); g.lineTo(nx + 80, G - 236); g.lineTo(nx + 50, G - 236); g.closePath(); g.fill();
    glow(g, nx + 65, G - 214, 220, M.practical, 0.38);
  });
  return { GY: G, M, bed: { top: G - 92 + 0, x: CX - V(760, 520), w: V(900, 760) } };
}

// desk room: wall clock, window blinds, desk with laptop + notebook (figure sits behind the desk line)
export function deskRoom(g, t, cam, o = {}) {
  const M = mood(o.mood || 'interiorWarm'), G = GY(), CX = E.W / 2;
  wallAndFloor(g, cam, M, G);
  layer(g, cam, 0.4, (g) => {
    FX.windowFrame(g, { x: CX - V(700, 420), y: G - V(800, 1180), w: V(460, 380), h: V(380, 520), cols: 2, frame: shade(M.wall, -0.5), bar: 8, blinds: 7 }, (g, x, y, w, h) => { g.fillStyle = linGrad(g, 0, y, 0, y + h, M.sky); g.fillRect(x, y, w, h); });
    const cx = CX + V(420, 220), cy = G - V(700, 1000);
    FX.clock(g, cx, cy, V(74, 66), o.clockT ?? (t * 120), { face: '#e9e4ea', speed: 1 });
  });
  const desk = () => layer(g, cam, 1, (g) => {
    const dw = V(1000, 900), dx = CX - dw / 2, top = G - 150;
    rr(g, dx, top, dw, 22, 6); g.fillStyle = shade(M.wall, 0.12); g.fill(); g.fillStyle = shade(M.wall, -0.4); g.fillRect(dx + 20, top + 22, dw - 40, 130);
    const lx = CX + 60, lw = 280, lh = 170; seg(g, [[lx + lw / 2, top], [lx + lw / 2, top - 30]], 8, '#15161c');
    rr(g, lx, top - lh - 30, lw, lh, 10); g.fillStyle = '#0d0f15'; g.fill(); rr(g, lx + 8, top - lh - 22, lw - 16, lh - 16, 6); g.fillStyle = '#e9eef8'; g.fill();
    for (let i = 0; i < 5; i++) { g.fillStyle = '#b9c2d6'; g.fillRect(lx + 26, top - lh + i * 24, lw - 52 - (i % 3) * 40, 6); }
    glow(g, lx + lw / 2, top - lh / 2, 260, '#cfe0ff', 0.12);
    rr(g, CX - 250, top - 12, 150, 12, 3); g.fillStyle = '#e7e0d2'; g.fill();           // notebook
  });
  return { GY: G, M, desk };
}
