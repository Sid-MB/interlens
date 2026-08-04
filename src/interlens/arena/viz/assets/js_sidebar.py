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
# [rational_agents: viz-sidebar] 2026-08-03

"""Browser layer, part 5: the tabbed sidebar and the scroll sync that drives it.

The sidebar's three live tabs all answer the same question — *what did the table look like at the point in the
transcript I am reading?* — so they share one piece of state: the turn currently in the viewport, tracked with an
``IntersectionObserver`` over the turn cards rather than a scroll handler (no per-frame work, and the browser
does the geometry).

- **Conversation** re-anchors the public chat to the acting seat: that seat's bubbles move to the right, everyone
  else's stay left, and the list scrolls itself so the turn being read is the one in the middle. The bubbles are
  rendered server-side and never rebuilt — the point of view is two class toggles.
- **Frontier** redraws the main chart's geometry restricted to what had been proposed by that turn: earlier
  proposals numbered, the deal standing on the table squared, later ones ghosted. It is drawn through the SAME
  ``frontierChart`` the page's main chart uses, so the two cannot drift apart.
- **Issues** shows the acting seat's private valuation of each issue, with a marker on the option the deal on the
  table picks. The bars, ticks and threshold line come from the server-rendered SVG; the marker is placed by
  reading each tick's own ``data-y``, so the browser never re-derives the scale.
- **Info** is a standing reading guide. Inline information buttons open it directly at the oracle explanation.

The seat shown in the issue tab can be pinned with the picker; the next time scrolling changes which turn is in
view the pin is released, because a pin that silently survived a scroll is how a reader ends up reading one
seat's bars believing they are another's.
"""
from __future__ import annotations

