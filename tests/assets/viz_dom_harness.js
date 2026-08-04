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
// Usage:  node viz_dom_harness.js PAGE.html '[{"turns":[5,6]},{"turns":[9]}]'
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
if (!ElementProto.getBoundingClientRect)
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
if (scripts.length !== 1) { console.log(JSON.stringify({ ok: false, errors: ["expected exactly one executable script, found " + scripts.length] })); process.exit(1); }
try {
  new Function(scripts[0].textContent)();
} catch (e) {
  console.log(JSON.stringify({ ok: false, errors: ["page script threw: " + (e && e.stack || e)] }));
  process.exit(1);
}

// --- observe what it built, stepping the synthetic scroll ---------------------------------------------------
const q = (sel) => document.querySelector(sel);
const all = (sel) => Array.from(document.querySelectorAll(sel));
const classesOf = (sel) => all(sel).map(n => n.getAttribute("class") || "");

function snapshot(label) {
  const shownSeat = all("#issue-seats .issueseat").filter(n => !n.hasAttribute("hidden"));
  return {
    label,
    tabs: all("#sidebar .tab").map(t => t.dataset.tab),
    activeTab: (q('#sidebar .tab[aria-selected="true"]') || {}).dataset,
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
    out.steps.push(snapshot(JSON.stringify(step)));
  }
} catch (e) {
  out.ok = false;
  errors.push("step failed: " + (e && e.stack || e));
}
console.log(JSON.stringify(out));
process.exit(out.ok && !errors.length ? 0 : 1);
