// interlens — [rational_agents: viz-sidebar] 2026-08-03
//
// Execute a rendered visualizer page's script in a stubbed DOM and report what it built.
//
// The pages render every number server-side, so most of the visualizer is testable without a browser. What is
// NOT is the part that only exists once the script runs: the sidebar's scroll sync. This harness closes that
// gap without a browser — linkedom supplies the DOM, and the handful of browser APIs the page touches that a
// DOM library does not have (layout boxes, storage, matchMedia, IntersectionObserver) are stubbed here.
//
// The IntersectionObserver stub is the interesting one: it records the observed nodes and lets the harness fire
// a synthetic "these turn cards are in the viewport" event, which is exactly the input the sidebar consumes. So
// scrolling is simulated deterministically rather than approximated.
//
// A step may also HOVER a chart mark (`{"hover": 3}` = the mark at that index or the one whose accessible name
// starts with that string, `{"hover": "cloud"}` = a pointer move over the deal cloud, `{"hover": "out"}` = leave
// the chart) and pin it (`{"click": ...}`), which is how the rich hover card is tested. `{"card": {mark}}` opens
// a card for a mark the fixture does not draw, through the page's own controller.
//
// Usage:  node viz_dom_harness.js PAGE.html '[{"turns":[5,6]},{"turns":[9]},{"hover":0}]'
// Output: one JSON object on stdout — {ok, steps:[...], errors:[...]}.  Exit code 1 on any thrown error.
const fs = require("fs");
const { parseHTML } = require("linkedom");

const pagePath = process.argv[2];
const steps = JSON.parse(process.argv[3] || "[]");
const errors = [];

const html = fs.readFileSync(pagePath, "utf8");
const { window, document } = parseHTML(html);

// --- browser APIs a DOM library does not carry -------------------------------------------------------------
const ElementProto = window.Element.prototype;
// Unconditionally, not only when absent: linkedom HAS a getBoundingClientRect and it reports a ZERO-sized box,
// which the chart correctly reads as "not laid out yet" and bails out of all pointer maths. The box below is the
// frontier chart's own viewBox, so a client coordinate is a chart coordinate and a synthetic pointer event can
// aim at a mark's cx/cy exactly.
ElementProto.getBoundingClientRect = function () {
  return { top: 0, left: 0, right: 760, bottom: 470, width: 760, height: 470, x: 0, y: 0 };
};
if (!ElementProto.scrollIntoView) ElementProto.scrollIntoView = function () {};
if (!ElementProto.scrollTo) ElementProto.scrollTo = function () {};
if (!("scrollTop" in ElementProto)) ElementProto.scrollTop = 0;

const observers = [];
class IntersectionObserverStub {
  constructor(callback, options) {
    this.callback = callback; this.options = options; this.targets = [];
    observers.push(this);
  }
  observe(node) { this.targets.push(node); }
  unobserve(node) { this.targets = this.targets.filter(n => n !== node); }
  disconnect() { this.targets = []; }
  // fire a synthetic scroll: `visible` is the set of turn indices now in the viewport
  fire(visible) {
    const set = new Set(visible.map(String));
    this.callback(this.targets.map(node => ({
      target: node, isIntersecting: set.has(String(node.dataset.turnidx)),
      intersectionRatio: set.has(String(node.dataset.turnidx)) ? 1 : 0 })), this);
  }
}

globalThis.window = window;
globalThis.document = document;
globalThis.location = window.location || { href: "" };
globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
globalThis.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
globalThis.IntersectionObserver = IntersectionObserverStub;
window.matchMedia = globalThis.matchMedia;
window.localStorage = globalThis.localStorage;
window.IntersectionObserver = IntersectionObserverStub;

// --- run the page's own script -----------------------------------------------------------------------------
const scripts = Array.from(document.querySelectorAll("script")).filter(s => !s.getAttribute("type"));
if (scripts.length !== 1) { fs.writeFileSync(1, JSON.stringify({ ok: false, errors: ["expected exactly one executable script, found " + scripts.length] })); process.exit(1); }
// The script also hands back the few functions a test needs to call DIRECTLY: a mark kind that a given fixture
// happens not to produce (an episode that closed no deal has no AGREED square) still has to be renderable, and
// asking the page's own function for that card is honest in a way a re-implementation in the test would not be.
let api = {};
try {
  api = new Function(scripts[0].textContent + `
    ;return { game: (typeof G !== "undefined") ? G : null,
              hoverCard: (typeof hoverCard === "function") ? hoverCard : null,
              counterfactualOverlay: (typeof counterfactualOverlay === "function") ? counterfactualOverlay : null };`)() || {};
} catch (e) {
  fs.writeFileSync(1, JSON.stringify({ ok: false, errors: ["page script threw: " + (e && e.stack || e)] }));
  process.exit(1);
}

