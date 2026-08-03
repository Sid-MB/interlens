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

"""Browser layer, part 3: the transcript — turn cards, the scrubber, and lazy prompt bodies.

A turn card wears its action type: a coloured left edge, a chip with a glyph and the word, and a dashed edge when
the seat was a computable policy rather than a model. The header is sticky, so scrolling a long reasoning trace
never loses track of whose turn it is, and clicking it selects the turn (which lights up the deal that turn put on
the chart).

**Prompt bodies are built on first open, not on first paint.** A six-seat thirty-turn episode carries a few
hundred kilobytes of prompt text; turning all of it into DOM nodes before the reader has asked for any of it is
the difference between a page that appears instantly and one that hitches. The ``<details>`` ships with its
summary and an empty body, and one delegated ``toggle`` listener fills it the first time it is opened.

**The scrubber** is the transcript's map: one chip per turn, coloured by action type, fabricated turns ringed in
the critical colour, the current turn filled. It is how a reader gets from "something went wrong around the end"
to the turn in one click instead of a scroll hunt.
"""
from __future__ import annotations

JS_TRANSCRIPT = r"""
const VIEW_LABEL = {
  stored: "exactly as recorded at generation time",
  reconstructed: "RE-DERIVED by replay through the current prompt code — not a byte record of what the model saw",
  reconstructed_pre_retry: "RE-DERIVED, and INCOMPLETE: this turn was a retry after a malformed response, and the repair instruction the model actually saw is not recoverable from the record — what follows is the FIRST attempt's prompt",
  absent: "not recorded" };

/* The prompt panel's SUMMARY only. The body is filled by fillLazy() the first time it is opened — see the module
   docstring: the prompt text is most of the page's weight and none of it is wanted until it is asked for. */
function viewPanel(t) {
  const label = VIEW_LABEL[t.view_source] || t.view_source;
  if (!t.view) return `<details><summary>Prompt the seat saw — ${E(label)}</summary><div class="body">
    <div class="gap">This episode predates per-turn view capture and could not be reconstructed, so the exact prompt is unavailable. The game setup, protocol, and this seat's private sheet are in the side panel; do not treat them as the literal prompt text.</div></div></details>`;
  return `<details data-lazy="view" data-turnidx="${t.idx}">
    <summary>Prompt the seat saw — ${t.view.length} message(s), ${E(t.view_source)}</summary>
    <div class="body"><div class="sub">${E(label)}</div><div class="lazybody"></div></div></details>`;
}

/* Fill a lazy panel's body once, from the payload. Delegated from the transcript container, so cards that are
   re-rendered (an oracle change, the compare page's counterfactual toggle) need no re-binding. */
function fillLazy(details, turnsById) {
  if (details.dataset.filled) return;
  details.dataset.filled = "1";
  const t = turnsById[details.dataset.turnidx];
  const body = details.querySelector(".lazybody");
  if (!t || !body) return;
  if (details.dataset.lazy === "view")
    body.innerHTML = (viewOf(t) || []).map(msg =>
      `<div class="msgrole">${E(msg.role)}</div><pre>${E(msg.content)}</pre>`).join("");
  else if (details.dataset.lazy === "content") body.innerHTML = `<pre>${E(t.content)}</pre>`;
  else if (details.dataset.lazy === "reasoning") body.innerHTML = `<pre>${E(t.reasoning)}</pre>`;
}
function bindLazy(container, turns) {
  const byId = Object.fromEntries(turns.map(t => [String(t.idx), t]));
  container.addEventListener("toggle", (ev) => {
    const d = ev.target;
    if (d.tagName === "DETAILS" && d.open && d.dataset.lazy) fillLazy(d, byId);
  }, true);
  return byId;
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
  const k = actKind(a.atype);
  /* A fabricated turn is marked on the card itself, not only in the page banner: someone scrolling the
     transcript must not read engine filler as something the model chose to say. */
  const fabricatedNote = t.gen_failed
    ? `<div class="gap fabnote"><b>This turn was not generated.</b> The engine substituted its placeholder text
       after generation failed${t.gen_failure ? ` (${E(t.gen_failure)})` : ""}. It parses as a well-formed no-op,
       so it looks like a deliberate pass — it is not. Detected by ${E(t.gen_failed_detected_by || "stamp")}.</div>`
    : "";
  const dealLink = a.deal_index !== null && a.deal_index !== undefined
    ? `<div class="deal"><a href="#" data-deal="${a.deal_index}">${E(dealSummary(game, a.deal_index))}</a></div>`
    : (a.deal_named ? `<div class="deal neg">proposal did not resolve to a legal deal: ${E(JSON.stringify(a.deal_named))}</div>` : "");
  const w = t.deal_welfare;
  const oracles = Object.keys(t.oracles || {});
  const prefix = opts.idPrefix || "turn-";
  return `<article class="turn ${k.cls} k-${E(t.kind)}${t.gen_failed ? " fabricated" : ""}" id="${prefix}${t.idx}" data-turnidx="${t.idx}">
   <div class="turnhd" role="button" tabindex="0" aria-label="turn ${t.idx}, ${E(t.seat)}, ${E(k.word)}">
     <span class="who"><span class="idx">${t.idx}</span> ${E(t.seat)}
       <span class="badge ${E(t.kind)}">${E(t.kind)}</span>
       <span class="kind ${k.cls}">${k.glyph} ${E(k.word)}</span>${
       t.gen_failed ? ` <span class="badge fabricated" title="${E(t.gen_failure || "")}">NOT GENERATED</span>` : ""}</span>
     <span class="sub">${E(t.phase)} · round ${t.round}${t.n_tokens_out ? " · " + t.n_tokens_out + " tok out" : ""}${t.parse_ok ? "" : " · <b class='neg'>parse error</b>"}</span>
   </div>
   ${opts.showCounterfactual ? `<div class="cols">
     <div class="col acted"><div class="hd">the model acted</div><div class="act">${E(a.label || a.atype)}</div>${dealLink}
       ${w ? `<div class="pills"><span class="pill">USW <b>${N(w.usw, 1)}</b></span><span class="pill">worst-off <b class="${w.esw >= 0 ? "pos" : "neg"}">${SIGN(w.esw, 1)}</b></span>${w.n_below_threshold ? `<span class="pill"><b class="neg">${w.n_below_threshold}</b> below τ</span>` : ""}</div>` : ""}</div>
     ${oracleColumn(t, game, oracle)}</div>`
    : `<div class="act">${E(a.label || a.atype)}</div>${dealLink}`}
   ${fabricatedNote}
   ${a.message ? `<div class="msg">${E(a.message)}</div>` : ""}
   ${a.syntax_error ? `<div class="gap neg">syntax error: ${E(a.syntax_error)}</div>` : ""}
   ${t.reasoning ? `<details data-lazy="reasoning" data-turnidx="${t.idx}">
      <summary>Reasoning / scratchpad — provenance ${E(t.reasoning_provenance)}</summary>
      <div class="body"><div class="lazybody"></div></div></details>`
     : `<div class="sub muted">No reasoning recorded (provenance ${E(t.reasoning_provenance)}). Do not impute it.</div>`}
   ${viewPanel(t)}
   ${t.content ? `<details data-lazy="content" data-turnidx="${t.idx}"><summary>Raw turn text as the table saw it</summary>
      <div class="body"><div class="lazybody"></div></div></details>` : ""}
   ${oracles.length ? `<details><summary>All oracle verdicts (${oracles.length}) and every action they scored</summary><div class="body">
      ${oracles.map(name => {
        const o = t.oracles[name];
        return `<h3>${E(name)}</h3><div class="tablewrap"><table><thead><tr><th>action the oracle scored</th><th>value</th></tr></thead><tbody>
         ${o.action_values.map(av => `<tr><td>${E(av.label)}${av.deal ? ` <span class="muted">${E(JSON.stringify(av.deal))}</span>` : ""}</td><td>${N(av.value)}</td></tr>`).join("")}
         </tbody></table></div>
         <div class="pills"><span class="pill">chose <b>${N(o.chosen_value)}</b></span><span class="pill">best <b>${N(o.best_value)}</b></span>
         <span class="pill">regret <b>${N(o.divergence)}</b></span>${Object.entries(o.extra || {}).map(([k2, v]) =>
           `<span class="pill">${E(k2)} <b>${E(typeof v === "number" ? N(v, 3) : JSON.stringify(v))}</b></span>`).join("")}</div>`;
      }).join("")}</div></details>` : ""}
  </article>`;
}

/* The transcript's map: one chip per turn, coloured by action type, fabricated turns ringed. Chips address turn
   cards by ELEMENT ID rather than by index, because a comparison page carries two transcripts whose turn indices
   collide — each side renders with its own id prefix and gets its own scrubber. */
function scrubberHtml(turns, idPrefix) {
  if (!turns.length) return "";
  const prefix = idPrefix || "turn-";
  return `<div class="scrub" role="navigation" aria-label="jump to a turn">` + turns.map(t => {
    const k = actKind((t.action || {}).atype);
    return `<button class="chip ${k.cls}${t.gen_failed ? " fab" : ""}" data-goturn="${prefix}${t.idx}" data-turnidx="${t.idx}"
      title="turn ${t.idx} · ${E(t.seat)} · ${E(k.word)}${t.gen_failed ? " · NOT GENERATED" : ""}">${t.idx}</button>`;
  }).join("") + `</div>`;
}

/* Selection is one function so every entry point agrees: a scrubber chip, a regret bar, a chart mark, the j/k
   keys, and a click on the turn header all mark the same card and move the same scrubber chip. */
function makeSelectTurn(onSelect, idPrefix) {
  const prefix = idPrefix || "turn-";
  return function selectTurn(idx, opts) {
    const node = $(prefix + idx);
    if (!node) return null;
    document.querySelectorAll(".turn.sel").forEach(n => n.classList.remove("sel"));
    document.querySelectorAll(".chip.cur").forEach(n => n.classList.remove("cur"));
    node.classList.add("sel");
    const chip = document.querySelector(`.chip[data-goturn="${prefix}${idx}"]`);
    if (chip) chip.classList.add("cur");
    if (!opts || opts.scroll !== false)
      node.scrollIntoView({ behavior: "smooth", block: (opts && opts.block) || "center" });
    if (onSelect) onSelect(idx);
    return node;
  };
}

/* Collapse/expand every disclosure inside a container. Expanding fills the lazy bodies it opens, which is the
   one moment the page deliberately pays the whole prompt-text cost — because the reader just asked for it. */
function setAllOpen(container, open) {
  container.querySelectorAll("details").forEach(d => { d.open = open; });
}
"""
