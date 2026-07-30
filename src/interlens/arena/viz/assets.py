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
# [rational_agents: viz] 2026-07-29

"""The page's inline stylesheet and interactive layer — no external assets of any kind.

Every generated page is opened straight off a filesystem path (``file://``), often on a cluster login node behind
no web server, so a single request to a CDN would leave the chart blank. The CSS and JS therefore live here as
strings that get inlined into the HTML.

**Colour.** Both modes are explicitly selected, not derived by flipping the light values, and the categorical
slots are capped at THREE. That cap is the binding constraint of the colour formula for a scatter: with all pairs
of series simultaneously on screen (which is what a scatter does, unlike a bar chart's adjacent pairs), only the
first three slots clear the colour-blindness and normal-vision separation floors in both modes. The three slots
carry the only three identities that must be told apart by colour:

============  =========================  ==========================
slot          episode page               comparison page
============  =========================  ==========================
1 (blue)      what the model actually did the left episode
2 (orange)    what the oracle recommends  the right episode
3 (aqua)      normative solution points   normative solution points
============  =========================  ==========================

Everything else is encoded by **shape plus a direct label**: the five solution concepts share slot 3 and are each
labelled on the chart (``NBS``, ``KS``, ``UTIL``, ``EGAL``, ``MNW``), and the per-party ideal points share one
diamond with the party named on hover and enumerated in the side panel's table. Deals themselves are chart chrome,
not a series: dominated deals are muted dots, frontier deals carry the secondary-ink ring. Slot 3 sits below 3:1
against the light surface, which obligates the relief rule — hence the always-visible direct labels and the
numeric table view that every chart ships with.
"""
from __future__ import annotations