// --- observe what it built, stepping the synthetic scroll ---------------------------------------------------
const q = (sel) => document.querySelector(sel);
const all = (sel) => Array.from(document.querySelectorAll(sel));
const classesOf = (sel) => all(sel).map(n => n.getAttribute("class") || "");

// --- driving the frontier chart's pointer ------------------------------------------------------------------
// The card only exists once the script runs and only opens on a pointer event, so the harness synthesizes those.
// The stubbed layout box is 760x470 at the origin, which is exactly the chart's viewBox, so a client coordinate
// IS a chart coordinate and aiming at a dot's own cx/cy is a guaranteed hit on the nearest-deal handler.
function mouseAt(node, type, x, y) {
  const ev = new window.Event(type, { bubbles: true });
  if (x !== undefined) { ev.clientX = x; ev.clientY = y; }
  node.dispatchEvent(ev);          // linkedom sets `target` itself, which is what the chart's handlers read
}
function driveChart(step) {
  const svg = q("#chart svg");
  if (!svg) return null;
  if (step.axis) {                                    // an axis-title info control, not a data point
    const dot = q(`#chart [data-axisinfo="${step.axis}"]`);
    if (!dot) return null;
    mouseAt(dot, step.axispin ? "click" : "mouseenter");   // `pin` is taken: it drives the issue-seat picker
    return "axis:" + step.axis;
  }
  if (step.hover === "out") { mouseAt(svg, "mouseleave"); return "out"; }
  if (step.hover === "cloud" || step.click === "cloud") {
    const dot = q("#chart svg circle.dot") || q("#chart svg circle.front");
    if (!dot) return null;
    const x = Number(dot.getAttribute("cx")), y = Number(dot.getAttribute("cy"));
    mouseAt(svg, step.click === "cloud" ? "click" : "mousemove", x, y);
    return "cloud";
  }
  const marks = all("#chart [data-mark]");
  const which = step.hover !== undefined ? step.hover : step.click;
  const node = typeof which === "number" ? marks[which]
    : marks.find(n => (n.getAttribute("aria-label") || "").startsWith(String(which)));
  if (!node) return null;
  mouseAt(node, step.click !== undefined ? "click" : "mouseenter");
  return node.getAttribute("aria-label");
}

// A mark's centre in chart coordinates, whatever shape the renderer chose: circles carry cx/cy, the diamond and
// the square are rects (the diamond additionally rotated about its own centre, which does not move it).
function markCentre(node) {
  if (node.hasAttribute("cx")) return [Number(node.getAttribute("cx")), Number(node.getAttribute("cy"))];
  if (node.hasAttribute("x"))
    return [Number(node.getAttribute("x")) + Number(node.getAttribute("width")) / 2,
            Number(node.getAttribute("y")) + Number(node.getAttribute("height")) / 2];
  return null;
}

