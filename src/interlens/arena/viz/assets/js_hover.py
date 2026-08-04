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
# [rational_agents: viz-hovers] 2026-08-03

"""Browser layer, part 2a: the rich hover card that EVERY point on the frontier chart carries.

The chart plots the whole deal space, so a reader hovering a dot is asking three questions at once — *what am I
looking at*, *what deal is it*, and *who does it favour*. Before this the answer was a one-line SVG ``<title>``
plus a panel far below the chart, so identifying a point meant looking away from it. The card answers all three
at the pointer:

1. **What it is.** Role-specific phrasing: a solution concept, a party's dictated best, an oracle's move at a
   turn, a numbered move by a seat, the deal that closed, or an ordinary point in the cloud.
2. **The deal**, in words — ``Location: Kestrel Park · Power: solar with storage`` — decoded client-side from the
   deal index against the issue/option name table the game payload already ships, so no per-deal strings travel.
3. **The numbers**: the deal-level summary (mean and min normalized surplus, Nash welfare, distance below the
   frontier, IR and feasibility flags) and a compact per-party table sorted by normalized surplus — the "who
   wins most here" ranking, with each party's utility, threshold, raw surplus and a bar.

**The maths is written out, without a maths library.** The five solution concepts are definitions, not labels, so
each carries its formula and the one property that distinguishes it (Nash's axioms, KS's monotonicity,
utilitarianism's *lack* of scale invariance, egalitarian maximin, MNW's Caragiannis fallback). Those definitions
live in :mod:`interlens.arena.viz.concepts` and are serialized into the page from there, so a second place that
explains a concept to a reader cannot disagree with this one. Pages are opened off ``file://`` with no network, so
the formulae are HTML ``<sub>`` plus Unicode operators (``Σ Π τ − >``) rather than KaTeX or MathJax — they render
everywhere, add nothing to the page weight, and copy as readable text.

**One card, never under the cursor.** A single element is reused for every point on the page, so two cards can
never be open at once; it is offset from the pointer and flips side or vertical anchor near a viewport edge. A
click *pins* it (the card becomes interactive and stays put until the next pick or ``Escape``), which is also
what makes it usable by touch, where there is no hover. Everything is styled from the shared CSS variables, so
it follows the light/dark theme like the rest of the page.
"""
from __future__ import annotations

import json

from ..concepts import AXIS_NOTES, CONCEPT_MATH, PROJECTION_CAVEAT, ROLE_NOTES

# The explanations are SERIALIZED from `viz.concepts`, not restated here: anything else that explains a solution
# concept to a reader (a server-rendered help panel, a writeup) reads the same dict, so the axioms cannot end up
# in two versions that disagree. They are JSON literals in a data position, never interpolated into markup.
_DEFS = (f"const CONCEPT_NOTES = {json.dumps(CONCEPT_MATH, ensure_ascii=False)};\n"
         f"const ROLE_NOTES = {json.dumps(ROLE_NOTES, ensure_ascii=False)};\n"
         f"const AXIS_NOTES = {json.dumps(AXIS_NOTES, ensure_ascii=False)};\n"
         f"const PROJECTION_CAVEAT = {json.dumps(PROJECTION_CAVEAT, ensure_ascii=False)};\n")

