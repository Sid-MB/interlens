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
utilitarianism's *lack* of scale invariance, egalitarian maximin, MNW's Caragiannis fallback). Pages are opened
off ``file://`` with no network, so this is HTML ``<sub>`` plus Unicode operators (``Σ Π τ ≥ −``) rather than
KaTeX or MathJax — it renders everywhere, adds nothing to the page weight, and copies as readable text.

**One card, never under the cursor.** A single element is reused for every point on the page, so two cards can
never be open at once; it is offset from the pointer and flips side or vertical anchor near a viewport edge. A
click *pins* it (the card becomes interactive and stays put until the next pick or ``Escape``), which is also
what makes it usable by touch, where there is no hover. Everything is styled from the shared CSS variables, so
it follows the light/dark theme like the rest of the page.
"""
from __future__ import annotations

JS_HOVER = r"""
/* ---- the explanation library ---------------------------------------------------------------------------
   A solution concept is a DEFINITION, not a label, and a reader who cannot recall which of five axiomatic
   points they are hovering cannot read the chart. Each entry: the full name, the objective it maximizes, and
   the one property that separates it from its neighbours. `math` is HTML (<sub> + Unicode), never LaTeX — the
   pages must render with no network. `u_i` is party i's utility, `tau_i` its walk-away threshold, `b_i` its
   ideal, and z_i = max(u_i - tau_i, 0) / (b_i - tau_i) the normalized surplus both chart axes are built from. */
const CONCEPT_NOTES = {
  nash: { name: "Nash bargaining solution",
    math: "argmax<sub>d</sub> &Sigma;<sub>i</sub> log(u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>)",
    note: "maximizes the <b>product</b> of every party's gain over its walk-away point &mdash; the unique split satisfying Nash's four axioms (efficiency, symmetry, invariance to affine rescaling, independence of irrelevant alternatives). Scale-invariant, so it does not care whose score sheet is written in bigger numbers." },
  kalai_smorodinsky: { name: "Kalai&ndash;Smorodinsky solution",
    math: "argmax<sub>d</sub> min<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>) / (b<sub>i</sub> &minus; &tau;<sub>i</sub>)",
    note: "equalizes each party's <b>fraction of its own ideal gain</b>, and so lifts the worst-treated fraction as high as it will go. Trades Nash's independence axiom for <b>monotonicity</b>: enlarging what is on the table can never leave a party worse off. Also scale-invariant." },
  utilitarian: { name: "utilitarian point",
    math: "argmax<sub>d</sub> &Sigma;<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>)",
    note: "maximizes <b>total</b> surplus, with no regard for how it is divided. <b class='neg'>NOT scale-invariant</b>: it adds up privately-scaled score sheets, so a party that happens to write larger numbers is handed the deal. Read it as a reference point, never as a fairness target." },
  egalitarian: { name: "egalitarian point",
    math: "argmax<sub>d</sub> min<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>)",
    note: "maximizes the <b>worst-off</b> party's surplus &mdash; Rawlsian maximin. It is blind to everything above that minimum, so two deals with the same worst-off party tie however differently they treat everyone else." },
  max_nash_welfare: { name: "maximum Nash welfare",
    math: "argmax<sub>d</sub> &Pi;<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>),&nbsp; u<sub>i</sub>(d) &gt; &tau;<sub>i</sub> &forall;i",
    note: "the Nash product over the <b>strictly</b> individually-rational deals. When no deal clears every threshold it falls back to the <b>Caragiannis</b> rule &mdash; first maximize how many parties are above threshold, then the Nash product among exactly those &mdash; so the point exists even where the strict problem is empty." },
};

/* The non-concept point kinds. `what` is answered per-point (it names seats and turns), so these carry only the
   standing explanation of what that kind of mark means. */
const ROLE_NOTES = {
  party_best: "the <b>frontier deal this party would dictate</b> if it could choose alone: argmax<sub>d</sub> u<sub>i</sub>(d) over the deals that are both efficient and able to close. The gap between it and the deal that closed is what this party gave up by having to agree with anyone.",
  oracle: "what the <b>best-response oracle</b> would have put on the table at this turn, holding the same information the seat had. The chart's regret strip is the value of this deal minus the value of what the seat actually did.",
  proposal: "a deal the negotiation actually put <b>on the table</b>. The numbered path traces the order of play, so the walk from the first move to the last is the concession pattern.",
  agreed: "the deal the parties <b>closed on</b>. Everything the episode is scored against &mdash; capture, distance to the Nash solution, whether anyone was left below threshold &mdash; is read off this point.",
  standing: "the deal <b>standing on the table</b> at the turn in view: the most recent live offer, which is what the next seat is answering.",
};

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
    return { head: E(mk.label || c.name) + " &mdash; " + c.name, sub: "axiomatic solution concept",
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

/* The whole card for one point. Pure function of (game, mark): the same markup is produced whether the card was
   opened by hover, by keyboard focus, or by a pin, so there is only one thing to test. */
function hoverCardHtml(game, mk) {
  const index = mk.index;
  if (!game || index === null || index === undefined) return "";
  const id = pointIdentity(game, mk), st = dealStats(game, index);
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
    <div class="hfoot">click to pin &middot; Esc to dismiss</div>`;
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
  function open(game, mk, evt, doPin) {
    const html = hoverCardHtml(game, mk);
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
    show(game, mk, evt) { if (!pinned) open(game, mk, evt, false); },
    /* Follow the pointer without rebuilding the card — the caller uses this while the nearest deal is unchanged. */
    move(evt) { if (pinned || !node.classList.contains("on")) return; const [x, y] = anchorOf(evt); place(x, y); },
    pin(game, mk, evt) { open(game, mk, evt, true); },
    hide(force) { if (pinned && !force) return; pinned = false; node.classList.remove("on", "pinned"); },
    isPinned: () => pinned,
  };
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") HOVER_CARD.hide(true); });
  return HOVER_CARD;
}
"""