function snapshot(label, hovered) {
  const shownSeat = all("#issue-seats .issueseat").filter(n => !n.hasAttribute("hidden"));
  const card = q(".hcard");
  const reasoning = q("#turnlist .reasoning"), message = q("#turnlist .msg");
  const cloudDeals = new Set(all("#chart circle.dot,#chart circle.front").map(n => Number(n.dataset.deal)));
  const marksByDeal = {};
  const solutionMarks = (selector) => all(selector)
    .filter(n => /^(NBS|KS|UTIL|EGAL|MNW)\b/.test(n.getAttribute("aria-label") || ""))
    .map(n => ({ label: n.getAttribute("aria-label"), kind: n.dataset.kind,
                 fill: n.getAttribute("fill"), tag: n.tagName.toLowerCase(),
                 box: [n.getAttribute("cx") || n.getAttribute("x") || n.getAttribute("points"),
                       n.getAttribute("cy") || n.getAttribute("y")] }));
  all("#chart [data-mark]").forEach(n => {
    const deal = String(Number(n.dataset.deal));
    (marksByDeal[deal] ||= []).push({
      deal: Number(deal), kind: n.dataset.kind, fill: n.getAttribute("fill")
    });
  });
  // Always a string, never undefined: JSON.stringify DROPS undefined values, and a key vanishing out of the
  // report reads to the test as a broken harness rather than as "that block is absent from this card".
  const txt = (sel) => ((card && q(sel)) || {}).textContent || "";
  return {
    label,
    hovered: hovered === undefined ? null : hovered,
    card_on: Boolean(card && card.classList.contains("on")),
    card_pinned: Boolean(card && card.classList.contains("pinned")),
    card_kind: txt(".hcard .hkind"),
    card_sub: txt(".hcard .hsub"),
    // every explanation block on the card, joined: a point card has one, an axis card has its definition plus the
    // projection caveat, and a test asking "does the card explain X" should not have to know which block X is in
    card_note: card ? all(".hcard .hnote").map(n => n.textContent).join(" ") : "",
    card_math: ((card && q(".hcard .hmath")) || {}).innerHTML || "",
    card_deal: txt(".hcard .hdeal"),
    card_pills: all(".hcard .pills .pill").map(n => n.textContent),
    card_rank: all(".hcard table.hrank tbody .hnm").map(n => n.textContent),
    card_rank_z: all(".hcard table.hrank tbody tr").map(r => (r.lastElementChild || {}).textContent),
    card_bars: all(".hcard table.hrank tbody .hbar .meter i").length,
    card_goto: ((card && q(".hcard [data-goto]")) || { dataset: {} }).dataset.goto || "",
    // the chart-to-transcript jump: which marks CAN navigate, and where the last click actually landed
    mark_turns: all("#chart [data-markturn]").map(n => [n.getAttribute("aria-label"), n.dataset.markturn]),
    cloud_mark_overlap: Object.keys(marksByDeal).map(Number).filter(deal => cloudDeals.has(deal)),
    mark_stacks: Object.values(marksByDeal).filter(group => group.length > 1).map(group => ({
      deal: group[0].deal, kinds: group.map(m => m.kind), fills: group.map(m => m.fill)
    })),
    party_best_labels: all("#chart text.partybest").map(n => ({
      text: n.textContent, x: n.getAttribute("x"), y: n.getAttribute("y"), anchor: n.getAttribute("text-anchor")
    })),
    axis_dots: all("#chart [data-axisinfo]").map(n => n.dataset.axisinfo),
    flashed: all(".turn.flash").map(n => n.id),
    selected_turn: (all(".turn.sel")[0] || {}).id || "",
    tabs: all("#sidebar .tab").map(t => t.dataset.tab),
    activeTab: (q('#sidebar .tab[aria-selected="true"]') || {}).dataset,
    info_hidden: Boolean(q("#pane-info") && q("#pane-info").hidden),
    info_buttons: all(".infobtn").length,
    acted_oracle_text: (q("#turnlist .col.acted table") || {}).textContent,
    oracle_table_text: (q("#turnlist .col.oracle table") || {}).textContent,
    bubbles: all("#chatlog .bubble").length,
    self_bubble_seats: Array.from(new Set(all("#chatlog .bubble.self").map(b => b.dataset.seat))),
    self_bubbles: all("#chatlog .bubble.self").length,
    future_bubbles: all("#chatlog .bubble.future").length,
    current_bubble: (all("#chatlog .bubble.cur")[0] || { dataset: {} }).dataset.turnidx,
    sync_note: (q("#sync-note") || {}).textContent,
    issue_seat_shown: shownSeat.map(n => n.dataset.seat),
    issue_bars: all("#issue-seats .issueseat:not([hidden]) .issuebar").length,
    deal_marks: all("#issue-seats .issueseat:not([hidden]) .dealmark").length,
    issue_numbers: (q("#issue-seats .issueseat:not([hidden]) .issuenums") || {}).textContent,
    mini_marks: all("#mini-chart [data-mark]").length,
    mini_note: (q("#mini-note") || {}).textContent,
    ghosted_marks: classesOf("#mini-chart [data-mark]").filter(c => /\bghost\b/.test(c)).length,
    mini_fills: Array.from(new Set(all("#mini-chart [data-mark]").map(n => n.getAttribute("fill")))).sort(),
    solution_marks: solutionMarks("#chart [data-mark]"),
    solution_leaders: all("#chart .solutionleader").length,
    mini_solution_marks: solutionMarks("#mini-chart [data-mark]"),
    cf_card_on: Boolean(q(".cfcard.on")),
    cf_card_pinned: Boolean(q(".cfcard.pinned")),
    cf_overlay: (q(".cfcard") || { dataset: {} }).dataset.overlay || "",
    cf_note: (q(".cfcardnote") || {}).textContent || "",
    cf_context: (q("#turnlist .cfcontext") || {}).textContent || "",
    // The COUNT as well as the first one: "no card anywhere explains an accept" is a statement about the whole
    // transcript, and reading one node cannot distinguish an empty document from a correctly silent one.
    cf_context_count: all("#turnlist .cfcontext").length,
    // `at` is the mark's CENTRE regardless of shape, so a test can ask where a mark sits without knowing whether
    // the renderer drew it as a circle or as a rotated rect: the arrow-direction assertion needs exactly that.
    cf_marks: all(".cfchart [data-mark]").map(n => ({ fill: n.getAttribute("fill"), label: n.getAttribute("aria-label"),
      deal: n.dataset.deal, at: markCentre(n) })),
    cf_arrow: Boolean(q(".cfchart .cfpath[marker-end]")),
    // The marker sits on the polyline's LAST vertex, so the final point is where the arrowhead is. Reported as
    // data because "an arrow exists" and "the arrow points at the oracle" are different claims.
    cf_arrow_end: (() => {
      const line = q(".cfchart .cfpath[marker-end]");
      if (!line) return null;
      const pts = (line.getAttribute("points") || "").trim().split(/\s+/);
      return pts.length ? pts[pts.length - 1].split(",").map(Number) : null;
    })(),
    cf_focusable_marks: all(".cfchart [data-mark][tabindex],.cfchart [data-mark][role=button]").length,
    cf_svg_label: (q(".cfchart svg") || {}).getAttribute && q(".cfchart svg").getAttribute("aria-label") || "",
    model_package_links: all("[data-package-preview]").length,
    rational_package_links: all("[data-counterfactual]").length,
    reasoning_text: (reasoning || {}).textContent || "",
    reasoning_html: (reasoning || {}).innerHTML || "",
    reasoning_before_message: Boolean(reasoning && message &&
      Array.from(reasoning.parentElement.children).indexOf(reasoning) < Array.from(message.parentElement.children).indexOf(message)),
  };
}

