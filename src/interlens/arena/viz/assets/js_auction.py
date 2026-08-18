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
# [implement: auctions | 2026-08-18 | lane auction-viz | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""The auction episode page's wiring: the DM stage scrubber, the hover card on the bid ladder, and the
cross-links between every mark and the turn it belongs to.

Deliberately thin. Every panel on an auction page is rendered server-side in
:mod:`~interlens.arena.viz.auction_page`, including all of its SVG and all of its numbers, so this layer only
adds behaviour that needs a pointer: with scripting off the page loses the stage filter and the rich hover, and
keeps every mark, every ``<title>`` tooltip and every table cell.

It shares the transcript layer with the negotiation page (``turnCard`` renders an auction turn without a game
geometry, which is the graceful-degradation path that already existed), and it does not touch the frontier
chart or the regret strip, neither of which an auction has.
"""
from __future__ import annotations

JS_AUCTION = r"""
const P = PAYLOAD, A = P.auction || {};
PAYLOAD.seatNames = (P.seats || []).map(s => s.name);
let CURRENT_TURN = null;

/* The turn rows, indexed by turn id, so a mark on the ladder can name the seat, the stage and the two
   counterfactual moves without the SVG carrying a copy of any of it. */
const AUCTION_TURNS = new Map((A.turns || []).map(t => [t.idx, t]));

function bidText(bids) {
  if (!bids || !bids.length) return "no priced action";
  return bids.map(b => (b.lot ? b.lot + " " : "") + N(b.amount, 0)).join(", ");
}

/* The hover card the design commits to: the played move beside what each computable rule would have played at
   the SAME state. Assembled here rather than baked into every mark's <title> because it is the same 8 lines
   for 800 marks, and because a <title> cannot carry structure. */
function ladderCard(t) {
  if (!t) return "";
  const cf = t.counterfactual || {};
  const rule = (name, label) => {
    const e = cf[name];
    if (!e) return "";
    if (e.error) return `<div class='cfrow'><span class='k'>${E(label)}</span> <span class='neg'>not scored</span></div>`;
    const agrees = e.agrees ? "<span class='pos'>same move</span>" : "<span class='differ'>differs</span>";
    return `<div class='cfrow'><span class='k'>${E(label)}</span> <b>${E(e.action || "none")}</b>
      ${E(bidText(e.bids))} ${agrees}</div>`;
  };
  return `<div class='hovercard'>
    <div class='hd'><b>${E(t.seat)}</b> — stage ${t.stage}, round ${t.round} <span class='muted'>turn ${t.idx}</span></div>
    <div class='cfrow'><span class='k'>played</span> <b>${E(t.atype)}</b> ${E(bidText(t.bids))}</div>
    ${rule("rational", "rational")}
    ${rule("oracle", "oracle")}
    <div class='sub muted'>own values ${E((t.own_values || []).join(", "))}${
      t.budget_remaining === null || t.budget_remaining === undefined ? "" : ` · budget left ${t.budget_remaining}`}</div>
    <div class='sub muted'>Click the mark to jump to this turn in the transcript.</div></div>`;
}

/* ---- the bid ladder ---- */
function bindLadder() {
  const svg = document.querySelector(".laddersvg");
  const host = $("ladder-detail");
  if (!svg) return;
  svg.querySelectorAll("[data-turn]").forEach(mk => {
    const idx = Number(mk.dataset.turn);
    if (host) {
      mk.addEventListener("mouseenter", () => { host.innerHTML = ladderCard(AUCTION_TURNS.get(idx)); });
      mk.addEventListener("focus", () => { host.innerHTML = ladderCard(AUCTION_TURNS.get(idx)); });
    }
    mk.addEventListener("click", () => selectAuctionTurn(idx));
    mk.setAttribute("tabindex", "0");
  });
}

/* ---- the DM stage scrubber ---- */
/* Filtering, never re-rendering: every stage's edges are already in the document, so the scrubber changes
   visibility only and the graph reads identically with scripting off. */