# --------------------------------------------------------------------------------------------- CSS --
# Roles first (light), then the same roles re-stated for dark under BOTH the OS media query and the explicit
# data-theme scope, so the viewer's toggle wins in either direction.
CSS = """
:root{
 color-scheme:light;
 --surface-1:#fcfcfb; --plane:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
 --grid:#e1e0d9; --axis:#c3c2b7; --ring:rgba(11,11,11,.10);
 --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;
 --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --critical:#d03b3b; --up:#006300;
}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){
 color-scheme:dark;
 --surface-1:#1a1a19; --plane:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
 --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,.10);
 --s1:#3987e5; --s2:#d95926; --s3:#199e70; --up:#0ca30c;
}}
:root[data-theme="dark"]{
 color-scheme:dark;
 --surface-1:#1a1a19; --plane:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
 --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,.10);
 --s1:#3987e5; --s2:#d95926; --s3:#199e70; --up:#0ca30c;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}
main{max-width:1560px;margin:0 auto;padding:20px}
h1{font-size:1.3rem;margin:0 0 4px} h2{font-size:1rem;margin:0 0 10px;letter-spacing:.01em}
h3{font-size:.9rem;margin:14px 0 6px;color:var(--ink-2)}
a{color:var(--s1)} code,kbd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em}
.card{background:var(--surface-1);border:1px solid var(--ring);border-radius:10px;padding:14px;margin-bottom:14px}
.sub{color:var(--ink-2);font-size:.87rem}
.muted{color:var(--muted)}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.pill{border:1px solid var(--ring);border-radius:999px;padding:2px 9px;font-size:.78rem;color:var(--ink-2);
 background:var(--plane);white-space:nowrap}
.pill b{color:var(--ink);font-weight:600}
.badge{border-radius:4px;padding:1px 6px;font-size:.72rem;font-weight:600;border:1px solid var(--ring)}
.badge.llm{color:var(--s1)} .badge.policy{color:var(--s3)} .badge.advocate{color:var(--s2)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:14px}
.tile{background:var(--surface-1);border:1px solid var(--ring);border-radius:10px;padding:10px 12px}
.tile .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.tile .v{font-size:1.45rem;font-weight:600;margin-top:2px}
.tile .n{font-size:.75rem;color:var(--ink-2)}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:14px;align-items:start}
aside{position:sticky;top:14px;max-height:calc(100vh - 28px);overflow-y:auto}
table{border-collapse:collapse;width:100%;font-size:.84rem;font-variant-numeric:tabular-nums}
th,td{text-align:right;padding:4px 7px;border-bottom:1px solid var(--grid)}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.03em}
tr.hi td{background:color-mix(in oklab,var(--s1) 12%,transparent)}
.neg{color:var(--critical)} .pos{color:var(--up)} .zero{color:var(--muted)}
details{margin:6px 0;border:1px solid var(--ring);border-radius:8px;background:var(--plane)}
details>summary{cursor:pointer;padding:6px 10px;font-size:.83rem;color:var(--ink-2);list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"\\25B8  ";color:var(--muted)}
details[open]>summary::before{content:"\\25BE  "}
details>summary:focus-visible{outline:2px solid var(--s1);outline-offset:1px}
details .body{padding:2px 10px 10px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:6px 0;background:var(--surface-1);
 border:1px solid var(--grid);border-radius:6px;padding:8px;font-size:.8rem;max-height:460px;overflow:auto}
.msgrole{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-top:8px}
button,select{font:inherit;font-size:.83rem;color:var(--ink);background:var(--surface-1);
 border:1px solid var(--ring);border-radius:7px;padding:5px 10px;cursor:pointer}
button[aria-pressed="true"]{border-color:var(--s1);color:var(--s1)}
button:focus-visible,select:focus-visible{outline:2px solid var(--s1);outline-offset:1px}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 2px;font-size:.79rem;color:var(--ink-2)}
.legend span{display:flex;align-items:center;gap:5px}
.swatch{width:10px;height:10px;border-radius:50%;border:2px solid var(--surface-1);flex:none}
.swatch.sq{border-radius:2px} .swatch.di{border-radius:2px;transform:rotate(45deg)}
.chartwrap{overflow-x:auto}
svg{display:block;max-width:100%;height:auto;touch-action:pan-y}
svg text{fill:var(--ink-2);font-size:11px;font-family:system-ui,sans-serif}
svg .gridline{stroke:var(--grid);stroke-width:1}
svg .axisline{stroke:var(--axis);stroke-width:1}
svg .lab{fill:var(--ink);font-size:10px;font-weight:600;paint-order:stroke;
 stroke:var(--surface-1);stroke-width:3px;stroke-linejoin:round}
svg .dot{fill:var(--muted);opacity:.35}
svg .front{fill:none;stroke:var(--ink-2);stroke-width:1.5;opacity:.75}
svg .envfill{fill:var(--ink-2);opacity:.07} svg .envline{fill:none;stroke:var(--ink-2);stroke-width:2;opacity:.35}
svg .mark{stroke:var(--surface-1);stroke-width:2;cursor:pointer}
svg .path1{fill:none;stroke:var(--s1);stroke-width:2;opacity:.85}
svg .path2{fill:none;stroke:var(--s2);stroke-width:2;opacity:.85}
svg .hitrow:hover{fill:var(--ink);opacity:.05}
svg .sel{stroke:var(--ink);stroke-width:2.5}
.detail{margin-top:10px;border-top:1px solid var(--grid);padding-top:10px;min-height:76px}
.detail .hd{font-weight:600;margin-bottom:4px}
.meter{position:relative;height:9px;background:var(--grid);border-radius:5px;overflow:hidden}
.meter i{position:absolute;inset:0 auto 0 0;border-radius:5px;display:block}
.meter i.ok{background:var(--s3)} .meter i.bad{background:var(--critical)}
.meter u{position:absolute;top:-2px;bottom:-2px;width:2px;background:var(--ink)}
.turn{border:1px solid var(--ring);border-radius:10px;background:var(--surface-1);padding:11px 13px;margin-bottom:11px}
.turn.divergent{border-color:var(--s2);border-left-width:4px}
.turn.sel{border-color:var(--s1);border-left-width:4px}
.turnhd{display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap}
.turnhd .who{font-weight:600}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:9px}
.col{border:1px solid var(--grid);border-radius:8px;padding:8px 10px;background:var(--plane)}
.col .hd{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:3px}
.col.acted{border-top:2px solid var(--s1)} .col.oracle{border-top:2px solid var(--s2)}
.act{font-weight:600;font-size:.9rem}
.deal{font-size:.8rem;color:var(--ink-2);margin-top:3px}
.msg{border-left:3px solid var(--grid);padding-left:9px;margin:7px 0;font-size:.88rem}
.gap{border:1px dashed var(--axis);border-radius:8px;padding:8px 10px;font-size:.82rem;color:var(--ink-2);
 background:var(--plane)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start}
.two>div{min-width:0}
.colhd{font-weight:600;padding:6px 10px;border-radius:8px;background:var(--plane);border:1px solid var(--ring);
 margin-bottom:10px;position:sticky;top:0;z-index:2}
.colhd.a{border-top:3px solid var(--s1)} .colhd.b{border-top:3px solid var(--s2)}
.divmark{border-top:2px dashed var(--s2);color:var(--s2);font-size:.78rem;font-weight:600;
 text-align:center;margin:14px 0;padding-top:5px}
.warn{border-left:4px solid var(--warn);padding:8px 12px;background:var(--surface-1);border-radius:8px;
 font-size:.85rem;margin-bottom:12px}
.warn b{color:var(--ink)}
@media (max-width:1180px){.layout{grid-template-columns:1fr}aside{position:static;max-height:none}}
@media (max-width:760px){.cols,.two{grid-template-columns:1fr}}
@media print{aside,button,select{display:none}.card{break-inside:avoid}}
"""

