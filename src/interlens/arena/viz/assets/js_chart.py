# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# [rational_agents: viz-ux] 2026-08-03

"""Browser layer, part 2: the two charts.

**The frontier chart** places every deal in the instance's deal space, draws the efficient envelope, the play
trajectory, and the reference marks, and lets a reader inspect any of the ``|D|`` deals — not only the marked
ones — by hovering: one handler on the SVG finds the nearest deal in plot coordinates rather than attaching
thousands of listeners. Hover opens the headline read; a click *pins* the full per-party breakdown.

It also zooms and pans, in plain SVG with no library: the view is the ``viewBox``, so zooming is arithmetic on
four numbers and every mark stays vector-crisp. Wheel-zoom is deliberately gated behind Ctrl/⌘ or Shift — an
ungated wheel over a chart hijacks page scrolling, which is the single most irritating thing a chart can do — and
the explicit +/−/reset buttons carry the same behaviour for anyone who would rather click. Because the pointer
maths reads the *current* viewBox, nearest-deal hover keeps working at every zoom level.

**The regret strip** is one series (per-turn regret against the selected oracle), so it carries no legend: the
title names it. Non-zero bars are direct-labelled and every bar jumps to its turn.

Both return a small handle so the page can drive them from elsewhere — above all ``focusTurn``, which is how
clicking a transcript turn lights up the deal it put on the table.
"""
from __future__ import annotations