function bindScrubber() {
  const buttons = Array.from(document.querySelectorAll("[data-dmstage]"));
  if (!buttons.length) return;
  const edges = Array.from(document.querySelectorAll(".dmedge"));
  const apply = (want) => {
    edges.forEach(e => {
      const stages = String(e.dataset.stages || "").split(",").filter(Boolean);
      e.classList.toggle("dim", want !== "all" && !stages.includes(want));
    });
    buttons.forEach(b => {
      const on = b.dataset.dmstage === want;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", String(on));
    });
  };
  buttons.forEach(b => b.addEventListener("click", () => apply(b.dataset.dmstage)));
  apply("all");
}

/* ---- transcript sync ---- */
const SELECT_AUCTION = makeSelectTurn((idx) => { CURRENT_TURN = idx; });

function selectAuctionTurn(idx) {
  if (idx === null || idx === undefined) return;
  SELECT_AUCTION(idx);
}

function drawTurns() {
  const host = $("turns");
  const defaults = occupantDefaults(P.turns);
  host.innerHTML = scrubberHtml(P.turns)
    + `<div id="turnlist">` + P.turns.map(t => turnCard(t, null, "",
        { showCounterfactual: false, infoLinks: true, occupantDefaults: defaults })).join("") + `</div>`;
  bindLazy(host, P.turns);
  host.querySelectorAll(".chip[data-goturn]").forEach(b =>
    b.addEventListener("click", () => selectAuctionTurn(Number(b.dataset.turnidx))));
  host.querySelectorAll(".turnhd").forEach(hd => {
    const idx = Number(hd.closest(".turn").dataset.turnidx);
    hd.addEventListener("click", () => SELECT_AUCTION(idx, { scroll: false }));
  });
}

/* Every row of the counterfactual table is a link into the transcript; the anchor works with scripting off and
   the handler adds the flash and the selection. */
function bindCounterfactualTable() {
  document.querySelectorAll(".cftable tr[data-turn] a").forEach(a =>
    a.addEventListener("click", ev => { ev.preventDefault(); selectAuctionTurn(Number(a.closest("tr").dataset.turn)); }));
}

const expand = $("expand-all"), collapse = $("collapse-all");
if (expand) expand.addEventListener("click", () => setAllOpen($("turns"), true));
if (collapse) collapse.addEventListener("click", () => setAllOpen($("turns"), false));

drawTurns(); bindLadder(); bindScrubber(); bindCounterfactualTable();

function stepTurn(delta) {
  const order = P.turns.map(t => t.idx);
  if (!order.length) return;
  const at = CURRENT_TURN === null ? -1 : order.indexOf(CURRENT_TURN);
  SELECT_AUCTION(order[Math.max(0, Math.min(order.length - 1, at + delta))]);
}
registerKeys(shellKeys().concat([
  { keys: ["j", "ArrowDown"], what: "next turn", run: () => stepTurn(1) },
  { keys: ["k", "ArrowUp"], what: "previous turn", run: () => stepTurn(-1) },
  { keys: ["b"], what: "jump to the bid ladder", run: () => { const n = $("ladder"); if (n) n.scrollIntoView({ behavior: "smooth", block: "start" }); } },
  { keys: ["a"], what: "jump to the per-lot allocation strip", run: () => { const n = $("allocation"); if (n) n.scrollIntoView({ behavior: "smooth", block: "start" }); } },
  { keys: ["v"], what: "jump to the per-turn counterfactual table", run: () => { const n = $("counterfactuals"); if (n) n.scrollIntoView({ behavior: "smooth", block: "start" }); } },
  { keys: ["e"], what: "expand every panel in the transcript", run: () => setAllOpen($("turns"), true) },
  { keys: ["c"], what: "collapse every panel in the transcript", run: () => setAllOpen($("turns"), false) },
]));
"""
