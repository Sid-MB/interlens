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
# [implement: live-play/laneD] 2026-08-16

"""Browser layer, part 3: the transcript — turn cards, the scrubber, and lazy prompt bodies.

A turn card wears its action type: a coloured left edge, a chip with a glyph and the word, and a dashed edge when
the seat was a computable policy rather than a model. The header is sticky, so scrolling a long reasoning trace
never loses track of whose turn it is, and clicking it selects the turn (which lights up the deal that turn put on
the chart).

**A hazard note comes before the turn's analysis, not after it.** "This turn is not what it looks like" — the
engine fabricated it, or generation produced no publishable answer — has to reach a reader before the columns
that discuss what the seat chose, because those columns are discussing a non-event.

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
  else if (details.dataset.lazy === "raw")
    /* One line, deliberately: a newline inside a template literal is OUTPUT, so a wrapped sentence reaches the
       reader with the source's indentation in the middle of it. */
    body.innerHTML = (t.raw_truncated
      ? `<div class="sub">Excerpt: the first ${t.raw.length} of ${t.raw_chars} characters. The full text is in the episode record linked at the top of this page.</div>`
      : "") + `<pre>${E(t.raw)}</pre>`;
}
function bindLazy(container, turns) {
  const byId = Object.fromEntries(turns.map(t => [String(t.idx), t]));
  container.addEventListener("toggle", (ev) => {
    const d = ev.target;
    if (d.tagName === "DETAILS" && d.open && d.dataset.lazy) fillLazy(d, byId);
  }, true);
  return byId;
}

/* WHAT KIND of record the scratchpad text is, which the stored provenance token alone does not say: `full` and
   `withheld_or_summarized` are internal spellings, and a reader deciding how much weight to give a scratchpad
   needs to know whether they are reading the model's own reasoning stream, a provider's summary of it, or prose
   the scaffold ASKED the seat to write in its response body. The raw token is kept beside the phrase so the
   record is never hidden behind an interpretation of it, and an unrecognized token renders alone rather than
   being described wrongly. */
const REASONING_KIND = {
  full: "verbatim chain of thought",
  withheld_or_summarized: "provider summary — the raw chain of thought was not returned",
};
function reasoningLabel(t) {
  const token = t.reasoning_provenance || "none";
  // `elicited` wins over the token: the text came out of the response BODY, so a provider-stream provenance of
  // "none" is not a contradiction to report, it is simply about a different channel.
  if (t.reasoning_source === "elicited") return "elicited rationale";
  const kind = REASONING_KIND[token];
  return kind ? `${kind} · ${token}` : token;
}

function oracleColumn(t, game, oracle, showInfoLinks) {
  const o = (t.oracles || {})[oracle];
  const privateInfo = String((((game || {}).protocol || {}).info || "")).toLowerCase().startsWith("priv");
  const role = (o || {}).counterfactual_role || "";
  /* A fairness reference names itself from the payload's registry rather than from a branch here: its heading has
     to carry the OBJECTIVE, because "omniscient oracle" over a table-welfare number is the exact confusion the
     unit labelling exists to prevent. The two self-interest headings keep their established wording. */
  const heading = (o || {}).objective === "table_fairness" ? `${E(o.reference_label)} (${E(oracle)})`
    : role === "rational_private" ? `private-information rational agent (${E(oracle)})`
    : role === "oracle_omniscient" && oracle !== "bestresponse" ? `omniscient oracle (${E(oracle)})`
    : privateInfo ? `omniscient hindsight oracle (${E(oracle)})` : `full-information oracle (${E(oracle)})`;
  const gapLabel = role === "rational_private" ? "private-policy value improvement"
    : (privateInfo || (role === "oracle_omniscient" && oracle !== "bestresponse"))
      ? "hindsight value gap" : "value improvement available";
  if (!o) return `<div class="col oracle"><div class="hd">${heading}</div>
    <div class="gap">This run carries no <code>${E(oracle)}</code> verdict for this turn, so there is no counterfactual to compare against.</div></div>`;
  const reg = o.divergence;
  const context = counterfactualContext(t, o);
  const previewIndex = counterfactualDealIndex(t, o);
  return `<div class="col oracle"><div class="hd">${heading} would</div>
    <div class="act">${E(o.best_label)}</div>
    ${context ? `<div class="cfcontext">${E(context)}</div>` : ""}
    ${previewIndex !== null && previewIndex !== undefined
      ? `<div class="deal"><a href="#" class="cflink" data-counterfactual data-turnidx="${t.idx}"
          data-deal="${previewIndex}" aria-haspopup="dialog" aria-expanded="false"
          aria-label="Preview the decision reference package on the frontier">${E(dealSummary(game, previewIndex))}</a></div>` : ""}
    <table><tbody>
      <tr><td>${E(o.value_label || "oracle's value of its best move")}
        ${o.unit ? `<span class="unit">${E(o.unit)}</span>` : ""}
        ${infoLink("How the oracle scores moves", showInfoLinks)}</td><td>${N(o.best_value)}</td></tr>
      ${o.objective === "table_fairness"
        ? `<tr><td><b>${E(o.gap_label)}</b><span class="unit">${E(o.unit)}</span></td>
           <td class="${CLS(-(o.shortfall || 0))}"><b>${N(o.shortfall)}</b></td></tr>
           <tr><td>this seat's own points at that deal <span class="unit">a SEPARATE quantity from the table
             objective above — not a gain and not comparable with it</span></td>
           <td>${N(o.own_surplus, 1)}</td></tr>`
        : `<tr class="${typeof reg === "number" && reg > 0 ? "hi" : ""}"><td><b>${gapLabel}</b>
        ${infoLink("How the oracle calculates the improvement gap", showInfoLinks)}</td>
        <td class="${CLS(reg === 0 ? 0 : -reg)}"><b>${N(reg)}</b></td></tr>`}
    </tbody></table>
    ${o.flags && o.flags.length ? `<div class="pills">${o.flags.map(f => `<span class="pill"><b class="neg">${E(f)}</b></span>`).join("")}</div>` : ""}</div>`;
}

/* ---- the four-type decision-reference grid -------------------------------------------------------------- */
/* Every reference the turn carries, laid out on the 2x2 the payload describes: information across (what it
   could see) and objective down (what it was maximizing). Grouping is read from `o.information_axis` /
   `o.objective` rather than from the reference's NAME, so a new reference appears in the right cell without a
   change here.

   The grid exists because the selector shows one reference at a time and the interesting fact is usually the
   relationship between them — and because putting four numbers side by side is exactly where the unit hazard
   bites. So no cell prints a bare number: each carries the unit string the payload gives it, a fairness cell
   states its table optimum and its own-surplus consequence separately, and the footer says which of these
   numbers may be subtracted from which. Two readers have already subtracted the wrong pair.

   It sits BELOW the acted/oracle pair at the card's full width rather than inside the oracle cell, which is
   where it was first built: a three-column grid whose cells carry a package summary each is illegible at half
   the card's width, and it wrapped every deal to one word per line. */
const REFERENCE_INFORMATION = ["private", "omniscient"];
const REFERENCE_OBJECTIVES = ["own_surplus", "table_fairness"];

function referenceCells(t) {
  /* {objective: {information: {name, oracle}}} over the references this turn actually carries. */
  const grid = {};
  Object.entries(t.oracles || {}).forEach(([name, o]) => {
    if (!o || !o.objective || !o.information_axis) return;      // a generic scored oracle, not a reference
    (grid[o.objective] ||= {})[o.information_axis] = { name, o };
  });
  return grid;
}

function referenceValue(o) {
  if (o.objective === "table_fairness") {
    const optimum = o.table_optimum;
    return `<div class="rv"><b>${N(o.best_value, 3)}</b><span class="ru">${E(o.unit)}</span></div>
      <div class="rsub">best any deal could score: <b>${N(optimum, 3)}</b>${
        typeof o.shortfall === "number" ? ` · shortfall <b>${N(o.shortfall, 3)}</b> in the same table units` : ""}</div>
      <div class="rsub">${typeof o.own_surplus === "number"
        ? `this seat's own points at that deal: <b>${N(o.own_surplus, 1)}</b> — a separate quantity, not the score above`
        : "no own-surplus recorded for this action"}</div>`;
  }
  return `<div class="rv"><b>${N(o.best_value, 3)}</b><span class="ru">${E(o.unit)}</span></div>
    ${o.value_basis ? `<div class="rsub">${E(o.value_basis)}</div>` : ""}
    ${typeof o.divergence === "number" ? `<div class="rsub">${E(o.gap_label)}: <b>${N(o.divergence, 3)}</b></div>` : ""}`;
}

function referenceCell(t, game, entry) {
  if (!entry) return `<td class="refcell empty">no reference of this kind was recorded for this turn</td>`;
  const o = entry.o;
  const index = counterfactualDealIndex(t, o);
  const deal = (index !== null && index !== undefined)
    ? `<div class="deal"><a href="#" data-deal="${index}"
        aria-label="show this reference's package on the frontier">${E(dealSummary(game, index))}</a></div>` : "";
  return `<td class="refcell obj-${E(o.objective)}">
    <div class="rname">${E(o.reference_label)} <code>${E(entry.name)}</code></div>
    <div class="act">${E(o.best_label)}</div>${deal}${referenceValue(o)}</td>`;
}

function referenceGrid(t, game) {
  const grid = referenceCells(t);
  const objectives = REFERENCE_OBJECTIVES.filter(k => grid[k]);
  if (!objectives.length) return "";
  const axes = (PAYLOAD.reference_axes || {});
  const head = REFERENCE_INFORMATION.map(k => {
    const meta = ((axes.information || {})[k]) || {};
    return `<th>${E(meta.name || k)}<span class="rsub">${E(meta.detail || "")}</span></th>`;
  }).join("");
  const rows = objectives.map(objective => {
    const meta = ((axes.objective || {})[objective]) || {};
    return `<tr><th class="objhd">${E(meta.name || objective)}<span class="rsub">${E(meta.unit || "")}</span></th>
      ${REFERENCE_INFORMATION.map(info => referenceCell(t, game, grid[objective][info])).join("")}</tr>`;
  }).join("");
  /* The non-comparability statement is assembled from the same per-objective data, so it can only ever say what
     the records support: a fairness row's two numbers ARE on one scale, a self-interest row's two are not, and
     nothing may be compared across rows. */
  const notes = objectives.map(objective => {
    const meta = ((axes.objective || {})[objective]) || {};
    return `<li><b>${E(meta.name || objective)}</b> — ${E(meta.note || "")}</li>`;
  }).join("");
  const missing = objectives.length < REFERENCE_OBJECTIVES.length
    ? `<div class="rsub">This annotation vintage records only the ${E(objectives.length)} reference row(s) shown;
       the table-fairness references were added by a later schema and are absent here.</div>` : "";
  return `<details class="refgrid" open><summary>All ${Object.values(grid).reduce((n, r) => n + Object.keys(r).length, 0)}
    decision references for this turn, on both axes</summary><div class="body">
    <div class="sub">Across: what the reference could SEE. Down: what it was MAXIMIZING. The two rows are in
    different units and must never be compared with each other.</div>
    <div class="tablewrap"><table class="refs"><thead><tr><th></th>${head}</tr></thead>
    <tbody>${rows}</tbody></table></div>
    <ul class="unitwarn">${notes}</ul>${missing}</div></details>`;
}

function decisionWord(label) {
  const m = String(label || "").trim().toLowerCase().match(/^(accept|reject|propose|walk|vote|talk|none)\b/);
  return m ? m[1] : "";
}

/* The KIND of the recommended action. Reads the payload's `best_atype`, which is parsed server-side from the
   stored action (`episode._oracle_payload`), and falls back to the display label only for records written before
   that field existed — a semantic branch must not depend on how a label happened to be formatted. */
function oracleDecision(oracle) {
  return String((oracle || {}).best_atype || "").toLowerCase() || decisionWord((oracle || {}).best_label);
}

/* ACCEPT names the offer already standing on the table and therefore commonly carries no `best_deal_index`.
   Every other constructive counterfactual previews the oracle's alternative package. */
function counterfactualDealIndex(t, oracle) {
  const standing = t.standing_deal_index;
  if (oracleDecision(oracle) === "accept" && standing !== null && standing !== undefined) return standing;
  return oracle.best_deal_index;
}

/* The COUNTERFACTUAL PACKAGE: one the reference would put on the table, as opposed to the offer already standing
   there. An accept has none by construction — its deal IS the standing offer — which is why an accept
   recommendation gets no explanatory context line below it. */
function counterfactualPackageIndex(oracle) {
  if (oracleDecision(oracle) === "accept") return null;
  const index = oracle.best_deal_index;
  return (index === null || index === undefined) ? null : index;
}

/* The rationale describes the relationship between a DECLINED offer and the package shown directly under it. The
   package is the reference's constructive alternative, not the offer being declined — so this renders only when
   such a package exists, and never for an accept, where inventing a "because" would attribute to the oracle a
   comparison it did not make. */
function counterfactualContext(t, oracle) {
  const decision = oracleDecision(oracle);
  if (!decision || decision === "accept") return "";
  if (counterfactualPackageIndex(oracle) === null) return "";
  if (decision === "reject")
    return `because the following package, better for ${t.seat}, is plausibly acceptable to the table in the remaining rounds`;
  return `because the following package is the strongest plausible remaining-round move for ${t.seat}`;
}

/* Build ONLY the semantic overlay; frontierChart remains the sole owner of axes, frontier geometry and marks. */
function counterfactualOverlay(t, oracle) {
  const model = decisionWord((t.action || {}).atype || (t.action || {}).label);
  const rational = oracleDecision(oracle);
  const standing = t.standing_deal_index;
  const modelProposal = (t.action || {}).deal_index;
  const alternative = oracle.best_deal_index;
  const valid = i => i !== null && i !== undefined;
  const marks = [], paths = [];
  let state = "other", note = "The highlighted package is the oracle's counterfactual move.";
  if (model === rational && (model === "accept" || model === "reject") && valid(standing)) {
    state = `agree-${model}`;
    marks.push({ index: standing, kind: "circle", color: model === "accept" ? "good" : "critical", r: 9,
      label: model === "accept" ? "ACCEPTED" : "REJECTED", title: `model and oracle both ${model}` });
    note = `The model and oracle agree to ${model} the package currently under consideration.`;
  } else if (model === "accept" && rational === "reject" && valid(standing)) {
    state = "model-accept-rational-reject";
    marks.push({ index: standing, kind: "circle", color: "good", r: 8, label: "MODEL ACCEPTED",
      title: "package accepted by the model" });
    if (valid(alternative)) {
      marks.push({ index: alternative, kind: "diamond", color: "critical", r: 8, label: "ORACLE PROPOSAL",
        title: "package the oracle would propose after rejecting" });
      paths.push({ cls: "cfpath", indices: [standing, alternative], arrowEnd: true });
    }
    note = "The model accepted the current package; the oracle would reject it and move toward the proposed alternative.";
  } else if (model === "reject" && rational === "accept" && valid(standing)) {
    state = "model-reject-rational-accept";
    marks.push({ index: standing, kind: "circle", color: "good", r: 9, label: "ORACLE: ACCEPT",
      title: "package rejected by the model but accepted by the oracle" });
    note = "The model rejected this package; the oracle would accept the same package.";
  } else if (model === "propose" && rational === "propose" && valid(modelProposal) && valid(alternative)) {
    if (Number(modelProposal) === Number(alternative)) {
      state = "agree-propose";
      marks.push({ index: modelProposal, kind: "circle", color: "s1", r: 9, label: "SAME PROPOSAL",
        title: "model and oracle proposed the same package" });
      note = "The model and oracle proposed the same package.";
    } else {
      state = "model-propose-rational-propose";
      marks.push({ index: modelProposal, kind: "circle", color: "s1", r: 8, label: "MODEL PROPOSAL",
        title: "package proposed by the model" });
      marks.push({ index: alternative, kind: "diamond", color: "s2", r: 8, label: "ORACLE PROPOSAL",
        title: "package the oracle would propose instead" });
      paths.push({ cls: "cfpath proposal", indices: [modelProposal, alternative], arrowEnd: true,
        arrowColor: "s2" });
      note = "The model and oracle would propose different packages; the arrow points toward the oracle alternative.";
    }
  } else if (valid(alternative)) {
    marks.push({ index: alternative, kind: "diamond", color: "critical", r: 8, label: "ORACLE MOVE",
      title: "oracle's counterfactual package" });
  }
  return { state, marks, paths, note };
}

/* The current campaign records TWO mathematically computed references at every turn. Keep their information sets
   as data, not name heuristics: the private rational policy is implementable by the acting seat; the omniscient
   oracle is a privileged hindsight ceiling. ``bestresponse`` remains the fallback ceiling for old campaigns. */
function decisionReferences(t) {
  const entries = Object.entries(t.oracles || {}).map(([name, value]) => ({ name, value }));
  const byRole = (role) => entries.find(e => (e.value || {}).counterfactual_role === role);
  return {
    rational: byRole("rational_private") || entries.find(e => e.name === "rational_private") || null,
    omniscient: byRole("oracle_omniscient") || entries.find(e => e.name === "oracle_omniscient")
      || entries.find(e => e.name === "bestresponse") || null,
  };
}

/* A three-way decision overlay: the package actually proposed or considered, the policy recommendation available
   from the seat's private information, and the omniscient optimum. Shapes and direct labels duplicate colour so
   the comparison survives colour-vision deficiencies. Coincident decisions deliberately remain three marks: an
   overlap is evidence of agreement, not a reason to drop either reference from the hover graph. */
function threeWayCounterfactualOverlay(t) {
  const refs = decisionReferences(t);
  if (!refs.rational || !refs.omniscient) return null;
  const actual = (t.action || {}).deal_index !== null && (t.action || {}).deal_index !== undefined
    ? (t.action || {}).deal_index : t.standing_deal_index;
  const rational = counterfactualDealIndex(t, refs.rational.value);
  const omniscient = counterfactualDealIndex(t, refs.omniscient.value);
  const valid = i => i !== null && i !== undefined;
  const marks = [], paths = [];
  if (valid(actual)) marks.push({ index: actual, kind: "circle", color: "s1", r: 9,
    label: "ACTUAL", title: "package proposed or considered by the LLM" });
  if (valid(rational)) marks.push({ index: rational, kind: "diamond", color: "s2", r: 8,
    label: "PRIVATE RATIONAL", title: "rational action using only the acting seat's private information" });
  if (valid(omniscient)) marks.push({ index: omniscient, kind: "square", color: "s3", r: 8,
    label: "OMNISCIENT", title: "oracle action using every party's hidden information" });
  if (valid(actual) && valid(rational) && Number(actual) !== Number(rational))
    paths.push({ cls: "cfpath proposal", indices: [actual, rational], arrowEnd: true, arrowColor: "s2" });
  if (valid(actual) && valid(omniscient) && Number(actual) !== Number(omniscient))
    paths.push({ cls: "cfpath", indices: [actual, omniscient], arrowEnd: true, arrowColor: "s3" });
  return { state: "actual-rational-oracle", marks, paths,
    note: "Actual package (circle), private-information rational reference (diamond), and omniscient oracle reference (square)." };
}

function modelPackageOverlay(t, index) {
  return {
    state: "model-package",
    marks: [{ index, kind: "circle", color: "s1", r: 9, label: "MODEL PROPOSAL",
      title: "package proposed by the model" }],
    paths: [],
    note: `The package ${t.seat} proposed on turn ${t.idx}, shown in the same deal space as the main frontier.`,
  };
}

let COUNTERFACTUAL_CARD = null;
function counterfactualCard() {
  if (COUNTERFACTUAL_CARD) return COUNTERFACTUAL_CARD;
  const node = document.createElement("div");
  node.className = "cfcard";
  node.setAttribute("role", "dialog");
  node.setAttribute("aria-label", "Oracle counterfactual on the frontier");
  node.setAttribute("tabindex", "-1");
  document.body.appendChild(node);
  let pinned = false, owner = null, closeTimer = null;
  const cancelClose = () => { if (closeTimer) clearTimeout(closeTimer); closeTimer = null; };
  function place(link) {
    const box = link.getBoundingClientRect(), pad = 12;
    const w = node.offsetWidth || 680, h = node.offsetHeight || 500;
    let left = Math.min(box.left, (window.innerWidth || 1200) - w - pad);
    let top = box.bottom + 10;
    if (top + h > (window.innerHeight || 800) - pad) top = Math.max(pad, box.top - h - 10);
    node.style.left = Math.max(pad, left) + "px"; node.style.top = top + "px";
  }
  function hide(force) {
    if (pinned && !force) return;
    cancelClose(); pinned = false; node.classList.remove("on", "pinned");
    if (owner) owner.setAttribute("aria-expanded", "false"); owner = null;
  }
  function scheduleHide() { cancelClose(); closeTimer = setTimeout(() => hide(false), 90); }
  function open(link, game, t, heading, overlay, doPin) {
    cancelClose();
    if (owner && owner !== link) owner.setAttribute("aria-expanded", "false");
    owner = link; pinned = Boolean(doPin); link.setAttribute("aria-expanded", "true");
    node.dataset.overlay = overlay.state;
    node.innerHTML = `<div class="cfcardhd"><b>${E(heading)}</b><span class="muted">turn ${t.idx} · ${E(t.seat)}</span></div>
      <div class="cfcardnote">${E(overlay.note)}</div><div class="cfchart"></div>
      <div class="hfoot">${pinned ? "Pinned · press Escape or activate the package again to close" : "Hover or focus to inspect · activate to pin"}</div>`;
    node.classList.toggle("pinned", pinned); node.classList.add("on"); place(link);
    frontierChart(node.querySelector(".cfchart"), game, overlay.marks, overlay.paths, () => {},
      { compact: true, interactive: false });
  }
  function show(link, game, t, oracle, doPin) {
    const three = threeWayCounterfactualOverlay(t);
    open(link, game, t, three ? "Actual · private rational · omniscient oracle" : oracle.best_label,
      three || counterfactualOverlay(t, oracle), doPin);
  }
  function showPackage(link, game, t, index, doPin) {
    const three = threeWayCounterfactualOverlay(t);
    open(link, game, t, three ? "Actual · private rational · omniscient oracle"
      : (t.action || {}).label || "MODEL PROPOSAL", three || modelPackageOverlay(t, index), doPin);
  }
  node.addEventListener("mouseenter", cancelClose);
  node.addEventListener("mouseleave", scheduleHide);
  node.addEventListener("focusin", cancelClose);
  node.addEventListener("focusout", scheduleHide);
  document.addEventListener("keydown", evt => { if (evt.key === "Escape") hide(true); });
  COUNTERFACTUAL_CARD = { node, show, showPackage, hide, scheduleHide,
    isPinned: () => pinned, owner: () => owner };
  return COUNTERFACTUAL_CARD;
}

function bindCounterfactualCards(container, game, turns, oracleName) {
  if (!game) return;
  const byId = Object.fromEntries(turns.map(t => [String(t.idx), t]));
  const card = counterfactualCard();
  function bind(link, open) {
    link.addEventListener("mouseenter", () => { if (!card.isPinned()) open(false); });
    link.addEventListener("mouseleave", card.scheduleHide);
    link.addEventListener("focus", () => { if (!card.isPinned()) open(false); });
    link.addEventListener("blur", card.scheduleHide);
    link.addEventListener("click", evt => {
      evt.preventDefault(); evt.stopPropagation();
      if (card.isPinned() && card.owner() === link) card.hide(true); else open(true);
    });
    link.addEventListener("keydown", evt => {
      if (evt.key === " " || evt.key === "Enter") { evt.preventDefault(); link.click(); }
    });
  }
  container.querySelectorAll("[data-counterfactual]").forEach(link => {
    bind(link, pin => {
      const t = byId[String(link.dataset.turnidx)], oracle = t && (t.oracles || {})[oracleName];
      if (t && oracle) card.show(link, game, t, oracle, pin);
    });
  });
  container.querySelectorAll("[data-package-preview]").forEach(link => {
    bind(link, pin => {
      const t = byId[String(link.dataset.turnidx)], index = Number(link.dataset.deal);
      if (t && Number.isInteger(index)) card.showPackage(link, game, t, index, pin);
    });
  });
}

/* A real button, rather than a fragile hash into a hidden panel. The sidebar layer switches to Info and places
   its oracle explanation in view; comparison pages have no tabbed sidebar, where the button safely does nothing. */
function infoLink(label, enabled) {
  if (!enabled) return "";
  return `<button type="button" class="infobtn" data-info-target="info-oracle" aria-label="${E(label)}"
    title="${E(label)}">i</button>`;
}

/* WHO played this turn, when that is not the obvious answer. Live play stamps every turn with its occupant
   (`TurnRecord.occupant`); nothing that ran before live play carries the field at all, so a batch episode's card
   is unchanged. The badge marks a DEPARTURE — a person, or a seat that has changed hands — against
   `opts.occupantDefaults` (seat -> the occupant it started under), which the live page derives from the payload
   and passes in. Without that map only a human turn badges, which is the conservative half of the rule: a
   default is exactly what tells a routine occupant from a swapped one. */
function occupantBadge(t, defaults) {
  const occupant = t.occupant;
  if (!occupant) return "";
  const human = String(occupant).indexOf("human:") === 0;
  const dflt = (defaults || {})[t.seat];
  if (!human && (dflt === undefined || dflt === occupant)) return "";
  const label = human ? String(occupant).slice("human:".length) : occupant;
  return ` <span class="badge occupant${human ? " human" : ""}" title="this turn was played by ${E(occupant)}">${
    human ? "played by " : "now "}${E(label)}</span>`;
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
  /* A SILENT turn that the engine did not fail on: generation succeeded and produced nothing publishable, which
     is what a thinking model does when it spends its whole per-turn budget inside an unterminated <think>. The
     fabrication banner is silent about these by construction — `gen_failed` is false — so the card has to say it
     itself, in the same hazard style, or a quarter-silent episode reads as a quarter of deliberate passes. The
     text that WAS generated is reachable below rather than summarized, because the only honest thing to say
     about it is what it literally is. */
  const silentNote = (t.silent && !t.gen_failed)
    ? `<div class="gap silentnote"><b>This turn published nothing.</b> Its visible text is the engine's
       placeholder, but generation did not fail — the model spent ${t.n_tokens_out || 0} of its
       ${t.cap || "?"}-token budget and never emitted an answer${t.raw ? ", leaving the unterminated scratchpad below" : ""}.
       It parses as a well-formed pass; it is not one. Exclude it from any measurement of what this seat chose.</div>`
    : "";
  /* The excerpt's summary states the TRUE length (`raw_chars`) and says so when it is showing less than that, so
     a capped panel cannot pass for the whole generation. */
  const rawPanel = t.raw
    ? `<details data-lazy="raw" data-turnidx="${t.idx}"><summary>The text the model actually generated before the
        placeholder replaced it — ${t.raw_truncated
          ? `first ${t.raw.length} of ${t.raw_chars} characters`
          : `${t.raw_chars || t.raw.length} characters`}, normally an unterminated scratchpad</summary>
       <div class="body"><div class="lazybody"></div></div></details>`
    : "";
  const dealLink = a.deal_index !== null && a.deal_index !== undefined
    ? `<div class="deal"><a href="#" class="cflink" data-package-preview data-turnidx="${t.idx}"
        data-deal="${a.deal_index}" aria-haspopup="dialog" aria-expanded="false"
        aria-label="Preview the model's package on the frontier">${E(dealSummary(game, a.deal_index))}</a></div>`
    : (a.deal_named ? `<div class="deal neg">proposal did not resolve to a legal deal: ${E(JSON.stringify(a.deal_named))}</div>` : "");
  const w = t.deal_welfare;
  const oracles = Object.keys(t.oracles || {});
  const selectedOracle = (t.oracles || {})[oracle];
  const prefix = opts.idPrefix || "turn-";
  const atCap = Boolean(t.cap && (t.n_tokens_out || 0) >= t.cap - 2);
  return `<article class="turn ${k.cls} k-${E(t.kind)}${t.gen_failed ? " fabricated" : ""}${
     t.silent ? " silent" : ""}" id="${prefix}${t.idx}" data-turnidx="${t.idx}">
   <div class="turnhd" role="button" tabindex="0" aria-label="turn ${t.idx}, ${E(t.seat)}, ${E(k.word)}${
     t.silent ? ", published nothing" : ""}">
     <span class="who"><span class="idx">${t.idx}</span> ${E(t.seat)}
       <span class="badge ${E(t.kind)}">${E(t.kind)}</span>${occupantBadge(t, opts.occupantDefaults)}
       <span class="kind ${k.cls}">${k.glyph} ${E(k.word)}</span>${
       t.gen_failed ? ` <span class="badge fabricated" title="${E(t.gen_failure || "")}">NOT GENERATED</span>` : ""}${
       t.silent && !t.gen_failed ? ` <span class="badge silent" title="generation succeeded but published no
         answer — the engine's placeholder stands in for it">SAID NOTHING</span>` : ""}</span>
     <span class="sub">${E(t.phase)} · round ${t.round}${t.n_tokens_out ? " · " + t.n_tokens_out + " tok out" : ""}${
       atCap ? ` <span class="badge atcap" title="output reached the ${E(t.cap)}-token cap stamped on this
         request, so the turn was cut off rather than finished">AT CAP ${E(t.cap)}</span>` : ""}${
       t.parse_ok ? "" : " · <b class='neg'>parse error</b>"}</span>
   </div>
   ${fabricatedNote}${silentNote}
   ${opts.showCounterfactual ? `<div class="cols">
     <div class="col acted"><div class="hd">the model acted</div><div class="act">${E(a.label || a.atype)}</div>${dealLink}
       ${w ? `<div class="pills"><span class="pill">USW <b>${N(w.usw, 1)}</b></span><span class="pill">worst-off <b class="${w.esw >= 0 ? "pos" : "neg"}">${SIGN(w.esw, 1)}</b></span>${w.n_below_threshold ? `<span class="pill"><b class="neg">${w.n_below_threshold}</b> below τ</span>` : ""}</div>` : ""}
       ${selectedOracle ? `<table><tbody><tr><td>oracle's value of the model's move
         ${infoLink("How the oracle scores the model's move", opts.infoLinks)}</td><td>${N(selectedOracle.chosen_value)}</td></tr></tbody></table>` : ""}</div>
     ${oracleColumn(t, game, oracle, opts.infoLinks)}</div>
     ${referenceGrid(t, game)}`
    : `<div class="act">${E(a.label || a.atype)}</div>${dealLink}`}
   ${t.human_note ? `<div class="reasoning human"><div class="reasoninghd"><b>Scratchpad [the player's own note]</b></div>
      <div class="reasoningbody">${E(t.human_note).replace(/\r?\n/g, "<br>")}</div></div>` : ""}
   ${t.reasoning ? `<div class="reasoning"><div class="reasoninghd"><b>Reasoning / scratchpad [${E(reasoningLabel(t))}]</b></div>
      <div class="reasoningbody">${E(t.reasoning).replace(/\r?\n/g, "<br>")}</div></div>`
     : (t.human_note ? "" : `<div class="sub muted">No reasoning recorded (provenance ${E(t.reasoning_provenance)}). Do not impute it.</div>`)}
   ${a.message ? `<div class="msg">${E(a.message)}</div>` : ""}
   ${a.syntax_error ? `<div class="gap neg">syntax error: ${E(a.syntax_error)}</div>` : ""}
   ${viewPanel(t)}
   ${t.content ? `<details data-lazy="content" data-turnidx="${t.idx}"><summary>Raw turn text as the table saw it</summary>
      <div class="body"><div class="lazybody"></div></div></details>` : ""}
   ${rawPanel}
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
    return `<button class="chip ${k.cls}${t.gen_failed ? " fab" : ""}${t.silent ? " silent" : ""}" data-goturn="${prefix}${t.idx}" data-turnidx="${t.idx}"
      title="turn ${t.idx} · ${E(t.seat)} · ${E(k.word)}${t.gen_failed ? " · NOT GENERATED" : ""}${
        t.silent && !t.gen_failed ? " · SAID NOTHING" : ""}">${t.idx}</button>`;
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