# --------------------------------------------------------------------------------------------- JS --
# One script serves both page kinds. It reads the payload from a JSON <script> tag, so no data is interpolated
# into executable positions.
JS = r"""
const PAYLOAD = JSON.parse(document.getElementById("viz-payload").textContent);
const E = (s) => String(s ?? "").replace(/[&<>"']/g, c => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const N = (v, d = 2) => (typeof v === "number" && isFinite(v)) ? v.toFixed(d) : "—";
const SIGN = (v, d = 2) => (typeof v === "number" && isFinite(v)) ? (v >= 0 ? "+" : "") + v.toFixed(d) : "—";
const CLS = (v, better = 1) => (typeof v !== "number" || v === 0) ? "zero" : ((v > 0) === (better >= 0) ? "pos" : "neg");
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };

/* ---------------------------------------------------------------- game helpers --- */
function dealNamed(game, index) {
  if (!game || index === null || index === undefined) return null;
  const out = {}; let rest = index;
  const strides = game.strides;
  game.issues.forEach((iss, j) => { out[iss.name] = iss.options[Math.floor(rest / strides[j]) % iss.options.length]; });
  return out;
}
function dealSummary(game, index) {
  const named = dealNamed(game, index);
  return named ? Object.entries(named).map(([k, v]) => k + "=" + v).join(", ") : "—";
}
function seatName(game, party) { return (PAYLOAD.seatNames || game.parties)[party] || game.parties[party]; }

/* Per-party breakdown of one deal: utility, threshold, surplus, and share of that party's ideal. This is the
   "how does EACH party feel about this proposal" panel the frontier chart opens on hover. */
function dealDetail(game, index, title, extra) {
  if (index === null || index === undefined) return `<div class="sub">Hover or click a deal on the chart.</div>`;
  const d = game.deals, s = d.s[index], u = d.u[index], xn = d.xn[index];
  const usw = s.reduce((a, b) => a + b, 0), esw = Math.min(...s);
  const below = s.filter(v => v < 0).length;
  const rows = game.parties.map((p, i) => {
    const ok = s[i] >= 0, w = Math.max(0, Math.min(1, xn[i]));
    return `<tr><td>${E(seatName(game, i))} <span class="muted">${E(p)}</span></td>
      <td>${N(u[i], 1)}</td><td class="muted">${N(game.thresholds[i], 1)}</td>
      <td class="${ok ? "pos" : "neg"}">${SIGN(s[i], 1)}</td>
      <td style="width:82px"><span class="meter"><i class="${ok ? "ok" : "bad"}" style="width:${(w * 100).toFixed(1)}%"></i></span></td>
      <td>${N(xn[i] * 100, 0)}%</td></tr>`;
  }).join("");
  return `<div class="hd">${E(title)} <span class="muted">deal #${index}</span></div>
   <div class="sub">${E(dealSummary(game, index))}</div>
   <div class="pills">
     <span class="pill">joint welfare <b>${N(usw, 1)}</b></span>
     <span class="pill">worst-off <b class="${esw >= 0 ? "pos" : "neg"}">${SIGN(esw, 1)}</b></span>
     <span class="pill">${d.pareto[index] ? "on the Pareto frontier" : "below the frontier by <b>" + N(d.d_frontier[index], 3) + "</b>"}</span>
     <span class="pill">${d.feasible[index] ? "can close under the protocol" : "<b>cannot close</b> (agreement rule)"}</span>
     ${below ? `<span class="pill"><b class="neg">${below}</b> part${below === 1 ? "y" : "ies"} below threshold</span>` : ""}
     ${extra ? `<span class="pill">${extra}</span>` : ""}
   </div>
   <table><thead><tr><th>party</th><th>utility</th><th>threshold</th><th>surplus</th><th>vs ideal</th><th></th></tr></thead>
   <tbody>${rows}</tbody></table>`;
}

/* ---------------------------------------------------------------- frontier chart --- */
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
   `marks` entries: {index, kind:'star'|'diamond'|'circle'|'square', color:'s1'|'s2'|'s3', label, title, series}. */
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
  s.push(`<text x="${(m.l + W - m.r) / 2}" y="${H - 8}" text-anchor="middle">joint welfare — mean normalized surplus →</text>`);
  s.push(`<text transform="rotate(-90 14 ${(m.t + H - m.b) / 2})" x="14" y="${(m.t + H - m.b) / 2}" text-anchor="middle">worst-off party — min normalized surplus →</text>`);
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
    s.push(shapeAt(mk.kind, x, y, r, "mark",
      `fill="var(--${mk.color})" data-mark="${k}" tabindex="0" role="button" aria-label="${tip}"`,
      `<title>${tip}</title>`));
    if (mk.label) s.push(`<text class="lab" x="${(x + (mk.dx ?? 9)).toFixed(1)}" y="${(y + (mk.dy ?? -8)).toFixed(1)}">${E(mk.label)}</text>`);
  });
  // the full-cloud hover anchor, drawn last so it sits on top; positioned + revealed on hover, never intercepts
  s.push('<circle class="sel hoverpt" r="5" fill="none" style="pointer-events:none;opacity:0"></circle>');
  host.innerHTML = `<div class="chartwrap"><svg viewBox="0 0 ${W} ${H}" role="img"
    aria-label="Deal space in a scale-invariant two-dimensional embedding: joint welfare against the worst-off party's surplus. Hover anywhere to inspect the nearest deal; the marked deals also take keyboard focus.">${s.join("")}</svg></div>`;
  host.querySelectorAll("[data-mark]").forEach(node => {
    const mk = marks[Number(node.dataset.mark)];
    const fire = () => onPick(mk);
    node.addEventListener("mouseenter", fire);
    node.addEventListener("focus", fire);
    node.addEventListener("click", () => onPick(mk, true));
  });
  /* Full-cloud inspection: EVERY one of the |D| deals is hoverable, not only the marked ones. Rather than attach
     a listener to each of thousands of dots, one handler on the svg finds the nearest deal to the pointer in plot
     coordinates and opens its per-party breakdown; a faint ring anchors it. A mark is the event target when the
     pointer is on it, so we defer to the mark's own (richer, titled) hover and skip the generic pick there. */
  const svg = host.querySelector("svg");
  const ring = svg.querySelector("circle.hoverpt");
  let lastIdx = -1;
  const nearest = (evt) => {
    const box = svg.getBoundingClientRect();
    if (!box.width || !box.height) return -1;
    const vx = (evt.clientX - box.left) * (W / box.width), vy = (evt.clientY - box.top) * (H / box.height);
    let bi = -1, bd = 1e18;
    for (let i = 0; i < d.n; i++) {
      const ex = px(d.wx[i]) - vx, ey = py(d.wy[i]) - vy, q = ex * ex + ey * ey;
      if (q < bd) { bd = q; bi = i; }
    }
    return bd <= 22 * 22 ? bi : -1;   // only snap within a comfortable radius, so empty regions clear the hover
  };
  const clearRing = () => { ring.style.opacity = "0"; lastIdx = -1; };
  svg.addEventListener("mousemove", (evt) => {
    if (evt.target.closest("[data-mark]")) { clearRing(); return; }   // a mark owns its own hover
    const i = nearest(evt);
    if (i < 0) { clearRing(); return; }
    ring.setAttribute("cx", px(d.wx[i]).toFixed(1)); ring.setAttribute("cy", py(d.wy[i]).toFixed(1));
    ring.style.opacity = "1";
    if (i !== lastIdx) { lastIdx = i; onPick({ index: i, role: "deal", title: "deal #" + i }); }
  });
  svg.addEventListener("mouseleave", clearRing);
  svg.addEventListener("click", (evt) => {
    if (evt.target.closest("[data-mark]")) return;
    const i = nearest(evt);
    if (i >= 0) onPick({ index: i, role: "deal", title: "deal #" + i }, true);
  });
}

/* --------------------------------------------------------------- regret strip --- */
/* One series (per-turn regret against the selected oracle), so no legend: the title names it. Non-zero bars are
   direct-labelled; hover carries the chosen/best values the regret is a difference of. */
function regretChart(host, turns, oracle, onPick) {
  const rows = turns.map(t => ({ t, o: (t.oracles || {})[oracle] })).filter(r => r.o && typeof r.o.divergence === "number");
  if (!rows.length) { host.innerHTML = `<div class="gap">No <code>${E(oracle)}</code> verdicts on this episode's turns.</div>`; return; }
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
  s.push(`<text x="${(m.l + W - m.r) / 2}" y="${H - 4}" text-anchor="middle">turn index</text>`);
  host.innerHTML = `<div class="chartwrap"><svg viewBox="0 0 ${W} ${H}" role="img"
    aria-label="Per-turn regret against the ${E(oracle)} oracle, in that oracle's value units.">${s.join("")}</svg></div>`;
  host.querySelectorAll("[data-turn]").forEach(n => n.addEventListener("click", () => onPick(Number(n.dataset.turn))));
}

/* A one-line provenance note naming the annotation vintage the post-hoc oracle values were read from
   (`annotations` = the original scoring pass, `annotations_v1` = a re-annotated set such as the oracle
   seat-binding fix), so an auditor always sees WHICH counterfactual they are reading. Empty when no counterfactual
   oracle is present or the values came from the episode's own inline records rather than an annotation store. */
function annProvenance(source, oracles) {
  if (!source || !(oracles && oracles.length)) return "";
  return `<div class="sub muted annprov">Rational-agent counterfactual (${oracles.map(E).join(", ")}) read from the <code>${E(source)}</code> annotation set.</div>`;
}

/* ------------------------------------------------------------------- transcript --- */
function viewPanel(t) {
  const label = { stored: "exactly as recorded at generation time",
                  reconstructed: "RE-DERIVED by replay through the current prompt code — not a byte record of what the model saw",
                  reconstructed_pre_retry: "RE-DERIVED, and INCOMPLETE: this turn was a retry after a malformed response, and the repair instruction the model actually saw is not recoverable from the record — what follows is the FIRST attempt's prompt",
                  absent: "not recorded" }[t.view_source] || t.view_source;
  if (!t.view) return `<details><summary>Prompt the seat saw — ${E(label)}</summary><div class="body">
    <div class="gap">This episode predates per-turn view capture and could not be reconstructed, so the exact prompt is unavailable. The game setup, protocol, and this seat's private sheet are in the side panel; do not treat them as the literal prompt text.</div></div></details>`;
  const msgs = t.view.map(msg => `<div class="msgrole">${E(msg.role)}</div><pre>${E(msg.content)}</pre>`).join("");
  return `<details><summary>Prompt the seat saw — ${t.view.length} message(s), ${E(t.view_source)}</summary>
    <div class="body"><div class="sub">${E(label)}</div>${msgs}</div></details>`;
}

function oracleColumn(t, game, oracle) {
  const o = (t.oracles || {})[oracle];
  if (!o) return `<div class="col oracle"><div class="hd">rational agent (${E(oracle)})</div>
    <div class="gap">This run carries no <code>${E(oracle)}</code> verdict for this turn, so there is no counterfactual to compare against.</div></div>`;
  const reg = o.divergence;
  return `<div class="col oracle"><div class="hd">rational agent would (${E(oracle)})</div>
    <div class="act">${E(o.best_label)}</div>
    ${o.best_deal_index !== null && o.best_deal_index !== undefined
      ? `<div class="deal"><a href="#" data-deal="${o.best_deal_index}">${E(dealSummary(game, o.best_deal_index))}</a></div>` : ""}
    <table><tbody>
      <tr><td>oracle value of the model's move</td><td>${N(o.chosen_value)}</td></tr>
      <tr><td>oracle value of its own best</td><td>${N(o.best_value)}</td></tr>
      <tr class="${typeof reg === "number" && reg > 0 ? "hi" : ""}"><td><b>regret</b></td>
        <td class="${CLS(reg === 0 ? 0 : -reg)}"><b>${SIGN(reg === null || reg === undefined ? null : -reg)}</b></td></tr>
    </tbody></table>
    ${o.flags && o.flags.length ? `<div class="pills">${o.flags.map(f => `<span class="pill"><b class="neg">${E(f)}</b></span>`).join("")}</div>` : ""}</div>`;
}

function turnCard(t, game, oracle, opts) {
  const a = t.action || {};
  const dealLink = a.deal_index !== null && a.deal_index !== undefined
    ? `<div class="deal"><a href="#" data-deal="${a.deal_index}">${E(dealSummary(game, a.deal_index))}</a></div>`
    : (a.deal_named ? `<div class="deal neg">proposal did not resolve to a legal deal: ${E(JSON.stringify(a.deal_named))}</div>` : "");
  const w = t.deal_welfare;
  const oracles = Object.keys(t.oracles || {});
  return `<article class="turn" id="turn-${t.idx}" data-turnidx="${t.idx}">
   <div class="turnhd">
     <span class="who">[${t.idx}] ${E(t.seat)} <span class="badge ${E(t.kind)}">${E(t.kind)}</span></span>
     <span class="sub">${E(t.phase)} · round ${t.round}${t.n_tokens_out ? " · " + t.n_tokens_out + " tok out" : ""}${t.parse_ok ? "" : " · <b class='neg'>parse error</b>"}</span>
   </div>
   ${opts.showCounterfactual ? `<div class="cols">
     <div class="col acted"><div class="hd">the model acted</div><div class="act">${E(a.label || a.atype)}</div>${dealLink}
       ${w ? `<div class="pills"><span class="pill">USW <b>${N(w.usw, 1)}</b></span><span class="pill">worst-off <b class="${w.esw >= 0 ? "pos" : "neg"}">${SIGN(w.esw, 1)}</b></span>${w.n_below_threshold ? `<span class="pill"><b class="neg">${w.n_below_threshold}</b> below τ</span>` : ""}</div>` : ""}</div>
     ${oracleColumn(t, game, oracle)}</div>`
    : `<div class="act">${E(a.label || a.atype)}</div>${dealLink}`}
   ${a.message ? `<div class="msg">${E(a.message)}</div>` : ""}
   ${a.syntax_error ? `<div class="gap neg">syntax error: ${E(a.syntax_error)}</div>` : ""}
   ${t.reasoning ? `<details><summary>Reasoning / scratchpad — provenance ${E(t.reasoning_provenance)}</summary>
      <div class="body"><pre>${E(t.reasoning)}</pre></div></details>`
     : `<div class="sub muted">No reasoning recorded (provenance ${E(t.reasoning_provenance)}). Do not impute it.</div>`}
   ${viewPanel(t)}
   ${t.content ? `<details><summary>Raw turn text as the table saw it</summary><div class="body"><pre>${E(t.content)}</pre></div></details>` : ""}
   ${oracles.length ? `<details><summary>All oracle verdicts (${oracles.length}) and every action they scored</summary><div class="body">
      ${oracles.map(name => {
        const o = t.oracles[name];
        return `<h3>${E(name)}</h3><table><thead><tr><th>action the oracle scored</th><th>value</th></tr></thead><tbody>
         ${o.action_values.map(av => `<tr><td>${E(av.label)}${av.deal ? ` <span class="muted">${E(JSON.stringify(av.deal))}</span>` : ""}</td><td>${N(av.value)}</td></tr>`).join("")}
         </tbody></table>
         <div class="pills"><span class="pill">chose <b>${N(o.chosen_value)}</b></span><span class="pill">best <b>${N(o.best_value)}</b></span>
         <span class="pill">regret <b>${N(o.divergence)}</b></span>${Object.entries(o.extra || {}).map(([k, v]) =>
           `<span class="pill">${E(k)} <b>${E(typeof v === "number" ? N(v, 3) : JSON.stringify(v))}</b></span>`).join("")}</div>`;
      }).join("")}</div></details>` : ""}
  </article>`;
}
"""

