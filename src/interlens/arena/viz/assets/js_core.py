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

"""Browser layer, part 1: the payload, the formatting helpers, and the deal-detail panel.

Loaded first on every page. Three jobs:

**Rehydration.** Prompt views travel as indices into a de-duplicated message pool rather than as inlined text —
a six-seat episode's thirty turns repeat the same system prompt thirty times and each view re-states the whole
history so far, so the pool is worth roughly a third of the page. :js:func:`viewOf` turns a turn's indices back
into ``[{role, content}]`` on demand; nothing else in the page knows the difference.

**Formatting.** One escape helper, one number formatter, one signed formatter, one "is this the good direction"
class picker — so a value is never formatted two different ways on two different panels.

**The action grammar.** :js:func:`actKind` maps an action type to the class, glyph, and word the transcript, the
scrubber, and the chart all wear for it. One mapping, so propose is the same blue everywhere it appears.
"""
from __future__ import annotations

# The formatting and DOM helpers, with no dependency on a payload — the run index carries no ``viz-payload`` tag,
# so it loads this and the shell but not the episode data layer below.
JS_UTIL = r"""
const E = (s) => String(s ?? "").replace(/[&<>"']/g, c => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const N = (v, d = 2) => (typeof v === "number" && isFinite(v)) ? v.toFixed(d) : "—";
const SIGN = (v, d = 2) => (typeof v === "number" && isFinite(v)) ? (v >= 0 ? "+" : "") + v.toFixed(d) : "—";
const CLS = (v, better = 1) => (typeof v !== "number" || v === 0) ? "zero" : ((v > 0) === (better >= 0) ? "pos" : "neg");
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const $ = (id) => document.getElementById(id);
"""

