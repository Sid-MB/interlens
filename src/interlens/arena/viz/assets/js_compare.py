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
# [rational_agents: viz-ux] 2026-08-03

"""The comparison page's wiring: one shared frontier carrying both trajectories, and two synchronized columns.

The two columns render with DIFFERENT element-id prefixes (``lturn-`` / ``rturn-``). They have to: both sides
number their turns from zero, so a single prefix put two elements with the same id on one page and every lookup
silently resolved to whichever came first.
"""
from __future__ import annotations

JS_COMPARE = r"""
const C = PAYLOAD, L = C.left, R = C.right, G = L.game || R.game;
PAYLOAD.seatNames = (L.seats || []).map(s => s.name);
let CCHART = null, CPINNED = null;

function pickC(mk, clicked) {
  const extra = mk.role === "solution" ? `solution concept <b>${E(mk.label)}</b>`
    : mk.role === "left" ? `<b>${E(C.labels.left)}</b> trajectory`
    : mk.role === "right" ? `<b>${E(C.labels.right)}</b> trajectory` : "";
  if (clicked) CPINNED = { mk, extra };
  $("detail").innerHTML = dealDetail(G, mk.index, mk.title || "deal", extra, Boolean(clicked));
}

if (G) {
  const marks = [];
  Object.entries(G.solutions).forEach(([name, pt]) => marks.push({
    index: pt.index, ...solutionMarkStyle(name), label: pt.label, r: 7, role: "solution", concept: name,
    title: `${pt.label} — ${name}` }));
  G.party_best.forEach(pb => marks.push({ index: pb.index, kind: "diamond", color: "s3", r: 5,
    ...partyBestLabel(G, pb), role: "party_best", party: pb.party,
    title: `best efficient deal for ${seatName(G, pb.party)} — surplus ${pb.surplus}` }));
  [[L, "s1", "left", C.labels.left], [R, "s2", "right", C.labels.right]].forEach(([side, color, role, label]) => {
    side.trajectory.forEach(p => marks.push({ index: p.index, kind: "circle", color, r: 6, role,
      label: String(p.ordinal), dx: role === "left" ? 8 : -8, dy: role === "left" ? -7 : 12,
      title: `${label} · move ${p.ordinal}: ${p.seat} ${p.atype}` }));
    const ai = side.outcome.deal_index;
    if (ai !== null && ai !== undefined) marks.push({ index: ai, kind: "square", color, r: 8, role,
      label: label.slice(0, 14) + " AGREED", dx: 10, dy: role === "left" ? 4 : 16, title: `${label}: the deal that closed` });
  });
  CCHART = frontierChart($("chart"), G, marks, [
    { cls: "path1", indices: L.trajectory.map(p => p.index) },
    { cls: "path2", indices: R.trajectory.map(p => p.index) }], pickC);
  if (CCHART) CCHART.svg.addEventListener("mouseleave", () => {
    if (CPINNED) $("detail").innerHTML =
      dealDetail(G, CPINNED.mk.index, CPINNED.mk.title || "deal", CPINNED.extra, true);
  });
}

const byIdx = (side) => Object.fromEntries(side.turns.map(t => [t.idx, t]));
const LT = byIdx(L), RT = byIdx(R);
const PREFIX = { left: "lturn-", right: "rturn-" };
const oracleOf = (side) => side.counterfactual_oracles[0] || side.oracle_names[0] || "";
let SHOW_CF = false;   // per-turn post-hoc oracle counterfactual column, off by default

function column(side, rows, which) {
  const prov = SHOW_CF ? annProvenance(side.annotations_source, side.counterfactual_oracles) : "";
  return prov + scrubberHtml(side.turns, PREFIX[which]) + rows.map((row, i) => {
    const idx = row[which + "_idx"];
    const t = (which === "left" ? LT : RT)[idx];
    const head = i === C.divergence ? `<div class="divmark" id="divmark-${which}">first behavioural divergence — the two episodes are in different states from here on</div>` : "";
    if (t === undefined) return head + `<div class="turn"><div class="sub muted">round ${row.round} · ${E(row.phase)} · ${E(row.seat)} — this episode had already ended.</div></div>`;
    const card = el(turnCard(t, G, oracleOf(which === "left" ? L : R),
                             { showCounterfactual: SHOW_CF, idPrefix: PREFIX[which] }));
    if (row.different) card.classList.add("divergent");
    return head + card.outerHTML;
  }).join("");
}

function bindColumn(which, side) {
  const host = $("col-" + which);
  bindLazy(host, side.turns);
  bindCounterfactualCards(host, G, side.turns, oracleOf(side));
  const select = makeSelectTurn(null, PREFIX[which]);
  host.querySelectorAll(".chip[data-goturn]").forEach(b =>
    b.addEventListener("click", () => select(Number(b.dataset.turnidx))));
  host.querySelectorAll(".turnhd").forEach(hd => {
    const idx = Number(hd.closest(".turn").dataset.turnidx);
    hd.addEventListener("click", () => select(idx, { scroll: false }));
  });
  host.querySelectorAll("[data-deal]:not([data-counterfactual]):not([data-package-preview])").forEach(a => a.addEventListener("click", ev => {
    ev.preventDefault();
    pickC({ index: Number(a.dataset.deal), title: "deal referenced from a transcript" }, true);
    $("frontier").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}

function renderColumns() {
  $("col-left").innerHTML = column(L, C.aligned, "left");
  $("col-right").innerHTML = column(R, C.aligned, "right");
  bindColumn("left", L); bindColumn("right", R);
}
renderColumns();

/* Opt-in overlay of each turn's post-hoc oracle column INSIDE the side-by-side. Off by
   default because the seat swap is itself the rational-vs-LLM contrast, so the extra column is only wanted when
   auditing per-turn. */
const cfToggle = $("cf-toggle");
if (cfToggle) cfToggle.addEventListener("click", () => {
  SHOW_CF = !SHOW_CF;
  cfToggle.setAttribute("aria-pressed", String(SHOW_CF));
  renderColumns();
});

/* Open the detail panel on something meaningful: whichever side closed a deal, else the Nash solution. */
if (G) {
  const closed = [[R, "right", C.labels.right], [L, "left", C.labels.left]]
    .find(([side]) => side.outcome.deal_index !== null && side.outcome.deal_index !== undefined);
  const nbs = G.solutions.nash || Object.values(G.solutions)[0];
  pickC(closed
    ? { index: closed[0].outcome.deal_index, role: closed[1], title: `${closed[2]}: the deal that closed` }
    : { index: nbs.index, role: "solution", label: nbs.label, title: "Nash bargaining solution — neither side closed a deal" }, true);
}

function jumpDivergence() {
  const node = document.querySelector(".divmark");
  if (node) node.scrollIntoView({ behavior: "smooth", block: "center" });
}
const jump = $("jump-divergence");
if (jump) jump.addEventListener("click", jumpDivergence);
const expandC = $("expand-all"), collapseC = $("collapse-all");
const bothCols = () => [$("col-left"), $("col-right")].filter(Boolean);
if (expandC) expandC.addEventListener("click", () => bothCols().forEach(c => setAllOpen(c, true)));
if (collapseC) collapseC.addEventListener("click", () => bothCols().forEach(c => setAllOpen(c, false)));

registerKeys(shellKeys().concat([
  { keys: ["d"], what: "jump to the divergence point", run: jumpDivergence },
  { keys: ["f"], what: "jump to the shared frontier chart", run: () => { const n = $("frontier"); if (n) n.scrollIntoView({ behavior: "smooth", block: "start" }); } },
  { keys: ["x"], what: "show or hide the per-turn post-hoc oracle counterfactual", run: () => { if (cfToggle) cfToggle.click(); } },
  { keys: ["e"], what: "expand every panel in both columns", run: () => bothCols().forEach(c => setAllOpen(c, true)) },
  { keys: ["c"], what: "collapse every panel in both columns", run: () => bothCols().forEach(c => setAllOpen(c, false)) },
  { keys: ["0"], what: "reset the chart's zoom", run: () => { if (CCHART) CCHART.reset(); } },
]));
"""
