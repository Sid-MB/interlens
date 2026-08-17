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
# [implement: live-play/lane0] 2026-08-16
# [implement: live-play/laneD] 2026-08-16
# [implement: live-play/laneE] 2026-08-17
"""The live page's browser layer: subscribe, merge, redraw, and take the player's move.

The merge rule is one line and worth stating exactly, because everything else follows from it: a
``turn_appended`` event's ``turn`` is PUSHED onto ``PAYLOAD.turns`` — the array is mutated in place, never
replaced — and then the existing draw functions are called again. The episode page already re-renders entirely
from the in-memory ``PAYLOAD`` (that is how its seat and oracle selectors work), so a live page is that same page
with a growing array. Nothing about the chart, the regret bars, the hover cards or the transcript cards is
reimplemented here.

Per turn: push the row, insert the server-rendered ``bubble_html`` into the chat pane, ``drawChart()`` and
``drawRegret()``, wire the ONE new turn card, and re-mount the sidebar (it snapshots turns at mount, and a
re-mount is cheap enough to be the honest fix).

Reconnects are handled by ``EventSource``, which resends ``Last-Event-ID`` by itself; the session replays its log
from there, so a dropped connection costs nothing. A page that has been away long enough to be unsure re-fetches
``/state`` instead of trusting an incremental merge.

**The one merge case an append cannot express.** Three fields on a payload row — ``published``, ``offer_id`` and
``standing_deal_index`` — are properties of a turn's POSITION IN THE SEQUENCE, and a retried turn retroactively
flips an EARLIER row's ``published`` to ``False`` (``viz.episode.public_ledger``, and see ``live.payload
.turn_delta``, which re-derives the ledger over the whole accumulated list on the server). The
``turn_appended`` event carries the new row only, so corrections to earlier rows do not ride along. The client
therefore detects the one situation that produces them — an arriving turn occupying a (round, phase, seat) slot
some earlier row already holds, which is what a retry is — and reloads the page, which re-renders server-side
from ``/state`` and is correct by construction. Reloading rather than patching is deliberate: the chat bubbles
are server-rendered, so there is no client-side renderer to rebuild a corrected transcript with, and inventing
one is exactly the second bubble renderer this design exists to avoid. Retries are rare (one per seat, round and
phase at most) and the reload is rate-limited so a pathological run cannot spin.

**Why the episode wiring is here rather than imported.** ``viz.assets.js_episode`` wires the static page's draw
functions but does its per-card binding inside ``drawTurns``, where a live page cannot reach it to wire ONE
arriving card. The wiring below is that module's, restructured around :js:func:`wireTurnCard` so a full draw and
a single append share it. Everything it draws with — ``frontierChart``, ``turnCard``, ``mountSidebar``,
``regretChart``, the hover and counterfactual cards — is imported unchanged from ``viz.assets``.

Owned by lane D.
"""
from __future__ import annotations

