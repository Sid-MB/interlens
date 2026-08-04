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

"""The episode page's own wiring: build the marks, render the panels, and keep chart and transcript in sync.

The sync is two-way and goes through one function on each side. Clicking a numbered move on the frontier selects
that turn in the transcript and scrolls to it; selecting a turn — by click, by scrubber chip, by regret bar, or
with ``j``/``k`` — rings the deal that turn put on the chart. Before this, the chart could reach the transcript
but the transcript could not reach the chart, so a reader following the text had to hunt for the corresponding
point by eye.
"""
from __future__ import annotations

JS_EPISODE = r"""
const P = PAYLOAD, G = P.game;
PAYLOAD.seatNames = (P.seats || []).map(s => s.name);
let ORACLE = (P.counterfactual_oracles[0] || P.oracle_names[0] || "");
let CHART = null, PINNED = null, CURRENT_TURN = null;

function buildMarks() {
  if (!G) return [];
  const marks = [];
  Object.entries(G.solutions).forEach(([name, pt]) => marks.push({
    index: pt.index, ...solutionMarkStyle(name), label: pt.label, r: 7,
    title: `${pt.label} — ${name}${pt.scale_invariant ? " (scale-invariant)" : " (NOT scale-invariant across private scales)"}`,
    role: "solution", concept: name }));
  G.party_best.forEach(pb => marks.push({
    index: pb.index, kind: "diamond", color: "s3", r: 5, ...partyBestLabel(G, pb),
    title: `best efficient deal for ${seatName(G, pb.party)} (${pb.agent}) — surplus ${pb.surplus}`,
    role: "party_best", party: pb.party }));
  P.turns.forEach(t => {
    const o = (t.oracles || {})[ORACLE];
    if (o && o.best_deal_index !== null && o.best_deal_index !== undefined)
      marks.push({ index: o.best_deal_index, kind: "circle", color: "s2", r: 4.5, role: "oracle",
        title: `${ORACLE} oracle's deal at turn ${t.idx} (${t.seat})`, turn: t.idx, seat: t.seat });
  });
  P.trajectory.forEach(p => marks.push({
    index: p.index, kind: "circle", color: "s1", r: 6.5, label: String(p.ordinal), dx: 8, dy: -7,
    title: `move ${p.ordinal}: ${p.seat} ${p.atype} at turn ${p.turn_idx}`, role: "proposal", turn: p.turn_idx,
    /* The same three facts the title states, kept as FIELDS as well, so the hover card can phrase them itself
       rather than re-parsing a sentence. */
    ordinal: p.ordinal, seat: p.seat, atype: p.atype }));
  if (P.outcome.deal_index !== null && P.outcome.deal_index !== undefined)
    marks.push({ index: P.outcome.deal_index, kind: "square", color: "s1", r: 8, label: "AGREED", dx: 10, dy: 4,
      /* The turn the accept (or final ballot) landed on, derived server-side — see `episode.closing_turn_index`.
         Without it the AGREED square is the one mark standing for an event with nowhere to send a reader. */
      title: "the deal that closed", role: "agreed", turn: P.outcome.closing_turn_idx });
  return marks;
}

/* Hover paints the headline read; a click PINS the full per-party breakdown and, when the mark belongs to a
   turn, selects that turn in the transcript. Un-pinned hover never overwrites a pinned panel's identity — it
   still updates, because tracking the cloud is the point, but the pin survives an accidental pointer sweep by
   being restored on mouseleave. */
function pick(mk, clicked) {
  const extra = mk.role === "solution" ? `solution concept <b>${E(mk.label)}</b>`
    : mk.role === "oracle" ? `<b>${E(ORACLE)}</b> oracle's recommendation`
    : mk.role === "proposal" ? `move <b>${mk.label}</b> on the table`
    : mk.role === "agreed" ? "<b>the deal that closed</b>" : "";
  if (clicked) PINNED = { mk, extra };
  $("detail").innerHTML = dealDetail(G, mk.index, mk.title || "deal", extra, Boolean(clicked));
  /* Clicking a point that stands for a real event jumps the transcript to that turn and flashes the card; a point
     that is a property of the GAME (a solution concept, a party-best, a bare deal) has no event to jump to and
     leaves the page where it is. `markTurn`/`goToTurn` (js_hover) decide which is which, in one place. */
  if (clicked) goToTurn(markTurn(mk));
}

function drawChart() {
  if (!G) return;
  CHART = frontierChart($("chart"), G, buildMarks(),
    [{ cls: "path1", indices: P.trajectory.map(p => p.index) }], pick);
  if (CHART) CHART.svg.addEventListener("mouseleave", () => {
    if (PINNED) $("detail").innerHTML =
      dealDetail(G, PINNED.mk.index, PINNED.mk.title || "deal", PINNED.extra, true);
  });
}

/* The tabbed sidebar (conversation / frontier / issues), which follows the transcript as it scrolls. Mounted
   before the turn cards exist; `observeTurns()` below attaches the observer once they are drawn. */
const SIDEBAR = mountSidebar({ game: G, turns: P.turns, trajectory: P.trajectory, seats: P.seats,
                               onSelect: (idx) => SELECT(idx) });

/* One selection function for every entry point (chart mark, scrubber chip, regret bar, j/k, header click), and
   it is also what rings the chart mark — the transcript-to-chart half of the sync. */
const SELECT = makeSelectTurn((idx) => {
  CURRENT_TURN = idx;
  if (CHART) CHART.focusTurn(idx);
  if (SIDEBAR) SIDEBAR.setCurrent(idx, "select");
});

function drawTurns() {
  const host = $("turns");
  host.innerHTML = annProvenance(P.annotations_source, P.counterfactual_oracles)
    + scrubberHtml(P.turns)
    + `<div id="turnlist">` + P.turns.map(t => turnCard(t, G, ORACLE,
        { showCounterfactual: Boolean(ORACLE), infoLinks: true })).join("") + `</div>`;
  bindLazy(host, P.turns);
  bindCounterfactualCards(host, G, P.turns, ORACLE);
  host.querySelectorAll(".chip[data-goturn]").forEach(b =>
    b.addEventListener("click", () => SELECT(Number(b.dataset.turnidx))));
  host.querySelectorAll(".turnhd").forEach(hd => {
    const idx = Number(hd.closest(".turn").dataset.turnidx);
    hd.addEventListener("click", () => SELECT(idx, { scroll: false }));
    hd.addEventListener("keydown", ev => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); SELECT(idx, { scroll: false }); }
    });
  });
  host.querySelectorAll("[data-deal]:not([data-counterfactual]):not([data-package-preview])").forEach(a => a.addEventListener("click", ev => {
    ev.preventDefault();
    pick({ index: Number(a.dataset.deal), title: "deal referenced from the transcript" }, true);
    $("frontier").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  if (CURRENT_TURN !== null) SELECT(CURRENT_TURN, { scroll: false });
  if (SIDEBAR) SIDEBAR.observeTurns();     // the cards are new on every re-render, so the observer is too
}

function drawRegret() {
  if (!P.oracle_names.length) return;
  regretChart($("regret"), P.turns, ORACLE, idx => SELECT(idx));
}

/* ---- controls ---- */
const sel = $("oracle-select");
if (sel) sel.addEventListener("change", ev => { ORACLE = ev.target.value; drawChart(); drawRegret(); drawTurns(); });
const tbl = $("table-toggle");
function toggleTable() {
  if (!tbl) return;
  const on = tbl.getAttribute("aria-pressed") !== "true";
  tbl.setAttribute("aria-pressed", String(on));
  $("chart-table").hidden = !on;
}
if (tbl) tbl.addEventListener("click", toggleTable);
const expand = $("expand-all"), collapse = $("collapse-all");
if (expand) expand.addEventListener("click", () => setAllOpen($("turns"), true));
if (collapse) collapse.addEventListener("click", () => setAllOpen($("turns"), false));

drawChart(); drawRegret(); drawTurns();

/* Open on the deal that closed; with no deal, open on the Nash bargaining solution as the normative anchor. */
if (G) {
  const nbs = G.solutions.nash || Object.values(G.solutions)[0];
  pick(P.outcome.deal_index !== null && P.outcome.deal_index !== undefined
    ? { index: P.outcome.deal_index, role: "agreed", title: "the deal that closed" }
    : { index: nbs.index, role: "solution", label: nbs.label, title: "Nash bargaining solution — no deal closed" }, true);
}

/* j/k walk the transcript in order — the reason the shortcut exists is that a thirty-turn six-seat episode is a
   very long scroll and the interesting turn is rarely the one you land on. */
function stepTurn(delta) {
  const order = P.turns.map(t => t.idx);
  if (!order.length) return;
  const at = CURRENT_TURN === null ? -1 : order.indexOf(CURRENT_TURN);
  SELECT(order[Math.max(0, Math.min(order.length - 1, at + delta))]);
}
registerKeys(shellKeys().concat([
  { keys: ["j", "ArrowDown"], what: "next turn", run: () => stepTurn(1) },
  { keys: ["k", "ArrowUp"], what: "previous turn", run: () => stepTurn(-1) },
  { keys: ["f"], what: "jump to the frontier chart", run: () => { const n = $("frontier"); if (n) n.scrollIntoView({ behavior: "smooth", block: "start" }); } },
  { keys: ["t"], what: "show or hide the chart's numeric table", run: toggleTable },
  { keys: ["e"], what: "expand every panel in the transcript", run: () => setAllOpen($("turns"), true) },
  { keys: ["c"], what: "collapse every panel in the transcript", run: () => setAllOpen($("turns"), false) },
  { keys: ["0"], what: "reset the chart's zoom", run: () => { if (CHART) CHART.reset(); } },
  { keys: ["s"], what: "next sidebar tab (game info / conversation / frontier / issues / info)",
    run: () => { if (SIDEBAR) SIDEBAR.cycleTab(1); } },
]));
"""