JS_HOVER = _DEFS + r"""

/* What a mark IS, in role-specific words. Returns {head, sub, note} — `head` is the identity line, `sub` the
   qualifier under it, `note` the standing explanation (empty for an ordinary cloud deal, which needs none). */
function pointIdentity(game, mk) {
  const d = game.deals, i = mk.index;
  const role = mk.role || "deal";
  const seat = (mk.seat !== undefined && mk.seat !== null) ? String(mk.seat)
             : (mk.party !== undefined && mk.party !== null) ? seatName(game, mk.party) : "";
  /* The cloud phrasing, and the honest fallback for a mark whose role this layer does not know (the comparison
     page marks a point by SIDE): say what the mark says about itself and place it, rather than attaching an
     explanation that might be the wrong one. */
  const placed = d.pareto[i] ? "on the Pareto frontier &mdash; no party can gain without another losing"
                             : "dominated &mdash; some other deal is at least as good for everyone";
  if (role === "solution") {
    const c = CONCEPT_NOTES[mk.concept] || null;
    if (!c) return { head: E(mk.title || mk.label || "reference point"), sub: placed, note: "" };
    /* Scale invariance is read from the STORED solution record rather than hardcoded here, so a concept the
       solver marks as scale-dependent always says so on its own card — this is the one property that decides
       whether a point is a fairness target or only a reference, and the chart's whole embedding depends on it. */
    const inv = (game.solutions[mk.concept] || {}).scale_invariant;
    return { head: E(mk.label || c.name) + " &mdash; " + c.name,
             sub: "axiomatic solution concept" + (inv === undefined ? ""
                  : inv ? " &middot; scale-invariant"
                        : ' &middot; <b class="neg">not scale-invariant</b> across private score sheets'),
             note: `<span class="hmath">${c.math}</span> ${c.note}` };
  }
  if (role === "party_best")
    return { head: "Party-best &mdash; " + E(seat), sub: "the deal this party would dictate",
             note: ROLE_NOTES.party_best };
  if (role === "oracle")
    return { head: "Oracle's move" + (mk.turn !== undefined ? " at turn " + E(mk.turn) : ""),
             sub: seat ? "the rational counterfactual for " + E(seat) : "the rational counterfactual",
             note: ROLE_NOTES.oracle };
  if (role === "proposal")
    return { head: "Move " + E(mk.ordinal !== undefined ? mk.ordinal : mk.label || "?")
                   + (seat ? " &mdash; " + E(seat) : ""),
             sub: (mk.atype ? actKind(mk.atype).glyph + " " + actKind(mk.atype).word : "tabled")
                  + (mk.turn !== undefined ? " at turn " + E(mk.turn) : ""),
             note: ROLE_NOTES.proposal };
  if (role === "agreed")
    return { head: "AGREED", sub: "the deal that closed", note: ROLE_NOTES.agreed };
  if (role === "standing")
    return { head: "On the table", sub: "the live offer at this turn", note: ROLE_NOTES.standing };
  if (mk.title) return { head: E(mk.title), sub: placed, note: "" };
  return { head: d.pareto[i] ? "Efficient deal" : "Deal in the space", sub: placed, note: "" };
}

/* The deal in words: "Location: Kestrel Park · Power: solar with storage · …". Decoded from the index against
   the issue/option names the game payload ships once, so |D| deals cost |D| integers, not |D| strings. */
function dealWords(game, index) {
  const named = dealNamed(game, index);
  if (!named) return "";
  return Object.entries(named).map(([k, v]) =>
    `<span class="hopt"><span class="muted">${E(k)}:</span> ${E(v)}</span>`).join('<span class="hsep">&middot;</span>');
}

/* The deal-level summary, in the scale-invariant z coordinates both axes use. Nash welfare is the geometric mean
   of the z's — the readable form of the Nash product, and zero the moment any party is left below threshold,
   which is exactly the property that makes it the right headline number. */
function dealStats(game, index) {
  const d = game.deals, z = d.xn[index], s = d.s[index], n = z.length;
  const mean = z.reduce((a, b) => a + b, 0) / n, worst = Math.min(...z);
  const nw = z.some(v => v <= 0) ? 0 : Math.exp(z.reduce((a, b) => a + Math.log(b), 0) / n);
  const below = s.filter(v => v < 0).length;
  return { mean, worst, nw, below, pareto: Boolean(d.pareto[index]), ir: Boolean(d.ir[index]),
           feasible: Boolean(d.feasible[index]), dfront: d.d_frontier[index] };
}

/* "Who wins most here": every party, sorted by normalized surplus descending, with the numbers the ranking is a
   summary OF (utility, threshold, raw surplus) beside the bar — so the order is never asserted without its
   evidence. Small text and tight rows: it sits inside a hover card, not on the page. */
function rankTable(game, index) {
  const d = game.deals, z = d.xn[index], u = d.u[index], s = d.s[index];
  const order = game.parties.map((p, i) => i).sort((a, b) => z[b] - z[a]);
  const rows = order.map((i, rank) => {
    const ok = s[i] >= 0, w = Math.max(0, Math.min(1, z[i]));
    return `<tr><td class="hrk">${rank + 1}</td><td class="hnm">${E(seatName(game, i))}</td>
      <td class="hnum">${N(u[i], 1)}</td><td class="hnum muted">${N(game.thresholds[i], 1)}</td>
      <td class="hnum ${ok ? "pos" : "neg"}">${SIGN(s[i], 1)}</td>
      <td class="hbar"><span class="meter"><i class="${ok ? "ok" : "bad"}" style="width:${(w * 100).toFixed(1)}%"></i></span></td>
      <td class="hnum">${N(z[i] * 100, 0)}%</td></tr>`;
  }).join("");
  return `<table class="hrank"><thead><tr><th></th><th>party</th><th>u</th><th>&tau;</th><th>surplus</th>
    <th></th><th>z</th></tr></thead><tbody>${rows}</tbody></table>`;
}

/* ---- the chart-to-transcript jump ------------------------------------------------------------------------
   Only marks that stand for a REAL event in the episode navigate: a numbered move, the oracle's move at a turn,
   and the AGREED square (whose closing turn is derived server-side, `episode.closing_turn_index`). A solution
   concept, a party-best diamond and an ordinary cloud deal are properties of the GAME, not things that happened,
   so they have no turn to go to and must not move the page — a click on them only pins the card.

   `turn-<idx>` is the turn cards' id contract, and the same one `makeSelectTurn` and the scrubber chips use. */
const EVENT_ROLES = ["proposal", "oracle", "agreed", "standing"];
const markTurn = (mk) => (mk && EVENT_ROLES.indexOf(mk.role) >= 0 && mk.turn !== undefined && mk.turn !== null)
  ? mk.turn : null;

/* Land on a turn and say so: select it (the page's own selection function, which scrolls it into view and rings
   its chart mark) and flash the card, because a smooth scroll that ends on one of thirty near-identical cards
   leaves a reader unsure which one they were sent to. The flash is a class the CSS animates and removes. */
function flashTurn(idx) {
  const node = document.getElementById("turn-" + idx);
  if (!node) return null;
  // Exactly one landing at a time: a previous flash that has not timed out yet would otherwise leave two cards
  // claiming to be the place the reader was just sent.
  document.querySelectorAll(".turn.flash").forEach(n => n.classList.remove("flash"));
  void node.offsetWidth;                       // restart the animation even on a repeat jump to the same turn
  node.classList.add("flash");
  setTimeout(() => node.classList.remove("flash"), 1200);
  return node;
}
function goToTurn(idx) {
  if (idx === null || idx === undefined) return;
  if (typeof SELECT === "function") SELECT(idx);          // absent on a page with no transcript (the comparison)
  else { const n = document.getElementById("turn-" + idx); if (n) n.scrollIntoView({ behavior: "smooth", block: "center" }); }
  flashTurn(idx);
}

/* The whole card for one point. Pure function of (game, mark): the same markup is produced whether the card was
   opened by hover, by keyboard focus, or by a pin, so there is only one thing to test. */
function hoverCardHtml(game, mk) {
  const index = mk.index;
  if (!game || index === null || index === undefined) return "";
  const id = pointIdentity(game, mk), st = dealStats(game, index), turn = markTurn(mk);
  const flags = [
    `<span class="pill">mean z <b>${N(st.mean * 100, 0)}%</b></span>`,
    `<span class="pill">worst-off z <b class="${st.worst > 0 ? "pos" : "neg"}">${N(st.worst * 100, 0)}%</b></span>`,
    `<span class="pill">Nash welfare <b>${N(st.nw, 3)}</b></span>`,
    st.pareto ? `<span class="pill">on the frontier</span>`
              : `<span class="pill">below the frontier by <b>${N(st.dfront, 3)}</b></span>`,
    st.ir ? `<span class="pill">individually rational</span>`
          : `<span class="pill"><b class="neg">${st.below}</b> below threshold</span>`,
    st.feasible ? `<span class="pill">can close</span>` : `<span class="pill"><b class="neg">cannot close</b></span>`,
  ].join("");
  return `<div class="hhd"><span class="hkind">${id.head}</span><span class="muted">deal #${index}</span></div>
    <div class="hsub">${id.sub}</div>
    ${id.note ? `<div class="hnote">${id.note}</div>` : ""}
    <div class="hdeal">${dealWords(game, index)}</div>
    <div class="pills">${flags}</div>
    <div class="hcap">who wins most here</div>
    ${rankTable(game, index)}
    <div class="hfoot">${turn === null ? "click to pin &middot; Esc to dismiss"
      : `<button type="button" class="goturn" data-goto="${turn}">go to turn ${E(turn)} &rarr;</button>
         <span class="muted">click the point to pin and jump</span>`}</div>`;
}

/* ---- the floating card ----------------------------------------------------------------------------------
   ONE element for the whole page, created on first use and reused by every chart on it (the main frontier chart
   and the sidebar's mini chart both call `frontierChart`, so both get cards without knowing this exists). While
   un-pinned it is `pointer-events:none`, so it can never eat the hover that is keeping it open. */
let HOVER_CARD = null;
function hoverCard() {
  if (HOVER_CARD) return HOVER_CARD;
  const node = document.createElement("div");
  node.className = "hcard";
  node.setAttribute("role", "tooltip");
  document.body.appendChild(node);
  let pinned = false;

  /* Offset from the pointer, then flipped rather than clamped when it would run off: a card that overlaps the
     point it describes hides the thing the reader is pointing at. */
  function place(x, y) {
    const pad = 10, w = node.offsetWidth || 320, h = node.offsetHeight || 240;
    const vw = window.innerWidth || 1200, vh = window.innerHeight || 800;
    let left = x + 18, top = y + 18;
    if (left + w + pad > vw) left = x - w - 18;
    if (top + h + pad > vh) top = y - h - 18;
    node.style.left = Math.max(pad, Math.min(left, vw - w - pad)) + "px";
    node.style.top = Math.max(pad, Math.min(top, vh - h - pad)) + "px";
  }
  /* A keyboard focus or a touch has no pointer position, so anchor off the mark's own box instead. */
  const anchorOf = (evt) => {
    if (evt && typeof evt.clientX === "number" && (evt.clientX || evt.clientY)) return [evt.clientX, evt.clientY];
    const box = evt && evt.target && evt.target.getBoundingClientRect && evt.target.getBoundingClientRect();
    return box ? [box.left + box.width / 2, box.top + box.height / 2] : [40, 80];
  };
  function open(html, evt, doPin) {
    if (!html) return;
    pinned = Boolean(doPin);
    node.innerHTML = html;
    node.classList.toggle("pinned", pinned);
    node.classList.add("on");
    const [x, y] = anchorOf(evt);
    place(x, y);
  }
  HOVER_CARD = {
    node,
    show(game, mk, evt) { if (!pinned) open(hoverCardHtml(game, mk), evt, false); },
    /* Follow the pointer without rebuilding the card — the caller uses this while the nearest deal is unchanged. */
    move(evt) { if (pinned || !node.classList.contains("on")) return; const [x, y] = anchorOf(evt); place(x, y); },
    pin(game, mk, evt) { open(hoverCardHtml(game, mk), evt, true); },
    /* An explanation with no deal behind it — the axis-title info controls. Same element and styling as a point
       card, so the two read as one mechanism rather than two kinds of tooltip. */
    note(title, html, evt, doPin) {
      open(`<div class="hhd"><span class="hkind">${title}</span></div><div class="hnote">${html}</div>
            <div class="hnote hproj">${PROJECTION_CAVEAT}</div>
            <div class="hfoot">${doPin ? "pinned &middot; Esc to dismiss" : "click to pin"}</div>`, evt, doPin);
    },
    hide(force) { if (pinned && !force) return; pinned = false; node.classList.remove("on", "pinned"); },
    isPinned: () => pinned,
  };
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") HOVER_CARD.hide(true); });
  /* The card is only interactive while pinned, so its "go to turn N" button lives here rather than on every
     caller: one listener, and it works for whichever point is pinned. */
  node.addEventListener("click", (ev) => {
    const go = ev.target.closest("[data-goto]");
    if (go) goToTurn(Number(go.dataset.goto));
  });
  return HOVER_CARD;
}
"""