# The live page's inline script: SSE client, PAYLOAD merge, human control dock, swap dock. Concatenated after
# the shared ``viz.assets.JS`` bundle (NOT after ``JS_EPISODE`` — this replaces it) into one <script> element.
JS_LIVE = r"""
/* ============================================================ episode wiring ============================== */
const P = PAYLOAD, G = P.game;
PAYLOAD.seatNames = (P.seats || []).map(s => s.name);
let ORACLE = (P.counterfactual_oracles[0] || P.oracle_names[0] || "");
let CHART = null, PINNED = null, CURRENT_TURN = null;

/* Which occupant a seat is held by by default (``occupantDefaults``, from the shared transcript module): a turn
   whose occupant differs from it changed hands, or is a person, and only those get badged — a seat played start
   to finish by one model would otherwise wear the same badge on all thirty of its turns. Recomputed as turns
   arrive, since the first turn a seat plays is what defines its default. */
let OCCUPANT_DEFAULTS = occupantDefaults(P.turns);

function buildMarks() {
  if (!G) return [];
  const marks = solutionReferenceMarks(G, 7);
  G.party_best.forEach(pb => marks.push({
    index: pb.index, kind: "diamond", color: "s3", r: 5, ...partyBestLabel(G, pb),
    title: `best efficient deal for ${seatName(G, pb.party)} (${pb.agent}) — surplus ${pb.surplus}`,
    role: "party_best", party: pb.party }));
  P.turns.forEach(t => {
    const o = (t.oracles || {})[ORACLE];
    if (o && o.best_deal_index !== null && o.best_deal_index !== undefined)
      marks.push({ index: o.best_deal_index, kind: "circle", color: "s2", r: 4.5, role: "oracle",
        title: o.counterfactual_role === "rational_private"
          ? `${ORACLE} rational counterfactual deal at turn ${t.idx} (${t.seat})`
          : `${ORACLE} oracle's deal at turn ${t.idx} (${t.seat})`, turn: t.idx, seat: t.seat,
        counterfactualRole: o.counterfactual_role, information: o.information });
  });
  P.trajectory.forEach(p => marks.push({
    index: p.index, kind: "circle", color: "s1", r: 6.5, label: String(p.ordinal), dx: 8, dy: -7,
    title: `move ${p.ordinal}: ${p.seat} ${p.atype} at turn ${p.turn_idx}`, role: "proposal", turn: p.turn_idx,
    ordinal: p.ordinal, seat: p.seat, atype: p.atype }));
  if (P.outcome.deal_index !== null && P.outcome.deal_index !== undefined)
    marks.push({ index: P.outcome.deal_index, kind: "square", color: "s1", r: 8, label: "AGREED", dx: 10, dy: 4,
      title: "the deal that closed", role: "agreed", turn: P.outcome.closing_turn_idx });
  return marks;
}

function pick(mk, clicked) {
  const extra = mk.role === "solution" ? `solution concept <b>${E(mk.label)}</b>`
    : mk.role === "oracle" ? `<b>${E(ORACLE)}</b> oracle's recommendation`
    : mk.role === "proposal" ? `move <b>${mk.label}</b> on the table`
    : mk.role === "agreed" ? "<b>the deal that closed</b>" : "";
  if (clicked) PINNED = { mk, extra };
  $("detail").innerHTML = dealDetail(G, mk.index, mk.title || "deal", extra, Boolean(clicked));
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

/* The sidebar snapshots the turn list at mount, so a live page re-mounts it after every arriving turn. Cheap:
   it is server-rendered HTML already in the document, and mounting only attaches handlers and the observer. */
let SIDEBAR = mountSidebar({ game: G, turns: P.turns, trajectory: P.trajectory, seats: P.seats,
                             onSelect: (idx) => SELECT(idx) });

const SELECT = makeSelectTurn((idx) => {
  CURRENT_TURN = idx;
  if (CHART) CHART.focusTurn(idx);
  if (SIDEBAR) SIDEBAR.setCurrent(idx, "select");
});

const CARD_OPTS = () => ({ showCounterfactual: Boolean(ORACLE), infoLinks: true,
                           occupantDefaults: OCCUPANT_DEFAULTS });

/* Everything one turn card needs to become interactive, in ONE function, because a live page wires a single
   arriving card with exactly what a full redraw wires all of them with. */
function wireTurnCard(node, t) {
  if (!node) return;
  bindLazy(node, [t]);
  bindCounterfactualCards(node, G, [t], ORACLE);
  node.querySelectorAll(".turnhd").forEach(hd => {
    hd.addEventListener("click", () => SELECT(t.idx, { scroll: false }));
    hd.addEventListener("keydown", ev => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); SELECT(t.idx, { scroll: false }); }
    });
  });
  node.querySelectorAll("[data-deal]:not([data-counterfactual]):not([data-package-preview])").forEach(a =>
    a.addEventListener("click", ev => {
      ev.preventDefault();
      pick({ index: Number(a.dataset.deal), title: "deal referenced from the transcript" }, true);
      $("frontier").scrollIntoView({ behavior: "smooth", block: "start" });
    }));
}

function wireScrubber(host) {
  host.querySelectorAll(".chip[data-goturn]:not([data-wired])").forEach(b => {
    b.dataset.wired = "1";
    b.addEventListener("click", () => SELECT(Number(b.dataset.turnidx)));
  });
}

function drawTurns() {
  const host = $("turns");
  host.innerHTML = annProvenance(P.annotations_source, P.counterfactual_oracles)
    + scrubberHtml(P.turns)
    + `<div id="turnlist">` + P.turns.map(t => turnCard(t, G, ORACLE, CARD_OPTS())).join("") + `</div>`;
  wireScrubber(host);
  P.turns.forEach(t => wireTurnCard($("turn-" + t.idx), t));
  if (CURRENT_TURN !== null) SELECT(CURRENT_TURN, { scroll: false });
  if (SIDEBAR) SIDEBAR.observeTurns();
}

function drawRegret() {
  if (!P.oracle_names.length) return;
  regretChart($("regret"), P.turns, ORACLE, idx => SELECT(idx));
}

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

if (G) {
  const nbs = G.solutions.nash || Object.values(G.solutions)[0];
  pick(P.outcome.deal_index !== null && P.outcome.deal_index !== undefined
    ? { index: P.outcome.deal_index, role: "agreed", title: "the deal that closed" }
    : { index: nbs.index, role: "solution", label: nbs.label, title: "Nash bargaining solution — no deal closed" }, true);
}

function stepTurn(delta) {
  const order = P.turns.map(t => t.idx);
  if (!order.length) return;
  const at = CURRENT_TURN === null ? -1 : order.indexOf(CURRENT_TURN);
  SELECT(order[Math.max(0, Math.min(order.length - 1, at + delta))]);
}

/* ============================================================ the live layer ============================== */
const LIVE = JSON.parse($("live-config").textContent);   // {sid, seq, phase, awaiting, occupants, seats, models, policies}
const API = "/api/session/" + encodeURIComponent(LIVE.sid);

/* ---------------------------------------------------------------- the human control dock --- */
/* The dock is rendered server-side, disabled, and this only opens/closes it and fills the parts that change
   with the moment: which offers may be accepted, which buttons are legal, and the running value of the package
   being built. Everything static about it — the one selector per issue, the private sheet, the scratchpad — is
   in the document already, so the layout does not move when it becomes this seat's turn. */
let PENDING = LIVE.awaiting || null;

function dockSheet() {
  /* The sheet the dock scores against: the one the server sent with the ask when a turn is open, else the one
     the page was rendered with. Never another seat's — this is the only private thing on the page. */
  if (PENDING && PENDING.sheet) return PENDING.sheet;
  const node = $("dock");
  const idx = node ? Number(node.dataset.seatIdx) : NaN;
  return Number.isInteger(idx) && G && G.sheets ? G.sheets[idx] : null;
}

function builtDeal() {
  if (!G) return [];
  return (G.issues || []).map((iss, j) => {
    const s = document.querySelector(`#dock-offer [data-issue="${j}"]`);
    return s ? Number(s.value) : 0;
  });
}

function dealIndexOf(deal) {
  if (!G || !G.strides) return null;
  let index = 0;
  deal.forEach((o, j) => { index += Number(o) * G.strides[j]; });
  return index;
}

/* What the package under construction is WORTH to the player, on their own sheet, against their own threshold.
   The whole point of the dock: a person negotiating without this is not playing the game a model seat plays. */
function paintValue() {
  const out = $("dock-value");
  if (!out) return;
  const sheet = dockSheet(), deal = builtDeal();
  if (!sheet || !sheet.values) { out.innerHTML = "<span class='muted'>no score sheet for this seat</span>"; return; }
  const u = deal.reduce((acc, o, j) => acc + Number(((sheet.values[j] || [])[o]) || 0), 0);
  const tau = Number(sheet.threshold || 0), surplus = u - tau;
  const index = dealIndexOf(deal);
  const named = G ? dealSummary(G, index) : "";
  out.innerHTML = `<span class="pill">your score <b>${N(u, 1)}</b></span>`
    + `<span class="pill">threshold τ <b>${THRESHOLD(tau)}</b></span>`
    + `<span class="pill">surplus <b class="${CLS(surplus)}">${SIGN(surplus, 1)}</b></span>`
    + (surplus < 0 ? `<span class="pill neg"><b>below your threshold</b> — you would do better walking away</span>` : "")
    + `<div class="sub muted">package ${E(named)}</div>`;
}

/* An offer already on the table, priced on the player's own sheet, so accepting is a decision rather than a
   guess. `state.offers` is the scenario's own registry (offer id -> option-index list) as the seat was
   conditioned on it, which is why the ids here are the ids the engine will accept.

   Accept and reject are gated SEPARATELY, each from its own list in the server's verdict, because they are not
   two halves of one permission: on the forced-final vote an offer can be acceptable and not rejectable. Reading
   one from the other — or from the phase string — would offer a move the server is about to refuse. */
function offerRow(id, deal, sheet, canAccept, canReject) {
  const u = (deal || []).reduce((acc, o, j) => acc + Number((((sheet || {}).values || [])[j] || [])[o] || 0), 0);
  const surplus = u - Number((sheet || {}).threshold || 0);
  return `<div class="offerrow">${
    canAccept ? `<button class="act-accept" data-accept="${E(id)}">Accept ${E(id)}</button>` : ""}${
    canReject ? `<button class="act-reject" data-reject="${E(id)}">Reject ${E(id)}</button>` : ""}
    <span class="sub">${E(G ? dealSummary(G, dealIndexOf(deal)) : "")}</span>
    <span class="pill">your score <b>${N(u, 1)}</b></span>
    <span class="pill">surplus <b class="${CLS(surplus)}">${SIGN(surplus, 1)}</b></span></div>`;
}

function paintOffers() {
  const host = $("dock-offers");
  if (!host) return;
  const state = (PENDING || {}).state || {}, legal = (PENDING || {}).legal || {};
  const offers = state.offers || {};
  const accept = legal.can_accept || [], reject = legal.can_reject || [];
  const ids = accept.concat(reject.filter(id => accept.indexOf(id) < 0));
  if (!ids.length) {
    host.innerHTML = "<div class='sub muted'>No offer on the table is yours to vote on right now.</div>";
    return;
  }
  const sheet = dockSheet();
  host.innerHTML = ids.map(id => offerRow(id, offers[id] || [], sheet,
                                          accept.indexOf(id) >= 0, reject.indexOf(id) >= 0)).join("");
  host.querySelectorAll("[data-accept]").forEach(b =>
    b.addEventListener("click", () => submit({ action: "accept", offer_id: b.dataset.accept })));
  host.querySelectorAll("[data-reject]").forEach(b =>
    b.addEventListener("click", () => submit({ action: "reject", offer_id: b.dataset.reject })));
}

function setDockOpen(open) {
  const dock = $("dock");
  if (!dock) return;
  dock.classList.toggle("open", Boolean(open));
  dock.querySelectorAll("button, select, textarea").forEach(n => { n.disabled = !open; });
  const head = $("dock-head");
  if (head) head.textContent = open
    ? `Your move — ${PENDING.seat}, round ${PENDING.round} of ${PENDING.deadline}, ${PENDING.phase}`
    : "Waiting — the dock opens when it is your seat's turn.";
  const legal = (PENDING || {}).legal || {};
  const gate = (id, ok) => { const n = $(id); if (n) n.disabled = !(open && ok); };
  gate("dock-propose", legal.can_offer);
  gate("dock-walk", legal.can_walk);
  gate("dock-pass", legal.can_pass);
  gateTalk();
}

/* Talk is a PASS carrying a message — the same turn a policy seat standing pat produces, which is the property
   that keeps a human's talk-only turn parsing like everyone else's. So an EMPTY talk is not a quiet no-op: the
   engine reads empty content as a well-formed pass, and the player would have said nothing while believing they
   spoke. The server refuses it; the button refuses to offer it. */
function gateTalk() {
  const btn = $("dock-talk"), msg = $("dock-msg"), dock = $("dock");
  if (!btn) return;
  const open = Boolean(dock && dock.classList.contains("open"));
  const legal = (PENDING || {}).legal || {};
  const said = Boolean(msg && msg.value.trim());
  btn.disabled = !(open && said && (legal.can_offer || legal.can_pass));
  btn.title = said ? "" : "type a message first — a talk turn with nothing in it is a pass";
}

function openDock(evt) {
  PENDING = evt;
  const dock = $("dock");
  if (dock && evt && Number.isInteger(evt.seat_idx)) dock.dataset.seatIdx = String(evt.seat_idx);
  dockError("");
  paintOffers();
  paintValue();
  setDockOpen(true);
  if (dock) dock.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeDock() {
  PENDING = null;
  setDockOpen(false);
  paintOffers();
}

function dockError(reason) {
  const n = $("dock-error");
  if (!n) return;
  n.innerHTML = reason ? `<div class="warn danger"><b>Refused:</b> ${E(reason)}</div>` : "";
}

/* A submission is a POST, and the dock stays open until the SERVER says the turn happened — a rejection comes
   back 400 with the reason and the seat is still waiting, which is the whole reason the form does not clear
   itself optimistically. */
function submit(move) {
  if (!PENDING) return;
  const msg = $("dock-msg"), note = $("dock-note");
  const body = Object.assign({ seat: PENDING.seat, message: msg ? msg.value : "",
                               note: note ? note.value : "" }, move);
  dockError("");
  fetch(API + "/act", { method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body) })
    .then(r => r.json().catch(() => ({})).then(d => ({ ok: r.ok, d })))
    .then(({ ok, d }) => {
      if (!ok) { dockError(d.error || d.reason || "the server refused this move"); return; }
      if (msg) msg.value = "";
      if (note) note.value = "";
      closeDock();
    })
    .catch(err => dockError(String(err)));
}

(function bindDock() {
  const dock = $("dock");
  if (!dock) return;
  dock.querySelectorAll("#dock-offer [data-issue]").forEach(s => s.addEventListener("change", paintValue));
  const msg = $("dock-msg");
  if (msg) msg.addEventListener("input", gateTalk);   // talk becomes available the moment there is something to say
  const on = (id, move) => { const n = $(id); if (n) n.addEventListener("click", () => submit(move())); };
  on("dock-propose", () => ({ action: "propose", deal: builtDeal() }));
  on("dock-walk", () => ({ action: "walk" }));
  on("dock-pass", () => ({ action: "pass" }));
  on("dock-talk", () => ({ action: "talk" }));
  paintValue();
  if (PENDING) openDock(PENDING); else setDockOpen(false);
})();

/* ---------------------------------------------------------------- the swap dock --- */
/* Reassigning a seat mid-game. The server decides whether a swap is allowed — it refuses one while that seat's
   human prompt is open, because the person is mid-decision and the turn is already theirs — so this posts and
   surfaces the refusal rather than second-guessing it locally. */
function swapError(idx, reason) {
  const n = $("swap-error-" + idx);
  if (n) n.innerHTML = reason ? `<span class="neg">${E(reason)}</span>` : "";
}

document.querySelectorAll("[data-swap-seat]").forEach(btn => {
  const idx = Number(btn.dataset.swapSeat);
  btn.addEventListener("click", () => {
    const val = id => { const n = $(id + "-" + idx); return n ? n.value : ""; };
    const config = { kind: val("swap-kind"), model_id: val("swap-model") || null,
                     policy: val("swap-policy") || null, thinking: val("swap-thinking") || "off",
                     display_name: val("swap-name"), instructions: "" };
    swapError(idx, "");
    fetch(API + "/swap", { method: "POST", headers: { "Content-Type": "application/json" },
                           body: JSON.stringify({ seat_idx: idx, seat_config: config }) })
      .then(r => r.json().catch(() => ({})).then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) { swapError(idx, d.error || d.reason || "the server refused this swap"); return; }
        /* The 200 carries the new occupant table, so the strip re-badges from the response rather than waiting
           for the `seat_swapped` broadcast to come back around — same map, one fewer round trip, and the
           broadcast still repaints for every OTHER browser watching. */
        paintOccupants(d.occupants);
      })
      .catch(err => swapError(idx, String(err)));
  });
});

function paintOccupant(seatIdx, label) {
  const n = $("occupant-" + seatIdx);
  if (n) n.textContent = label || "—";
}

/* A whole seat -> occupant map, as `hello` and a successful swap both carry it. Keyed by the name a seat SPEAKS
   under, which is what the transcript, the occupant map and the swap strip all agree on; the strip is indexed,
   so the seat list is the translation. */
function paintOccupants(map) {
  Object.entries(map || {}).forEach(([seat, label]) => {
    const at = (P.seats || []).findIndex(s => s.name === seat);
    if (at >= 0) paintOccupant(at, label);
  });
}

/* ---------------------------------------------------------------- status, usage, banners --- */
function setStatus(html, cls) {
  const n = $("live-status");
  if (n) n.innerHTML = `<div class="livestatus ${cls || ""}">${html}</div>`;
}

function setBanner(html, cls) {
  const n = $("live-banner");
  if (n) n.innerHTML = html ? `<div class="warn ${cls || ""}">${html}</div>` : "";
}

function paintUsage(u) {
  const n = $("live-usage");
  if (!n) return;
  const cap = u.cap_usd, near = cap ? (u.cost_usd >= 0.8 * cap) : false;
  n.innerHTML = `<span class="pill">spent <b class="${u.exhausted || near ? "neg" : ""}">$${N(u.cost_usd, 3)}</b></span>`
    + (cap ? `<span class="pill">cap <b>$${N(cap, 2)}</b></span>` : "<span class='pill muted'>no metered seat</span>")
    + `<span class="pill">${u.tokens_in} in / ${u.tokens_out} out</span>`
    + (u.exhausted ? `<span class="pill neg"><b>budget exhausted</b></span>`
       : (near ? `<span class="pill neg">approaching the cap</span>` : ""));
}

/* ---------------------------------------------------------------- the merge --- */
/* A retry re-plays a (round, phase, seat) slot, and doing so retroactively unpublishes the superseded row —
   a correction to an EARLIER row, which an append-only event cannot carry. Detecting it is exactly detecting a
   slot collision; the answer is to re-render from the server rather than to patch a transcript the client
   cannot rebuild (the bubbles are server-rendered). Rate-limited so a run that somehow retried repeatedly
   cannot turn into a reload loop. */
const RESYNC_KEY = "interlens-live-resync";
function slotTaken(turn) {
  return P.turns.some(t => t.idx !== turn.idx && t.round === turn.round && t.phase === turn.phase
                           && t.seat === turn.seat);
}
/* The rate limit is kept in sessionStorage rather than a variable, because the thing it is limiting DESTROYS
   every variable on the page. A guard that reset on each reload would permit exactly the loop it exists to
   prevent. */
function LAST_RESYNC() {
  try { return Number(sessionStorage.getItem(RESYNC_KEY)) || 0; } catch (e) { return 0; }
}
function resync(why) {
  const now = Date.now();
  if (now - LAST_RESYNC() < 5000) {
    console.warn("live: skipping a resync (" + why + ") — one just happened");
    return;
  }
  try { sessionStorage.setItem(RESYNC_KEY, String(now)); } catch (e) { /* storage may be denied */ }
  setStatus("Re-reading the episode from the server (" + E(why) + ")…", "");
  location.reload();
}

function appendTurn(evt) {
  const t = evt.turn;
  if (!t || P.turns.some(r => r.idx === t.idx)) return;
  if (slotTaken(t)) { resync("a turn was retried, which changes an earlier turn's published status"); return; }
  P.turns.push(t);                                    // mutate in place: every draw function reads this array
  if (typeof evt.rounds_used === "number") P.rounds_used = evt.rounds_used;
  if (evt.outcome_partial) P.outcome = Object.assign({}, P.outcome, evt.outcome_partial);
  /* The numbered move on the chart. A trajectory entry is a pure restatement of the row that just arrived
     (`viz.episode.episode_payload` builds it from exactly these four fields plus its position), so it is
     derived here rather than carried: the alternative is a second copy of the row on the wire, and a reload
     rebuilds the list from the same rule anyway. */
  const proposed = (t.action || {}).deal_index;
  if (proposed !== null && proposed !== undefined)
    P.trajectory.push({ turn_idx: t.idx, ordinal: P.trajectory.length + 1, seat: t.seat, kind: t.kind,
                        index: proposed, atype: (t.action || {}).atype });
  OCCUPANT_DEFAULTS = occupantDefaults(P.turns);
  const log = $("chatlog");
  if (log && evt.bubble_html && t.published !== false) {
    log.insertAdjacentHTML("beforeend", evt.bubble_html);
    log.lastElementChild.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  const list = $("turnlist");
  if (list) {
    list.insertAdjacentHTML("beforeend", turnCard(t, G, ORACLE, CARD_OPTS()));
    wireTurnCard($("turn-" + t.idx), t);
  }
  const scrub = document.querySelector("#turns .scrub");
  if (scrub) {
    /* One chip, built by the scrubber's own renderer and lifted out of the rail it came in — so the live rail
       and a redrawn one are the same markup rather than a second chip renderer that drifts. */
    const rail = el(scrubberHtml([t]));
    while (rail && rail.firstElementChild) scrub.appendChild(rail.firstElementChild);
    wireScrubber($("turns"));
  }
  drawChart(); drawRegret();
  SIDEBAR = mountSidebar({ game: G, turns: P.turns, trajectory: P.trajectory, seats: P.seats,
                           onSelect: (idx) => SELECT(idx) });
  if (SIDEBAR) SIDEBAR.observeTurns();
}

/* ---------------------------------------------------------------- the stream --- */
const SOURCE = new EventSource(API + "/events?last_event_id=" + encodeURIComponent(LIVE.seq || 0));

/* `hello` is connection metadata, not a logged event: the server stamps it with the id the stream RESUMED FROM,
   so it repeats an id already seen and must stay idempotent. Its body's `seq` is the session's current tip. */
SOURCE.addEventListener("hello", ev => {
  const d = JSON.parse(ev.data);
  paintOccupants(d.occupants);
  if (d.phase === "done") setStatus("This episode is over.", "done");
});

SOURCE.addEventListener("turn_started", ev => {
  const d = JSON.parse(ev.data);
  setStatus(`Waiting for <b>${E(d.seat)}</b>${d.occupant ? ` <span class="muted">(${E(d.occupant)})</span>` : ""}
             — round ${E(d.round)}, ${E(d.phase)}…`, "thinking");
});

SOURCE.addEventListener("turn_appended", ev => {
  const d = JSON.parse(ev.data);
  appendTurn(d);
  setStatus(`Turn ${E(d.turn.idx)} recorded — ${E(d.turn.seat)}.`, "");
});

SOURCE.addEventListener("awaiting_human", ev => {
  const d = JSON.parse(ev.data);
  openDock(d);
  setStatus(`<b>Your move</b> — ${E(d.seat)}, round ${E(d.round)} of ${E(d.deadline)}, ${E(d.phase)}.`, "you");
});

SOURCE.addEventListener("input_rejected", ev => {
  const d = JSON.parse(ev.data);
  dockError(d.reason);                                 // the dock stays open: the seat is still waiting
});

SOURCE.addEventListener("seat_swapped", ev => {
  const d = JSON.parse(ev.data);
  paintOccupant(d.seat_idx, d.to);
  swapError(d.seat_idx, "");
  setStatus(`<b>${E(d.seat)}</b> is now played by <b>${E(d.to)}</b>${d.from ? ` (was ${E(d.from)})` : ""}.`, "");
});

SOURCE.addEventListener("usage", ev => {
  const d = JSON.parse(ev.data);
  paintUsage(d);
});

SOURCE.addEventListener("episode_done", ev => {
  const d = JSON.parse(ev.data);
  closeDock();
  setStatus("This episode is over.", "done");
  const link = (P.paths || {}).episode;
  setBanner(`<b>Episode ${E(d.status)}.</b> ${E(JSON.stringify(d.outcome || {}))}`
    + (link ? ` <a href="file://${E(link)}">the saved episode record</a>` : ""),
    d.status === "done" ? "" : "danger");
  SOURCE.close();
});

SOURCE.addEventListener("error", ev => {
  /* Two different things arrive here: a session-level `error` EVENT (which has data) and the EventSource's own
     transport error (which does not, and which the browser is already retrying with Last-Event-ID). Only the
     first is worth showing a person. */
  if (!ev.data) { setStatus("Reconnecting to the live stream…", ""); return; }
  const d = JSON.parse(ev.data);
  setBanner(`<b>${d.fatal ? "Fatal: " : ""}</b>${E(d.message)}`, "danger");
  if (d.fatal) SOURCE.close();
});

SOURCE.addEventListener("episode_started", ev => {
  /* A page that was opened before the game began carries no geometry, so there is nothing to merge into. */
  if (!G) resync("the episode started");
});

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
  { keys: ["p"], what: "jump to your control dock", run: () => { const n = $("dock"); if (n) n.scrollIntoView({ behavior: "smooth", block: "center" }); } },
]));
"""