JS_SIDEBAR = r"""
/* Mount the tabbed sidebar. `cfg`: {game, turns, trajectory, seats, onSelect(turnIdx)}. Returns a handle the
   page uses to (re)observe turn cards after a re-render and to push a selection in from elsewhere, or null when
   the page carries no sidebar (the comparison page). */
function mountSidebar(cfg) {
  const root = $("sidebar");
  if (!root) return null;
  const G = cfg.game, TURNS = cfg.turns || [], TRAJ = cfg.trajectory || [];
  const BY_IDX = Object.fromEntries(TURNS.map(t => [String(t.idx), t]));
  let current = null, pinnedParty = null, miniStale = true, lastObserved = null;
  const momentCache = {};

  /* ---------------------------------------------------------------- tabs --- */
  const tabs = Array.prototype.slice.call(root.querySelectorAll(".tab"));
  const keyOf = (t) => t.dataset.tab;
  const activeTab = () => {
    const t = tabs.find(t => t.getAttribute("aria-selected") === "true");
    return t ? keyOf(t) : (tabs.length ? keyOf(tabs[0]) : null);
  };
  function showTab(key) {
    tabs.forEach(t => {
      const on = keyOf(t) === key;
      t.setAttribute("aria-selected", String(on));
      const pane = $("pane-" + keyOf(t));
      if (pane) pane.hidden = !on;
    });
    if (key === "frontier" && miniStale) drawMini();
    if (key === "chat") scrollChatTo(current);
  }
  tabs.forEach(t => t.addEventListener("click", () => showTab(keyOf(t))));
  /* Measurements outside the sidebar link into the standing guide. Scroll the PANE, not the whole document,
     because the sidebar itself is sticky and moving the transcript would destroy the reader's place. */
  document.addEventListener("click", (ev) => {
    const link = ev.target.closest && ev.target.closest("[data-info-target]");
    if (!link) return;
    ev.preventDefault();
    showTab("info");
    const pane = $("pane-info"), target = $(link.dataset.infoTarget);
    if (pane && target) pane.scrollTop = Math.max(0, target.offsetTop - pane.offsetTop - 8);
  });
  function cycleTab(delta) {
    if (!tabs.length) return;
    const at = tabs.findIndex(t => keyOf(t) === activeTab());
    showTab(keyOf(tabs[(at + (delta || 1) + tabs.length) % tabs.length]));
  }

  /* ------------------------------------------------------ conversation --- */
  /* The point of view is a class, not a re-render: every bubble already carries the seat that spoke it. */
  function paintChat(idx, seat) {
    root.querySelectorAll(".bubble").forEach(b => {
      const at = Number(b.dataset.turnidx);
      b.classList.toggle("self", Boolean(seat) && b.dataset.seat === seat);
      b.classList.toggle("future", idx !== null && at > idx);
      b.classList.toggle("cur", at === idx);
    });
    scrollChatTo(idx);
  }
  /* Scroll the bubble list — never the page — so the turn being read sits in the middle of the pane. */
  function scrollChatTo(idx) {
    const pane = $("pane-chat"), bubble = idx === null ? null : $("bub-" + idx);
    if (!pane || !bubble || pane.hidden) return;
    const pr = pane.getBoundingClientRect(), br = bubble.getBoundingClientRect();
    const top = pane.scrollTop + (br.top - pr.top) - (pr.height - br.height) / 2;
    if (pane.scrollTo) pane.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    else pane.scrollTop = Math.max(0, top);
  }

  /* ---------------------------------------------------------- frontier --- */
  /* Same geometry as the main chart, restricted in time: proposals up to the turn in view are numbered, the deal
     standing on the table is squared, later ones are ghosted rather than dropped so the shape of the cloud a
     reader has been looking at does not jump. */
  function miniMarks(upto, standing) {
    const marks = [];
    if (!G) return marks;
    Object.entries(G.solutions || {}).forEach(([name, pt]) => marks.push({
      index: pt.index, ...solutionMarkStyle(name), label: pt.label, r: 6,
      title: pt.label + " — " + name, role: "solution", concept: name }));
    (G.party_best || []).forEach(pb => marks.push({
      index: pb.index, kind: "diamond", color: "s3", r: 4.5, ...partyBestLabel(G, pb), role: "party_best",
      title: "best efficient deal for " + seatName(G, pb.party) + " (" + pb.agent + ")" }));
    TRAJ.forEach(p => {
      const later = p.turn_idx > upto;
      /* A later proposal keeps the trajectory's own colour and loses weight: it is the same series seen at a
         different time, so making it a fourth hue would both spend a categorical slot and collide with the
         solution points under deuteranopia (measured: ΔE 2.0 against slot 3 on the dark surface). */
      marks.push({
        index: p.index, kind: "circle", color: "s1", cls: later ? "ghost" : "", r: later ? 3.5 : 6,
        label: later ? "" : String(p.ordinal), dx: 8, dy: -7, turn: p.turn_idx, role: "proposal",
        title: later ? "proposal still to come (move " + p.ordinal + ", turn " + p.turn_idx + ")"
                     : "move " + p.ordinal + ": " + p.seat + " " + p.atype + " at turn " + p.turn_idx });
    });
    if (standing !== null && standing !== undefined)
      marks.push({ index: standing, kind: "square", color: "s1", r: 8, label: "ON THE TABLE", dx: 10, dy: 4,
                   role: "standing", title: "the deal standing on the table at this turn" });
    return marks;
  }
  function drawMini() {
    const host = $("mini-chart");
    if (!host || !G) return;
    const pane = $("pane-frontier");
    if (pane && pane.hidden) { miniStale = true; return; }
    const upto = current === null ? Infinity : current;
    const standing = current === null ? null : (BY_IDX[String(current)] || {}).standing_deal_index;
    const shown = TRAJ.filter(p => p.turn_idx <= upto);
    frontierChart(host, G, miniMarks(upto, standing), [{ cls: "path1", indices: shown.map(p => p.index) }],
      (mk, clicked) => { if (clicked && mk.turn !== undefined && cfg.onSelect) cfg.onSelect(mk.turn); });
    const note = $("mini-note");
    if (note) note.textContent = current === null
      ? "the whole episode: " + TRAJ.length + " proposal(s)"
      : shown.length + " of " + TRAJ.length + " proposal(s) tabled by turn " + current
        + (standing === null || standing === undefined ? "; nothing standing on the table"
           : "; standing offer is deal #" + standing);
    miniStale = false;
  }

  /* ------------------------------------------------------------- issues --- */
  /* Mean and sd of one agent's utility over the WHOLE deal space, so the z below the bars says where the deal on
     the table sits among everything that was available to this agent. Computed once per agent. */
  function moments(party) {
    if (momentCache[party]) return momentCache[party];
    const col = (G.deals.u || []).map(r => r[party]);
    const mean = col.reduce((a, b) => a + b, 0) / (col.length || 1);
    const sd = Math.sqrt(col.reduce((a, b) => a + (b - mean) * (b - mean), 0) / (col.length || 1));
    return (momentCache[party] = { mean, sd });
  }
  function paintIssues(party, dealIdx) {
    const host = $("issue-seats");
    if (!host || !G) return;
    host.querySelectorAll(".issueseat").forEach(n => { n.hidden = Number(n.dataset.party) !== party; });
    const block = host.querySelector('.issueseat[data-party="' + party + '"]');
    if (!block) return;
    block.querySelectorAll(".dealmark, .dealdot").forEach(n => n.remove());
    const nums = block.querySelector(".issuenums");
    if (dealIdx === null || dealIdx === undefined) {
      if (nums) nums.innerHTML = `<span class="sub muted">No deal is on the table at this turn.</span>`;
      return;
    }
    block.querySelectorAll(".issuebar").forEach(g => {
      const j = Number(g.dataset.issue);
      const opt = Math.floor(dealIdx / G.strides[j]) % G.shape[j];
      const tick = g.querySelector('.opt[data-opt="' + opt + '"]');
      if (!tick) return;
      const y = Number(tick.dataset.y), x0 = Number(g.dataset.x0), x1 = Number(g.dataset.x1);
      /* The marker is a CLONE of the tick it lands on: same element, same SVG namespace, same scale — the
         browser never re-derives the geometry the server drew, and the page needs no namespace literal. */
      const line = tick.cloneNode(true);
      line.setAttribute("class", "dealmark");
      line.removeAttribute("data-opt");
      line.setAttribute("x1", String(x0 - 6)); line.setAttribute("x2", String(x1 + 6));
      const title = line.querySelector("title");
      if (title) title.textContent =
        G.issues[j].name + " = " + G.issues[j].options[opt] + " in the deal on the table";
      g.appendChild(line);
    });
    if (!nums) return;
    const u = G.deals.u[dealIdx][party], tau = G.thresholds[party], s = u - tau;
    const mom = moments(party), z = mom.sd > 1e-9 ? (u - mom.mean) / mom.sd : null;
    nums.innerHTML =
      `<span class="pill">deal total <b>${N(u, 1)}</b></span>` +
      `<span class="pill">threshold τ <b>${N(tau, 1)}</b></span>` +
      `<span class="pill">surplus <b class="${s >= 0 ? "pos" : "neg"}">${SIGN(s, 1)}</b></span>` +
      (z === null ? `<span class="pill muted">z undefined (this agent values every deal alike)</span>`
                  : `<span class="pill">z <b>${SIGN(z, 2)}</b> <span class="muted">vs all ${G.deals.n} deals</span></span>`) +
      `<span class="pill">${E(dealSummary(G, dealIdx))}</span>`;
  }

  /* ------------------------------------------------ the shared selection --- */
  function setCurrent(idx, source) {
    const turn = BY_IDX[String(idx)];
    if (!turn) return;
    current = idx;
    const party = pinnedParty === null ? turn.party : pinnedParty;
    paintChat(idx, turn.seat);
    if (G) { paintIssues(party, turn.standing_deal_index); miniStale = true; drawMini(); }
    const note = $("sync-note");
    if (note) note.innerHTML = `turn <b>${E(idx)}</b> · <b>${E(turn.seat)}</b> acting`
      + (pinnedParty === null ? " · following the transcript"
         : ` · issues pinned to <b>${E((cfg.seats[pinnedParty] || {}).name)}</b>`)
      + (source === "select" ? " · selected in the transcript" : "");
    const seatNote = $("issue-seat-note");
    if (seatNote) seatNote.textContent = pinnedParty === null ? "" : "pinned — scroll to release";
  }

  /* --------------------------------------------------------- scroll sync --- */
  /* An IntersectionObserver over the turn cards, not a scroll handler: the browser reports which cards are in
     the viewport and the topmost one is what the reader is reading. The bottom margin keeps a card that is only
     peeking in from below from stealing the sidebar. */
  let observer = null;
  const visible = new Set();
  function observeTurns() {
    if (typeof IntersectionObserver === "undefined") return;
    if (observer) observer.disconnect();
    visible.clear();
    observer = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        const idx = Number(e.target.dataset.turnidx);
        if (e.isIntersecting) visible.add(idx); else visible.delete(idx);
      });
      if (!visible.size) return;
      const top = Math.min.apply(null, Array.from(visible));
      if (top === lastObserved) return;          // a pin only survives until the reader actually moves
      lastObserved = top;
      pinnedParty = null;
      const pick = $("issue-seat-pick");
      if (pick) pick.value = "auto";
      setCurrent(top, "scroll");
    }, { rootMargin: "-12% 0px -55% 0px", threshold: 0 });
    document.querySelectorAll("#turnlist .turn").forEach(n => observer.observe(n));
  }

  /* ------------------------------------------------------------ controls --- */
  const pick = $("issue-seat-pick");
  if (pick) pick.addEventListener("change", () => {
    const party = Number(pick.value);
    pinnedParty = (pick.value === "auto" || !isFinite(party)) ? null : party;
    if (current === null && TURNS.length) setCurrent(TURNS[0].idx, "pin");
    else if (current !== null) setCurrent(current, "pin");
  });

  if (TURNS.length) setCurrent(TURNS[0].idx, "init");
  return { observeTurns, setCurrent, showTab, cycleTab, tabs: tabs.map(keyOf) };
}
"""