JS_CHART = r"""
/* One marker of a given shape, centred on (x, y). `attrs` is the attribute string and `inner` the child markup
   (the <title> that gives every mark a native tooltip), so the element is built once with its content rather
   than being patched afterwards. */
function shapeAt(kind, x, y, r, cls, attrs, inner) {
  const open = (tag, geom) => `<${tag} class="${cls}" ${geom} ${attrs}>${inner}</${tag}>`;
  if (kind === "diamond")
    return open("rect", `x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" transform="rotate(45 ${x} ${y})"`);
  if (kind === "square")
    return open("rect", `x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" rx="2"`);
  if (kind === "star") {
    let p = "";
    for (let i = 0; i < 10; i++) {
      const rad = (i % 2 ? r * 0.46 : r * 1.15), a = -Math.PI / 2 + i * Math.PI / 5;
      p += `${(x + rad * Math.cos(a)).toFixed(2)},${(y + rad * Math.sin(a)).toFixed(2)} `;
    }
    return open("polygon", `points="${p.trim()}"`);
  }
  return open("circle", `cx="${x}" cy="${y}" r="${r}"`);
}

/* Draw the deal cloud, the efficient envelope, the reference marks, and one or two play trajectories.
   `marks` entries: {index, kind:'star'|'diamond'|'circle'|'square', color:'s1'|'s2'|'s3', label, title, turn}.
   Returns {focusTurn(idx), reset()} so the transcript can drive the chart. */
function frontierChart(host, game, marks, paths, onPick) {
  const W = 760, H = 470, m = { l: 54, r: 18, t: 14, b: 46 };
  const d = game.deals;
  const xmax = Math.max(0.001, Math.max(...d.wx)), ymax = Math.max(0.001, Math.max(...d.wy));
  const nice = (v) => Math.ceil(v * 20) / 20;
  const XM = nice(xmax * 1.04), YM = nice(ymax * 1.06);
  const px = (v) => m.l + (v / XM) * (W - m.l - m.r);
  const py = (v) => H - m.b - (v / YM) * (H - m.t - m.b);
  let s = [];
  for (let i = 0; i <= 5; i++) {
    const gx = XM * i / 5, gy = YM * i / 5;
    s.push(`<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${py(gy).toFixed(1)}" y2="${py(gy).toFixed(1)}"/>`);
    s.push(`<line class="gridline" y1="${m.t}" y2="${H - m.b}" x1="${px(gx).toFixed(1)}" x2="${px(gx).toFixed(1)}"/>`);
    s.push(`<text x="${m.l - 8}" y="${(py(gy) + 4).toFixed(1)}" text-anchor="end">${(gy * 100).toFixed(0)}%</text>`);
    s.push(`<text x="${px(gx).toFixed(1)}" y="${H - m.b + 16}" text-anchor="middle">${(gx * 100).toFixed(0)}%</text>`);
  }
  s.push(`<line class="axisline" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`);
  s.push(`<line class="axisline" x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${H - m.b}"/>`);
  s.push(`<text class="axistitle" x="${(m.l + W - m.r) / 2}" y="${H - 8}" text-anchor="middle">joint welfare — mean normalized surplus →</text>`);
  s.push(`<text class="axistitle" transform="rotate(-90 14 ${(m.t + H - m.b) / 2})" x="14" y="${(m.t + H - m.b) / 2}" text-anchor="middle">worst-off party — min normalized surplus →</text>`);
  // efficient envelope: shaded achievable region + its boundary
  if (game.envelope && game.envelope.length > 1) {
    const pts = game.envelope.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join(" ");
    const first = game.envelope[0], last = game.envelope[game.envelope.length - 1];
    s.push(`<polygon class="envfill" points="${px(first[0]).toFixed(1)},${py(0).toFixed(1)} ${pts} ${px(last[0]).toFixed(1)},${py(0).toFixed(1)}"/>`);
    s.push(`<polyline class="envline" points="${pts}"/>`);
  }
  // the deal cloud: dominated deals muted, frontier deals ringed
  for (let i = 0; i < d.n; i++) {
    if (d.pareto[i]) continue;
    s.push(`<circle class="dot" cx="${px(d.wx[i]).toFixed(1)}" cy="${py(d.wy[i]).toFixed(1)}" r="2"/>`);
  }
  for (let i = 0; i < d.n; i++) {
    if (!d.pareto[i]) continue;
    s.push(`<circle class="front" cx="${px(d.wx[i]).toFixed(1)}" cy="${py(d.wy[i]).toFixed(1)}" r="3.2"/>`);
  }
  // trajectories, drawn under the marks
  (paths || []).forEach(p => {
    if (p.indices.length < 2) return;
    s.push(`<polyline class="${p.cls}" points="${p.indices.map(i => `${px(d.wx[i]).toFixed(1)},${py(d.wy[i]).toFixed(1)}`).join(" ")}"/>`);
  });
  marks.forEach((mk, k) => {
    const x = px(d.wx[mk.index]), y = py(d.wy[mk.index]), r = mk.r || 6.5;
    const tip = E(mk.title || mk.label || "");
    /* `mk.cls` is a STATE of a mark (e.g. a proposal the reader has not scrolled to yet), never an identity:
       it changes weight, not hue, so the chart never spends a categorical slot on "later". */
    s.push(shapeAt(mk.kind, x, y, r, "mark" + (mk.cls ? " " + mk.cls : ""),
      `fill="var(--${mk.color})" data-mark="${k}"${mk.turn !== undefined ? ` data-markturn="${mk.turn}"` : ""}
       tabindex="0" role="button" aria-label="${tip}"`, `<title>${tip}</title>`));
    if (mk.label) s.push(`<text class="lab" x="${(x + (mk.dx ?? 9)).toFixed(1)}" y="${(y + (mk.dy ?? -8)).toFixed(1)}">${E(mk.label)}</text>`);
  });
  // the full-cloud hover anchor, drawn last so it sits on top; positioned + revealed on hover, never intercepts
  s.push('<circle class="sel hoverpt" r="5" fill="none" style="pointer-events:none;opacity:0"></circle>');
  host.innerHTML = `<div class="chartwrap"><div class="zoombar">
      <button class="iconbtn" data-zoom="in" title="Zoom in (or Ctrl/Shift + wheel over the chart)" aria-label="Zoom in">+</button>
      <button class="iconbtn" data-zoom="out" title="Zoom out" aria-label="Zoom out">&minus;</button>
      <button class="iconbtn" data-zoom="reset" title="Reset the view (or double-click the chart)">reset</button>
    </div><svg viewBox="0 0 ${W} ${H}" class="pannable" role="img"
    aria-label="Deal space in a scale-invariant two-dimensional embedding: joint welfare against the worst-off party's surplus. Hover anywhere to inspect the nearest deal and click to pin its per-party breakdown; the marked deals also take keyboard focus. Drag to pan, Ctrl or Shift with the wheel to zoom.">${s.join("")}</svg></div>`;
  const svg = host.querySelector("svg");
  const ring = svg.querySelector("circle.hoverpt");

  /* ---- zoom & pan: the view IS the viewBox, so both are arithmetic on four numbers ---- */
  let VB = { x: 0, y: 0, w: W, h: H };
  const applyVB = () => svg.setAttribute("viewBox", `${VB.x.toFixed(2)} ${VB.y.toFixed(2)} ${VB.w.toFixed(2)} ${VB.h.toFixed(2)}`);
  /* Zoom about a fixed point in chart coordinates so what is under the pointer stays under the pointer. Clamped
     to [1x, 20x] and kept from wandering off the drawn area, so a page can never end up staring at blank space. */
  function zoomAt(factor, cx, cy) {
    const nw = Math.max(W / 20, Math.min(W, VB.w * factor));
    const scale = nw / VB.w, nh = VB.h * scale;
    VB = { x: cx - (cx - VB.x) * scale, y: cy - (cy - VB.y) * scale, w: nw, h: nh };
    clamp(); applyVB();
  }
  function clamp() {
    VB.x = Math.max(-0.15 * W, Math.min(W - VB.w + 0.15 * W, VB.x));
    VB.y = Math.max(-0.15 * H, Math.min(H - VB.h + 0.15 * H, VB.y));
  }
  const reset = () => { VB = { x: 0, y: 0, w: W, h: H }; applyVB(); };
  /* Client pixels -> chart units, THROUGH the current viewBox, so hover stays exact at every zoom level. */
  const toChart = (evt) => {
    const box = svg.getBoundingClientRect();
    if (!box.width || !box.height) return null;
    return { x: VB.x + (evt.clientX - box.left) * (VB.w / box.width),
             y: VB.y + (evt.clientY - box.top) * (VB.h / box.height) };
  };
  host.querySelectorAll("[data-zoom]").forEach(b => b.addEventListener("click", () => {
    const k = b.dataset.zoom;
    if (k === "reset") return reset();
    zoomAt(k === "in" ? 0.7 : 1 / 0.7, VB.x + VB.w / 2, VB.y + VB.h / 2);
  }));
  svg.addEventListener("wheel", (evt) => {
    if (!(evt.ctrlKey || evt.metaKey || evt.shiftKey)) return;   // an ungated wheel must keep scrolling the page
    evt.preventDefault();
    const p = toChart(evt);
    if (p) zoomAt(evt.deltaY < 0 ? 0.85 : 1 / 0.85, p.x, p.y);
  }, { passive: false });
  svg.addEventListener("dblclick", reset);
  let drag = null;
  svg.addEventListener("pointerdown", (evt) => {
    if (evt.button !== 0 || evt.target.closest("[data-mark]")) return;
    drag = { x: evt.clientX, y: evt.clientY, vx: VB.x, vy: VB.y, moved: false };
  });
  svg.addEventListener("pointerup", () => { svg.classList.remove("panning"); drag = null; });
  svg.addEventListener("pointerleave", () => { svg.classList.remove("panning"); drag = null; });

  /* ---- full-cloud inspection: EVERY one of the |D| deals is hoverable, not only the marked ones ----
     Rather than attach a listener to each of thousands of dots, one handler on the svg finds the nearest deal to
     the pointer in plot coordinates and opens its headline read; a faint ring anchors it. A mark is the event
     target when the pointer is on it, so we defer to the mark's own (richer, titled) hover there. */
  let lastIdx = -1;
  const nearest = (evt) => {
    const p = toChart(evt);
    if (!p) return -1;
    const zoom = W / VB.w;
    let bi = -1, bd = 1e18;
    for (let i = 0; i < d.n; i++) {
      const ex = px(d.wx[i]) - p.x, ey = py(d.wy[i]) - p.y, q = ex * ex + ey * ey;
      if (q < bd) { bd = q; bi = i; }
    }
    const snap = 22 / zoom;                  // a constant SCREEN radius, so zooming in really does separate deals
    return bd <= snap * snap ? bi : -1;
  };
  const clearRing = () => { ring.style.opacity = "0"; lastIdx = -1; };
  svg.addEventListener("mousemove", (evt) => {
    if (drag) {
      const box = svg.getBoundingClientRect();
      drag.moved = true;
      svg.classList.add("panning");
      VB.x = drag.vx - (evt.clientX - drag.x) * (VB.w / box.width);
      VB.y = drag.vy - (evt.clientY - drag.y) * (VB.h / box.height);
      clamp(); applyVB();
      return;
    }
    if (evt.target.closest("[data-mark]")) { clearRing(); return; }   // a mark owns its own hover
    const i = nearest(evt);
    if (i < 0) { clearRing(); return; }
    ring.setAttribute("cx", px(d.wx[i]).toFixed(1)); ring.setAttribute("cy", py(d.wy[i]).toFixed(1));
    ring.style.opacity = "1";
    if (i !== lastIdx) { lastIdx = i; onPick({ index: i, role: "deal", title: "deal #" + i }); }
  });
  svg.addEventListener("mouseleave", clearRing);
  svg.addEventListener("click", (evt) => {
    if (drag && drag.moved) return;                     // a pan is not a click
    if (evt.target.closest("[data-mark]")) return;
    const i = nearest(evt);
    if (i >= 0) onPick({ index: i, role: "deal", title: "deal #" + i }, true);
  });
  host.querySelectorAll("[data-mark]").forEach(node => {
    const mk = marks[Number(node.dataset.mark)];
    const fire = () => onPick(mk);
    node.addEventListener("mouseenter", fire);
    node.addEventListener("focus", fire);
    node.addEventListener("click", () => onPick(mk, true));
  });

  /* Light up the mark a given TURN put on the table — the transcript-to-chart half of the sync. */
  function focusTurn(idx) {
    let found = null;
    svg.querySelectorAll("[data-markturn]").forEach(n => {
      const hit = Number(n.dataset.markturn) === Number(idx);
      n.classList.toggle("pinned", hit);
      if (hit) found = marks[Number(n.dataset.mark)];
    });
    return found;
  }
  return { focusTurn, reset, svg };
}

/* --------------------------------------------------------------- regret strip --- */
/* One series (per-turn regret against the selected oracle), so no legend: the title names it. Non-zero bars are
   direct-labelled; hover carries the chosen/best values the regret is a difference of. */
function regretChart(host, turns, oracle, onPick) {
  const rows = turns.map(t => ({ t, o: (t.oracles || {})[oracle] })).filter(r => r.o && typeof r.o.divergence === "number");
  if (!rows.length) { host.innerHTML = `<div class="gap">No <code>${E(oracle)}</code> verdicts on this episode's turns.</div>`; return null; }
  const W = 760, H = 168, m = { l: 46, r: 12, t: 12, b: 34 };
  const max = Math.max(1e-9, ...rows.map(r => r.o.divergence));
  const bw = Math.max(3, Math.min(26, (W - m.l - m.r) / rows.length - 3));
  const bx = (i) => m.l + (i + 0.5) * ((W - m.l - m.r) / rows.length);
  const by = (v) => H - m.b - (v / max) * (H - m.t - m.b);
  let s = [];
  for (let i = 0; i <= 4; i++) {
    const gy = max * i / 4;
    s.push(`<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${by(gy).toFixed(1)}" y2="${by(gy).toFixed(1)}"/>`);
    s.push(`<text x="${m.l - 7}" y="${(by(gy) + 4).toFixed(1)}" text-anchor="end">${N(gy, max < 5 ? 2 : 0)}</text>`);
  }
  s.push(`<line class="axisline" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`);
  rows.forEach((r, i) => {
    const h = Math.max(r.o.divergence > 0 ? 2 : 0, (H - m.b) - by(r.o.divergence));
    const x = bx(i) - bw / 2;
    s.push(`<rect class="mark" x="${x.toFixed(1)}" y="${(H - m.b - h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}"
      rx="${Math.min(4, bw / 2).toFixed(1)}" fill="var(--s2)" data-turn="${r.t.idx}" tabindex="0" role="button"
      aria-label="turn ${r.t.idx} ${E(r.t.seat)} regret ${N(r.o.divergence, 2)}"><title>turn ${r.t.idx} · ${E(r.t.seat)}
 · chose ${N(r.o.chosen_value, 2)} · oracle best ${N(r.o.best_value, 2)} · regret ${N(r.o.divergence, 2)}</title></rect>`);
    if (r.o.divergence > max * 0.06) s.push(`<text class="lab" x="${bx(i).toFixed(1)}" y="${(H - m.b - h - 5).toFixed(1)}" text-anchor="middle">${N(r.o.divergence, max < 5 ? 2 : 0)}</text>`);
    if (rows.length <= 30) s.push(`<text x="${bx(i).toFixed(1)}" y="${H - m.b + 15}" text-anchor="middle">${r.t.idx}</text>`);
  });
  s.push(`<text class="axistitle" x="${(m.l + W - m.r) / 2}" y="${H - 4}" text-anchor="middle">turn index</text>`);
  host.innerHTML = `<div class="chartwrap"><svg viewBox="0 0 ${W} ${H}" role="img"
    aria-label="Per-turn regret against the ${E(oracle)} oracle, in that oracle's value units.">${s.join("")}</svg></div>`;
  host.querySelectorAll("[data-turn]").forEach(n => n.addEventListener("click", () => onPick(Number(n.dataset.turn))));
  return { host };
}
"""
