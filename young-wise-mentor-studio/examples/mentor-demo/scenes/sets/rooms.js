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

// presenter backdrop: soft panel light, shelves, bokeh practicals, plant silhouette
export function studio(g, t, cam, o = {}) {
  const M = mood(o.mood || 'interiorCool'), G = GY(), CX = E.W / 2;
  wallAndFloor(g, cam, M, G);
  layer(g, cam, 0.4, (g) => {
    const px = CX - V(820, 380), pw = V(520, 340), ph = V(560, 900), py = G - V(860, 1200);
    g.fillStyle = radGrad(g, px + pw / 2, py + ph / 2, 10, ph * 0.9, [alpha(M.key, 0.22), alpha(M.key, 0.0)]); g.fillRect(px - 300, py - 300, pw + 600, ph + 600);
    rr(g, px, py, pw, ph, 10); g.fillStyle = alpha(shade(M.wall, 0.12), 0.95); g.fill();
    for (let i = 0; i < 3; i++) { const y = py + 60 + i * (ph / 3.2); g.fillStyle = shade(M.wall, -0.4); g.fillRect(px - 12, y, pw + 24, 8); const r = rng(i + 3); let x = px + 14; while (x < px + pw - 40) { const w = 22 + r() * 34, h = 60 + r() * 70; g.fillStyle = shade(M.wall, 0.06 + r() * 0.2); g.fillRect(x, y - h, w, h); x += w + 4 + r() * 6; } }
    const px2 = CX + V(420, 180), r2 = rng(9);
    for (let i = 0; i < 7; i++) glow(g, px2 + r2() * V(900, 600), G - V(300, 520) - r2() * V(520, 700), 28 + r2() * 46, M.practical, 0.35);
  });
  layer(g, cam, 0.9, (g) => { const lx = CX + V(780, 380); seg(g, [[lx, G], [lx, G - V(290, 420)]], 5, shade(M.dark, 0.1)); glow(g, lx, G - V(300, 430), 120, M.practical, 0.42); circle(g, lx, G - V(300, 430), 14, M.practical); });
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