const out = { ok: true, errors, observers: observers.length, steps: [snapshot("after-load")] };
try {
  // A page with no sidebar (the run index, a comparison) simply has nothing to drive: the steps no-op rather
  // than fail, so the same harness is the no-runtime-errors check for every page kind.
  for (const step of steps) {
    const tab = step.tab && q('#sidebar .tab[data-tab="' + step.tab + '"]');
    if (tab) tab.dispatchEvent(new window.Event("click"));
    const pick = step.pin !== undefined && q("#issue-seat-pick");
    if (pick) {
      // linkedom does not implement <select>.value, so give the node the property a browser would have
      Object.defineProperty(pick, "value", { value: String(step.pin), writable: true, configurable: true });
      pick.dispatchEvent(new window.Event("change"));
    }
    if (step.turns) observers.forEach(o => o.fire(step.turns));
    if (step.info) {
      const info = q("#turnlist .infobtn");
      if (info) info.dispatchEvent(new window.Event("click", { bubbles: true }));
    }
    if (step.counterfactual) {
      const link = all("[data-counterfactual]")[Number(step.counterfactual.index || 0)];
      if (link) {
        const kind = step.counterfactual.event || "mouseenter";
        mouseAt(link, kind);
      }
    }
    if (step.package) {
      const link = all("[data-package-preview]")[Number(step.package.index || 0)];
      if (link) {
        const kind = step.package.event || "mouseenter";
        mouseAt(link, kind);
      }
    }
    // `{"card": {...mark...}}` renders that mark's card through the page's own controller, no pointer involved
    if (step.card && api.hoverCard && api.game) api.hoverCard().pin(api.game, step.card, null);
    const hovered = (step.hover !== undefined || step.click !== undefined || step.axis !== undefined)
      ? driveChart(step) : undefined;
    out.steps.push(snapshot(JSON.stringify(step), hovered));
  }
} catch (e) {
  out.ok = false;
  errors.push("step failed: " + (e && e.stack || e));
}
// stdout is a pipe under pytest. `console.log` writes asynchronously and can be truncated when a rich multi-step
// report exceeds the pipe's buffer and the process exits immediately; a synchronous fd write makes the harness
// report atomic from the caller's point of view.
fs.writeFileSync(1, JSON.stringify(out));
process.exit(out.ok && !errors.length ? 0 : 1);
