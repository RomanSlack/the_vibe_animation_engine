/*
 * belo "thinking" animation — shared draw module (browser + node).  [v2 motion]
 *
 * "belo" is a cloud of medial-axis discs in PEN-STROKE ORDER (see order_discs.py),
 * so each disc has an arc-length param s in [0,1] from the start of the stroke.
 * Every beat is a transform of those discs:
 *   writeon : discs drop in under gravity, sweeping left->right in stroke order
 *   hold    : full wordmark
 *   morph   : the stroke straightens like a snake pulled taut (s -> x on a line)
 *   split   : the line gathers into 3 clusters (with overshoot bounce)
 *   pulse   : the 3 dots bounce on a gravity arc, staggered, seamless loop
 */
(function (root) {
  'use strict';

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth01 = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };

  // easeOutBack: settles with a little overshoot -> "snap / pulled taut"
  function easeOutBack(t, s) {
    const c1 = (s == null ? 1.70158 : s), c3 = c1 + 1;
    const u = t - 1;
    return 1 + c3 * u * u * u + c1 * u * u;
  }
  // easeOutBounce: gravity landing with a couple of bounces
  function easeOutBounce(t) {
    const n1 = 7.5625, d1 = 2.75;
    if (t < 1 / d1) return n1 * t * t;
    if (t < 2 / d1) { t -= 1.5 / d1; return n1 * t * t + 0.75; }
    if (t < 2.5 / d1) { t -= 2.25 / d1; return n1 * t * t + 0.9375; }
    t -= 2.625 / d1; return n1 * t * t + 0.984375;
  }

  function defaults() {
    return {
      color: '#FFFFFF',
      bg: 'transparent',
      // durations (seconds)
      dur: { writeon: 1.55, hold1: 0.35, morph: 1.0, hold2: 0.25, split: 0.85, pulse: 1.1 },
      // write-on (gravity drop-in)
      revealWindow: 0.12,      // fraction of the stroke mid-drop at once (wave width)
      dropHeight: 44,          // how far above each disc falls in from (px)
      // collapsed line + dots
      lineR: 16,               // half-thickness of the taut line (px)
      lineSpan: 1.0,           // taut-line length as a fraction of word width
      dotR: 23,                // dot radius (px)
      dotGap: 84,              // spacing between the 3 dot centres (px)
      // bounce / snap strength
      morphBack: 1.6,          // taut-pull overshoot
      splitBack: 2.1,          // split gather overshoot
      // pulse
      bounceAmp: 30,           // dot bounce height (px)
      dotPulse: 0.14,          // radius squash/pulse (fraction)
      bounceStagger: 0.16,     // phase offset between dots (turns)
    };
  }

  function prepare(medial) {
    const discs = medial.discs.map(([x, y, r]) => ({ hx: x, hy: y, hr: r }));
    const n = discs.length;
    discs.forEach((d, i) => {
      d.s = n > 1 ? i / (n - 1) : 0.5;          // arc-length param (stroke order)
      d.bucket = d.s < 1 / 3 ? 0 : d.s < 2 / 3 ? 1 : 2;
    });
    return { discs, w: medial.w, h: medial.h, y_mid: medial.y_mid,
             x0: medial.x0, x1: medial.x1, cx: (medial.x0 + medial.x1) / 2 };
  }

  function timeline(P) {
    const d = P.dur;
    const writeonEnd = d.writeon;
    const hold1End = writeonEnd + d.hold1;
    const morphEnd = hold1End + d.morph;
    const hold2End = morphEnd + d.hold2;
    const splitEnd = hold2End + d.split;
    return { writeonEnd, hold1End, morphEnd, hold2End, splitEnd, introEnd: splitEnd, pulse: d.pulse };
  }

  function discState(M, P, tl, d, T) {
    let x = d.hx, y = d.hy, r = d.hr, a = 1;
    const lineX = M.cx + (d.s - 0.5) * (M.x1 - M.x0) * P.lineSpan;  // taut-line position (centred)
    const centers = [M.cx - P.dotGap, M.cx, M.cx + P.dotGap];
    const dotX = centers[d.bucket];

    if (T < tl.writeonEnd) {
      const p = clamp(T / P.dur.writeon, 0, 1);
      const w = P.revealWindow;
      const local = (p * (1 + w) - d.s) / w;                 // <0 not yet, >1 settled
      if (local <= 0) return { x, y, r: 0, a: 0 };
      const aa = clamp(local, 0, 1);
      a = clamp(local / 0.35, 0, 1);
      y = d.hy - P.dropHeight * (1 - easeOutBounce(aa));      // fall in with bounce
      r = d.hr * smooth01(clamp(local / 0.5, 0, 1));
    } else if (T < tl.hold1End) {
      /* full wordmark — home */
    } else if (T < tl.morphEnd) {
      const p = clamp((T - tl.hold1End) / P.dur.morph, 0, 1);
      const e = easeOutBack(p, P.morphBack);                  // taut snap (overshoot)
      x = lerp(d.hx, lineX, e);
      y = lerp(d.hy, M.y_mid, e);
      r = lerp(d.hr, P.lineR, p);
    } else if (T < tl.hold2End) {
      x = lineX; y = M.y_mid; r = P.lineR;
    } else if (T < tl.splitEnd) {
      const p = clamp((T - tl.hold2End) / P.dur.split, 0, 1);
      const e = easeOutBack(p, P.splitBack);
      x = lerp(lineX, dotX, e);
      y = M.y_mid;
      r = lerp(P.lineR, P.dotR, p);
    } else {
      const u = (((T - tl.splitEnd) / P.dur.pulse) % 1 + 1) % 1;
      const ph = ((u + d.bucket * P.bounceStagger) % 1 + 1) % 1;
      const hop = 4 * ph * (1 - ph);                          // gravity arc 0..1..0
      x = dotX;
      y = M.y_mid - P.bounceAmp * hop;
      r = P.dotR * (1 + P.dotPulse * (hop - 0.3));
    }
    return { x, y, r, a };
  }

  function discsAt(M, P, T) {
    const tl = timeline(P);
    return M.discs.map((d) => discState(M, P, tl, d, T));
  }

  function draw(ctx, M, P, T, opts) {
    const { W, H, scale = 1, ox = 0, oy = 0 } = opts;
    ctx.clearRect(0, 0, W, H);
    if (P.bg && P.bg !== 'transparent') { ctx.fillStyle = P.bg; ctx.fillRect(0, 0, W, H); }
    ctx.fillStyle = P.color;
    ctx.save();
    ctx.translate(ox, oy);
    ctx.scale(scale, scale);
    const tl = timeline(P);
    for (const d of M.discs) {
      const s = discState(M, P, tl, d, T);
      if (s.a <= 0.01 || s.r <= 0.2) continue;
      ctx.globalAlpha = s.a;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, 6.283185307);
      ctx.fill();
    }
    ctx.restore();
    ctx.globalAlpha = 1;
  }

  const API = { defaults, prepare, timeline, discsAt, draw, clamp, lerp };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  root.BeloAnim = API;
})(typeof globalThis !== 'undefined' ? globalThis : this);