JS_CORE = r"""
const PAYLOAD = JSON.parse(document.getElementById("viz-payload").textContent);

/* Prompt views travel as indices into PAYLOAD.msgpool (see the module docstring): rebuild one turn's view. A
   turn whose view was recorded inline (or is absent) passes through unchanged, so nothing depends on the pool
   existing. */
function viewOf(t) {
  const pool = PAYLOAD.msgpool;
  if (!t.view) return null;
  if (!pool || !t.view.length || typeof t.view[0] !== "number") return t.view;
  return t.view.map(i => ({ role: pool[i][0], content: pool[i][1] }));
}

/* The action grammar, in one place. Action types are STATES, so they wear the reserved status palette (accept =
   good, reject = serious, walk = critical) rather than a categorical series slot — and each ships a glyph and a
   word, so the colour never carries the meaning by itself. */
const ACT_KINDS = {
  propose: { cls: "a-propose", glyph: "▲", word: "propose" },
  accept:  { cls: "a-accept",  glyph: "✓", word: "accept" },
  reject:  { cls: "a-reject",  glyph: "✗", word: "reject" },
  walk:    { cls: "a-walk",    glyph: "⏻", word: "walk away" },
  vote:    { cls: "a-vote",    glyph: "◆", word: "vote" },
  talk:    { cls: "a-talk",    glyph: "“", word: "talk" },
  chat:    { cls: "a-talk",    glyph: "“", word: "talk" },
  message: { cls: "a-talk",    glyph: "“", word: "talk" },
  none:    { cls: "a-none",    glyph: "·", word: "no action" },
};
function actKind(atype) {
  const key = String(atype || "none").toLowerCase();
  return ACT_KINDS[key] || { cls: "a-none", glyph: "·", word: key };
}

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

/* Tiny direct labels for party-best diamonds. The six anchors deliberately occupy different sides of a point:
   several parties can share the same best deal, and identical x/y text would make the labels less informative
   precisely where they are most needed. More than six parties cycles deterministically. */
function partyBestLabel(game, pb) {
  const anchors = [
    { dx: 8, dy: -7, anchor: "start" }, { dx: 8, dy: 11, anchor: "start" },
    { dx: -8, dy: -7, anchor: "end" }, { dx: -8, dy: 11, anchor: "end" },
    { dx: 0, dy: -10, anchor: "middle" }, { dx: 0, dy: 15, anchor: "middle" }
  ];
  const pos = anchors[Number(pb.party) % anchors.length] || anchors[0];
  return { label: seatName(game, pb.party), labelClass: "partybest", labelAnchor: pos.anchor,
           dx: pos.dx, dy: pos.dy };
}

/* The deal panel, with progressive disclosure: a HOVER opens the headline read (what the deal is, and the three
   facts that decide whether it is any good), and PINNING it with a click adds the full per-party breakdown.
   Hovering the cloud used to repaint a six-row table on every pointer move, which flickered and buried the one
   line a reader was actually tracking. */
function dealDetail(game, index, title, extra, pinned) {
  if (index === null || index === undefined)
    return `<div class="sub">Hover any deal on the chart for its headline numbers; click to pin the full per-party breakdown.</div>`;
  const d = game.deals, s = d.s[index], u = d.u[index], xn = d.xn[index];
  const usw = s.reduce((a, b) => a + b, 0), esw = Math.min(...s);
  const below = s.filter(v => v < 0).length;
  const head = `<div class="hd">${E(title)} <span class="muted">deal #${index}</span>
     ${extra ? `<span class="pill">${extra}</span>` : ""}
     <span class="muted" style="margin-left:auto;font-weight:400;font-size:var(--t-xs)">${
       pinned ? "pinned — click another deal to move the pin" : "click to pin the per-party breakdown"}</span></div>
   <div class="sub">${E(dealSummary(game, index))}</div>
   <div class="pills">
     <span class="pill">joint welfare <b>${N(usw, 1)}</b></span>
     <span class="pill">worst-off <b class="${esw >= 0 ? "pos" : "neg"}">${SIGN(esw, 1)}</b></span>
     <span class="pill">${d.pareto[index] ? "on the Pareto frontier" : "below the frontier by <b>" + N(d.d_frontier[index], 3) + "</b>"}</span>
     <span class="pill">${d.feasible[index] ? "can close under the protocol" : "<b>cannot close</b> (agreement rule)"}</span>
     ${below ? `<span class="pill"><b class="neg">${below}</b> part${below === 1 ? "y" : "ies"} below threshold</span>` : ""}
   </div>`;
  if (!pinned) return head;
  const rows = game.parties.map((p, i) => {
    const ok = s[i] >= 0, w = Math.max(0, Math.min(1, xn[i]));
    return `<tr><td>${E(seatName(game, i))} <span class="muted">${E(p)}</span></td>
      <td>${N(u[i], 1)}</td><td class="muted">${N(game.thresholds[i], 1)}</td>
      <td class="${ok ? "pos" : "neg"}">${SIGN(s[i], 1)}</td>
      <td style="width:82px"><span class="meter"><i class="${ok ? "ok" : "bad"}" style="width:${(w * 100).toFixed(1)}%"></i></span></td>
      <td>${N(xn[i] * 100, 0)}%</td></tr>`;
  }).join("");
  return head + `<table><thead><tr><th>party</th><th>utility</th><th>threshold</th><th>surplus</th>
     <th>vs ideal</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
}

/* A one-line provenance note naming the annotation vintage the post-hoc oracle values were read from
   (`annotations` = the original scoring pass, `annotations_v1` = a re-annotated set such as the oracle
   seat-binding fix), so an auditor always sees WHICH counterfactual they are reading. Empty when no counterfactual
   oracle is present or the values came from the episode's own inline records rather than an annotation store. */
function annProvenance(source, oracles) {
  if (!source || !(oracles && oracles.length)) return "";
  return `<div class="sub muted annprov">Post-hoc oracle counterfactual (${oracles.map(E).join(", ")}) read from the <code>${E(source)}</code> annotation set.</div>`;
}
"""