# The episode page's own wiring: build the marks, render the panels, and cross-link chart <-> transcript.
JS_EPISODE = r"""
const P = PAYLOAD, G = P.game;
PAYLOAD.seatNames = (P.seats || []).map(s => s.name);
let ORACLE = (P.counterfactual_oracles[0] || P.oracle_names[0] || "");
let SELECTED = null;

function buildMarks() {
  if (!G) return [];
  const marks = [];
  Object.entries(G.solutions).forEach(([name, pt]) => marks.push({
    index: pt.index, kind: "star", color: "s3", label: pt.label, r: 7,
    title: `${pt.label} — ${name}${pt.scale_invariant ? " (scale-invariant)" : " (NOT scale-invariant across private scales)"}`,
    role: "solution", concept: name }));
  G.party_best.forEach(pb => marks.push({
    index: pb.index, kind: "diamond", color: "s3", r: 5,
    title: `best efficient deal for ${seatName(G, pb.party)} (${pb.agent}) — surplus ${pb.surplus}`,
    role: "party_best", party: pb.party }));
  P.turns.forEach(t => {
    const o = (t.oracles || {})[ORACLE];
    if (o && o.best_deal_index !== null && o.best_deal_index !== undefined)
      marks.push({ index: o.best_deal_index, kind: "circle", color: "s2", r: 4.5, role: "oracle",
        title: `${ORACLE} oracle's deal at turn ${t.idx} (${t.seat})`, turn: t.idx });
  });
  P.trajectory.forEach(p => marks.push({
    index: p.index, kind: "circle", color: "s1", r: 6.5, label: String(p.ordinal), dx: 8, dy: -7,
    title: `move ${p.ordinal}: ${p.seat} ${p.atype} at turn ${p.turn_idx}`, role: "proposal", turn: p.turn_idx }));
  if (P.outcome.deal_index !== null && P.outcome.deal_index !== undefined)
    marks.push({ index: P.outcome.deal_index, kind: "square", color: "s1", r: 8, label: "AGREED", dx: 10, dy: 4,
      title: "the deal that closed", role: "agreed" });
  return marks;
}

function pick(mk, clicked) {
  SELECTED = mk;
  const extra = mk.role === "solution" ? `solution concept <b>${E(mk.label)}</b>`
    : mk.role === "oracle" ? `<b>${E(ORACLE)}</b> oracle's recommendation`
    : mk.role === "proposal" ? `move <b>${mk.label}</b> on the table`
    : mk.role === "agreed" ? "<b>the deal that closed</b>" : "";
  document.getElementById("detail").innerHTML = dealDetail(G, mk.index, mk.title || "deal", extra);
  document.querySelectorAll(".turn").forEach(n => n.classList.remove("sel"));
  if (clicked && mk.turn !== undefined) {
    const node = document.getElementById("turn-" + mk.turn);
    if (node) { node.classList.add("sel"); node.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }
}

function drawChart() {
  if (!G) return;
  const marks = buildMarks();
  frontierChart(document.getElementById("chart"), G, marks,
    [{ cls: "path1", indices: P.trajectory.map(p => p.index) }], pick);
}

function drawTurns() {
  const showCf = Boolean(ORACLE);
  document.getElementById("turns").innerHTML =
    annProvenance(P.annotations_source, P.counterfactual_oracles) +
    P.turns.map(t => turnCard(t, G, ORACLE, { showCounterfactual: showCf })).join("");
  document.querySelectorAll("[data-deal]").forEach(a => a.addEventListener("click", ev => {
    ev.preventDefault();
    pick({ index: Number(a.dataset.deal), title: "deal referenced from the transcript" });
    document.getElementById("frontier").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}

function drawRegret() {
  if (!P.oracle_names.length) return;
  regretChart(document.getElementById("regret"), P.turns, ORACLE, idx => {
    const node = document.getElementById("turn-" + idx);
    if (node) { document.querySelectorAll(".turn").forEach(n => n.classList.remove("sel")); node.classList.add("sel"); node.scrollIntoView({ behavior: "smooth", block: "center" }); }
  });
}

const sel = document.getElementById("oracle-select");
if (sel) sel.addEventListener("change", ev => { ORACLE = ev.target.value; drawChart(); drawRegret(); drawTurns(); });
const tbl = document.getElementById("table-toggle");
if (tbl) tbl.addEventListener("click", () => {
  const on = tbl.getAttribute("aria-pressed") !== "true";
  tbl.setAttribute("aria-pressed", String(on));
  document.getElementById("chart-table").hidden = !on;
});
drawChart(); drawRegret(); drawTurns();
/* Open on the deal that closed; with no deal, open on the Nash bargaining solution as the normative anchor. */
if (G) {
  const nbs = G.solutions.nash || Object.values(G.solutions)[0];
  pick(P.outcome.deal_index !== null && P.outcome.deal_index !== undefined
    ? { index: P.outcome.deal_index, role: "agreed", title: "the deal that closed" }
    : { index: nbs.index, role: "solution", label: nbs.label, title: "Nash bargaining solution — no deal closed" });
}
"""

# The comparison page's wiring: one shared frontier carrying both trajectories, plus the synchronized columns.
JS_COMPARE = r"""
const C = PAYLOAD, L = C.left, R = C.right, G = L.game || R.game;
PAYLOAD.seatNames = (L.seats || []).map(s => s.name);

function pickC(mk) {
  const extra = mk.role === "solution" ? `solution concept <b>${E(mk.label)}</b>`
    : mk.role === "left" ? `<b>${E(C.labels.left)}</b> trajectory`
    : mk.role === "right" ? `<b>${E(C.labels.right)}</b> trajectory` : "";
  document.getElementById("detail").innerHTML = dealDetail(G, mk.index, mk.title || "deal", extra);
}

if (G) {
  const marks = [];
  Object.entries(G.solutions).forEach(([name, pt]) => marks.push({
    index: pt.index, kind: "star", color: "s3", label: pt.label, r: 7, role: "solution", concept: name,
    title: `${pt.label} — ${name}` }));
  G.party_best.forEach(pb => marks.push({ index: pb.index, kind: "diamond", color: "s3", r: 5, role: "solution",
    title: `best efficient deal for ${seatName(G, pb.party)} — surplus ${pb.surplus}` }));
  [[L, "s1", "left", C.labels.left], [R, "s2", "right", C.labels.right]].forEach(([side, color, role, label]) => {
    side.trajectory.forEach(p => marks.push({ index: p.index, kind: "circle", color, r: 6, role,
      label: String(p.ordinal), dx: role === "left" ? 8 : -8, dy: role === "left" ? -7 : 12,
      title: `${label} · move ${p.ordinal}: ${p.seat} ${p.atype}` }));
    const ai = side.outcome.deal_index;
    if (ai !== null && ai !== undefined) marks.push({ index: ai, kind: "square", color, r: 8, role,
      label: label.slice(0, 14) + " AGREED", dx: 10, dy: role === "left" ? 4 : 16, title: `${label}: the deal that closed` });
  });
  frontierChart(document.getElementById("chart"), G, marks, [
    { cls: "path1", indices: L.trajectory.map(p => p.index) },
    { cls: "path2", indices: R.trajectory.map(p => p.index) }], pickC);
}

const byIdx = (side) => Object.fromEntries(side.turns.map(t => [t.idx, t]));
const LT = byIdx(L), RT = byIdx(R);
const oracleOf = (side) => side.counterfactual_oracles[0] || side.oracle_names[0] || "";
let SHOW_CF = false;   // per-turn rational-agent counterfactual column, off by default (the seat swap IS the contrast)

function column(side, rows, which) {
  const prov = SHOW_CF ? annProvenance(side.annotations_source, side.counterfactual_oracles) : "";
  return prov + rows.map((row, i) => {
    const idx = row[which + "_idx"];
    const t = (which === "left" ? LT : RT)[idx];
    const head = i === C.divergence ? `<div class="divmark">first behavioural divergence — the two episodes are in different states from here on</div>` : "";
    if (t === undefined) return head + `<div class="turn"><div class="sub muted">round ${row.round} · ${E(row.phase)} · ${E(row.seat)} — this episode had already ended.</div></div>`;
    const card = el(turnCard(t, G, oracleOf(which === "left" ? L : R), { showCounterfactual: SHOW_CF }));
    if (row.different) card.classList.add("divergent");
    return head + card.outerHTML;
  }).join("");
}
function bindCompareDealLinks() {
  document.querySelectorAll("[data-deal]").forEach(a => a.addEventListener("click", ev => {
    ev.preventDefault();
    pickC({ index: Number(a.dataset.deal), title: "deal referenced from a transcript" });
    document.getElementById("frontier").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}
function renderColumns() {
  document.getElementById("col-left").innerHTML = column(L, C.aligned, "left");
  document.getElementById("col-right").innerHTML = column(R, C.aligned, "right");
  bindCompareDealLinks();
}
renderColumns();

/* Opt-in overlay of each turn's "what a rational agent would have done" column INSIDE the side-by-side. Off by
   default because the seat swap is itself the rational-vs-LLM contrast, so the extra column is only wanted when
   auditing per-turn. Injected next to the divergence-jump control so the static page needs no change. */
const cfToggle = el(`<button id="cf-toggle" aria-pressed="false">Show each turn's rational-agent counterfactual</button>`);
cfToggle.addEventListener("click", () => {
  SHOW_CF = !SHOW_CF;
  cfToggle.setAttribute("aria-pressed", String(SHOW_CF));
  renderColumns();
});
const jumpBtn = document.getElementById("jump-divergence");
(jumpBtn && jumpBtn.parentNode ? jumpBtn.parentNode : document.querySelector("main")).appendChild(cfToggle);
/* Open the detail panel on something meaningful: whichever side closed a deal, else the Nash solution. */
if (G) {
  const closed = [[R, "right", C.labels.right], [L, "left", C.labels.left]]
    .find(([side]) => side.outcome.deal_index !== null && side.outcome.deal_index !== undefined);
  const nbs = G.solutions.nash || Object.values(G.solutions)[0];
  pickC(closed
    ? { index: closed[0].outcome.deal_index, role: closed[1], title: `${closed[2]}: the deal that closed` }
    : { index: nbs.index, role: "solution", label: nbs.label, title: "Nash bargaining solution — neither side closed a deal" });
}

const jump = document.getElementById("jump-divergence");
if (jump) jump.addEventListener("click", () => {
  const node = document.querySelector(".divmark");
  if (node) node.scrollIntoView({ behavior: "smooth", block: "center" });
});
"""
