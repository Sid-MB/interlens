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
# [implement: live-play/laneC] 2026-08-16
# [implement: live-play/lobby-defaults] 2026-08-19
# [implement: live-play/lobby-redirect-fix] 2026-08-20
"""The lobby's browser layer: edit the seat lineup, then start the game.

Every edit is POSTed to ``/api/lobby`` and the server's response is what the page re-renders from — the server
owns the configuration, the page never keeps its own copy. That is what makes a second browser tab on the lobby
show the same lineup instead of a private one, and it means the validation that matters (does this model exist,
does it accept this thinking mode) happens where the provider is.

``/api/start`` returns the session id; the page then navigates to ``/play``, which is rendered server-side from
the session's snapshot.

Three things are worth knowing before reading the script:

**It edits controls, it does not build them.** Seat cards are rendered once, in Python
(``lobby_page._seat_card``). This layer sets values, toggles ``disabled``, and rebuilds two option lists that
genuinely depend on another choice — the thinking modes a newly picked model allows, and the instances a newly
picked bank contains. When an edit changes the page's SHAPE (a bank with a different party count, so a different
number of cards) it reloads and lets the server render it. A JavaScript copy of the card markup is the fast way
to end up with two lobbies that disagree about what a seat is.

**Field names live in one map.** :js:data:`SEAT_FIELDS` and :js:data:`LOBBY_FIELDS` are the only place this file
spells a state key, and they are exactly the ``data-field`` / ``data-lobby`` attributes the markup carries and
exactly ``SeatConfig``'s dataclass fields. The lobby test pins all three to each other, so a renamed field fails
a test instead of silently editing nothing.

**Defaults are computed, never typed.** Which model a new LLM seat opens on and which thinking mode it takes come
from ``defaultModelId`` / ``defaultThinking``, mirroring ``provider.default_model_id`` /
``provider.default_thinking`` — the provider flags its default model, so no model id is spelled in this file. The
"all model seats" row writes those same fields into many seats at once (``applyAll``) and then saves through the
ordinary whole-seats POST, which is why a bulk edit needs no wire change of its own.

**Only the tab that pressed Start follows the game.** The event stream REPLAYS its whole log to every new
subscriber (that is what makes a reconnect lossless), so a lobby opened while a game is running hears the old
``episode_started`` as if it had just happened. Navigating on it would bounce that tab straight to ``/play`` and
put the lobby — and its "End the session" button — out of reach for as long as the game lasts. So the redirect is
gated on :js:data:`startedHere`, set by this page's own Start click; every other tab stays on the lobby and shows
the running banner (``lobby_page._running_banner``, rendered on every load and unhidden by ``paint``) with its
link to the live page.

**Validation here is a courtesy.** ``validate`` mirrors the server's two rules so Start is disabled before it is
clicked rather than after — the click that costs money should not be the thing that discovers the budget cap is
missing. The server checks again and is the one that refuses.

Owned by lane C.
"""
from __future__ import annotations

from ...viz.assets import JS_SHELL, JS_UTIL

# The lobby page's inline script. See ``lobby_page.render_lobby_html`` for the DOM it drives.
JS_LOBBY = r"""
/* ---- the wire vocabulary: route paths, event names, and the state keys the controls edit ---- */

/* Every key of SeatConfig, in one place. These strings are the `data-field` attribute on each seat control AND
   the JSON keys the server reads, so the mapping between a control and a field is an attribute lookup rather
   than a switch that can fall out of step. */
const SEAT_FIELDS = ["kind", "model_id", "policy", "thinking", "instructions", "display_name"];
/* The game-level keys, carried on `data-lobby`. `budget_usd` is the only numeric one. */
const LOBBY_FIELDS = ["bank", "framing", "instance_id", "budget_usd"];
/* Seat kinds whose participant reads no prose — the private-instruction box is greyed for these. Mirrors
   `lobby_page.NO_INSTRUCTION_KINDS`. */
const NO_INSTRUCTION_KINDS = ["rational", "oracle"];
const POLICY_KINDS = ["rational", "oracle"];
/* The fields the "all model seats" row writes into each seat it applies to. A subset of SEAT_FIELDS, carried on
   `data-all` exactly as a card's are carried on `data-field`. */
const ALL_FIELDS = ["model_id", "thinking", "instructions"];
/* Thinking modes best-first, mirrored from `provider.THINKING_PREFERENCE`: a seat thinks wherever its model
   allows it, and prefers the explicit request over the model's own default so the episode records the condition
   it played under. The model's own `thinking_modes` still decides; this only orders that list. */
const THINKING_PREFERENCE = ["on", "auto", "off"];

const ROUTES = {
  lobby: "/api/lobby",
  start: "/api/start",
  reset: "/api/reset",
  play: "/play",
  events: (sid) => "/api/session/" + encodeURIComponent(sid) + "/events",
};
/* Event names mirrored from `live/events.py`. Mirrored only — this page never invents one. */
const EV = { lobby_state: "lobby_state", episode_started: "episode_started", error: "error" };

/* The lobby state, embedded by the server as an inert JSON tag. This object is the page's single copy: every
   control is read out of it and written back into it, and the server's response replaces it wholesale. */
let STATE = JSON.parse($("lobby-state").textContent);
let postTimer = null, source = null;
/* Whether THIS page started the game. The only thing that distinguishes a live `episode_started` from the one the
   stream replays to every new subscriber, and therefore the only safe gate on the redirect to /play. Set before
   the POST goes out, so an event that beats the response still counts as ours. */
let startedHere = false;

/* ---------------------------------------------------------------- reading the state --- */
function seats() { return STATE.seats || []; }
function models() { return STATE.models || []; }
function modelById(id) { return models().find(m => m.model_id === id) || null; }
function bankById(id) { return (STATE.banks || []).find(b => b.bank_id === id) || null; }
function seatName(i) { return (STATE.seat_names || [])[i] || ("seat " + i); }

/* The two default rules, mirroring `provider.default_thinking` / `provider.default_model_id`. They run whenever
   a seat becomes a model seat or changes model — the point where a card would otherwise show whatever happened
   to be first in the list. */
function defaultThinking(model) {
  const modes = (model || {}).thinking_modes || [];
  if (!modes.length) return "off";
  return THINKING_PREFERENCE.find(m => modes.indexOf(m) >= 0) || modes[0];
}
function defaultModelId() {
  const rank = (m) => (m.default && m.available !== false) ? 0 : (m.available !== false) ? 1 : m.default ? 2 : 3;
  let best = null;
  models().forEach(m => { if (best === null || rank(m) < rank(best)) best = m; });
  return best ? best.model_id : "";
}

/* Whether a seat spends money: a model seat whose model is metered. A provider that omits `metered` is assumed
   to charge — the assumption that costs a wasted cap is better than the one that costs a bill. */
function isMetered(seat) {
  if (seat.kind !== "llm") return false;
  const m = modelById(seat.model_id);
  return !m || m.metered !== false;
}
function meteredCount() { return seats().filter(isMetered).length; }

/* The server's rules, checked here so Start is disabled before it is clicked. Kept in the same order and the
   same words as `lobby_page._problems`. Anything the server would ACCEPT belongs in `notices` instead: a lobby
   that refuses a configuration the server is happy with is a front end forbidding its own back end. */
function validate() {
  const out = [];
  if (!(STATE.banks || []).length) out.push("This provider offers no instance banks.");
  if (!seats().length) out.push("No seats are configured yet.");
  const cap = STATE.budget_usd;
  if (meteredCount() > 0 && !(typeof cap === "number" && isFinite(cap) && cap > 0))
    out.push("A budget cap above $0 is required while a metered model is seated.");
  seats().forEach((s, i) => {
    if (s.kind === "llm" && !s.model_id)
      out.push("Seat " + i + " (" + seatName(i) + ") is a model seat with no model chosen.");
  });
  return out;
}

/* Worth saying, does not block. Mirrors `lobby_page._notices`, minus the exact default label — that one is
   derived from SeatConfig on the server and is not worth a second spelling here to say twice. */
function notices() {
  const out = [];
  seats().forEach((s, i) => {
    if (s.kind === "human" && !String(s.display_name || "").trim())
      out.push("Seat " + i + " (" + seatName(i) + ") has no display name — the transcript will record it "
               + "under the default occupant label.");
  });
  return out;
}

/* ---------------------------------------------------------------- painting --- */
function status(msg, bad) {
  const el = $("lobby-status");
  if (!el) return;
  el.textContent = msg || "";
  el.className = bad ? "sub neg" : "sub muted";
}

function setStat(id, value) { const el = $(id); if (el) el.textContent = value; }

/* Everything on the page that is derived rather than typed: the strip, the problem list, whether Start is live,
   and which seat controls apply to which kind. Called after every edit and after every server response. */
function paint() {
  const problems = validate();
  const list = $("lobby-problems");
  if (list) list.innerHTML = problems.map(p => "<li>" + E(p) + "</li>").join("");
  const notes = $("lobby-notices");
  if (notes) notes.innerHTML = notices().map(n => "<li>" + E(n) + "</li>").join("");
  const start = $("lobby-start");
  if (start) start.disabled = problems.length > 0 || !!STATE.running;
  /* The banner is in the document on every load and shown by state, so a tab that was sitting on the lobby when
     someone else started the game grows the same "watch it or end it" affordance the server would have rendered. */
  const running = $("lobby-running");
  if (running) running.hidden = !STATE.running;
  const cap = STATE.budget_usd;
  setStat("lobby-stat-phase", STATE.phase || (STATE.running ? "running" : "lobby"));
  setStat("lobby-stat-seats", String(seats().length));
  setStat("lobby-stat-metered", String(meteredCount()));
  setStat("lobby-stat-budget", (typeof cap === "number" && isFinite(cap)) ? "$" + cap.toFixed(2) : "—");
  const budget = $("lobby-budget");
  if (budget) budget.required = meteredCount() > 0;
  const n = seats().filter(s => s.kind === "llm").length;
  setStat("lobby-all-count", n + " model seat" + (n === 1 ? "" : "s"));
  shuffleNote();
  seats().forEach((s, i) => paintSeatKind(i));
}

/* Which of a seat card's controls apply to its current kind. The controls stay in the document and are
   disabled rather than removed, so cycling a kind never changes the card's shape. */
function paintSeatKind(idx) {
  const seat = seats()[idx];
  if (!seat) return;
  const off = {
    kind: false,
    model_id: seat.kind !== "llm",
    thinking: seat.kind !== "llm",
    policy: POLICY_KINDS.indexOf(seat.kind) < 0,
    instructions: NO_INSTRUCTION_KINDS.indexOf(seat.kind) >= 0,
    display_name: false,
  };
  SEAT_FIELDS.forEach(f => {
    const control = control_(idx, f);
    if (control) control.disabled = !!off[f];
    const field = document.querySelector(
      '.field[data-seat="' + idx + '"][data-field-for="' + f + '"]');
    if (field) field.classList.toggle("off", !!off[f]);
  });
}

function control_(idx, field) {
  return document.querySelector('[data-seat="' + idx + '"][data-field="' + field + '"]');
}

/* Set a control's value from the state, unless the person is typing in it — resetting the caret mid-sentence
   because a broadcast arrived is the classic way a collaborative form becomes unusable. */
function setValue(control, value) {
  if (!control || control === document.activeElement) return;
  control.value = value === null || value === undefined ? "" : String(value);
}

function options(pairs, selected) {
  return pairs.map(([value, label, disabled]) =>
    "<option value=\"" + E(value) + "\"" + (String(value) === String(selected ?? "") ? " selected" : "")
    + (disabled ? " disabled" : "") + ">" + E(label) + "</option>").join("");
}

/* The option lists that depend on another choice. Everything else is rendered once by the server. */

/* Refill a thinking picker from a model's declared modes and return the mode now selected. A `current` the model
   does not accept (the seat was on another model, or nobody has chosen yet) falls to that model's default, which
   is thinking ON wherever the model allows it. */
function fillThinking(control, model, current) {
  const modes = (model || {}).thinking_modes || ["off"];
  const mode = modes.indexOf(current) >= 0 ? current : defaultThinking(model);
  if (control) control.innerHTML = options(modes.map(m => [m, m, false]), mode);
  return mode;
}

function syncThinking(idx) {
  const seat = seats()[idx], control = control_(idx, "thinking");
  if (!seat || !control) return;
  const model = modelById(seat.model_id);
  seat.thinking = fillThinking(control, model, seat.thinking);
  const hint = $("hint-" + idx + "-thinking");
  const modes = (model || {}).thinking_modes || ["off"];
  if (hint) hint.textContent = modes.length < 2 ? "this model has one thinking mode"
                                                : "only the modes this model accepts are offered; defaults to on";
}

/* A seat that has just become a model seat: give it the provider's default model before its thinking picker is
   filled, so a card that has never been an LLM card does not open on an empty model. */
function applySeatDefaults(idx) {
  const seat = seats()[idx];
  if (!seat || seat.kind !== "llm") return;
  if (!seat.model_id) {
    seat.model_id = defaultModelId();
    setValue(control_(idx, "model_id"), seat.model_id);
  }
  syncThinking(idx);
}

function syncInstances() {
  const control = $("lobby-instance"), bank = bankById(STATE.bank);
  if (!control) return;
  const ids = (bank || {}).instance_ids || [];
  const pairs = [["", "random — let the provider choose", false]].concat(ids.map(i => [i, i, false]));
  if (ids.indexOf(STATE.instance_id) < 0) STATE.instance_id = "";
  control.innerHTML = options(pairs, STATE.instance_id);
}

/* Push the whole state into the controls that already exist. */
function syncControls() {
  LOBBY_FIELDS.forEach(k => {
    const control = document.querySelector('[data-lobby="' + k + '"]');
    if (control) setValue(control, STATE[k]);
  });
  syncInstances();
  seats().forEach((s, i) => {
    syncThinking(i);
    SEAT_FIELDS.forEach(f => setValue(control_(i, f), s[f]));
  });
}

/* ---------------------------------------------------------------- editing --- */
function onEdit(ev) {
  const t = ev.target;
  if (!t || !t.dataset) return;
  if (t.dataset.field && t.dataset.seat !== undefined) {
    const seat = seats()[Number(t.dataset.seat)];
    if (!seat || SEAT_FIELDS.indexOf(t.dataset.field) < 0) return;
    seat[t.dataset.field] = t.value;
    if (t.dataset.field === "model_id") syncThinking(Number(t.dataset.seat));
    if (t.dataset.field === "kind") applySeatDefaults(Number(t.dataset.seat));
  } else if (t.dataset.all) {
    /* The master row is a thing to send, not part of the state: an edit here changes nothing until Apply is
       pressed, so there is no POST and no repaint beyond its own thinking list. */
    if (t.dataset.all === "model_id") fillThinking($("lobby-all-thinking"), modelById(t.value), null);
    allStatus("");
    return;
  } else if (t.dataset.lobby) {
    const key = t.dataset.lobby;
    if (LOBBY_FIELDS.indexOf(key) < 0) return;
    STATE[key] = key === "budget_usd" ? (t.value === "" ? null : Number(t.value)) : t.value;
    if (key === "bank") syncInstances();
  } else return;
  paint();
  schedulePost();
}

/* ---------------------------------------------------------------- the "all model seats" row --- */
function allValue(field) { const c = $("lobby-all-" + field); return c ? c.value : ""; }
function allStatus(msg) { const el = $("lobby-all-status"); if (el) el.textContent = msg || ""; }

/* Write the master row's values into every seat it targets, then save once.

   Targets: the seats that are already model seats, plus — only with the checkbox ticked — every other seat,
   which is CONVERTED to a model seat. Model and thinking mode are overwritten on every target (a bulk control
   whose effect depends on each target's current value cannot be predicted); the shared instructions are written
   only when the box has something in it, so applying a model change does not silently wipe per-seat personas.

   Per-card edits afterwards are ordinary edits: nothing keeps writing from this row. */
function applyAll() {
  const include = !!($("lobby-all-include") || {}).checked;
  const model_id = allValue("model_id"), instructions = allValue("instructions");
  const model = modelById(model_id);
  if (!model_id) { allStatus("no model to apply"); return; }
  const thinking = ((model || {}).thinking_modes || []).indexOf(allValue("thinking")) >= 0
    ? allValue("thinking") : defaultThinking(model);
  let touched = 0, converted = 0;
  seats().forEach((seat, i) => {
    if (seat.kind !== "llm" && !include) return;
    if (seat.kind !== "llm") { seat.kind = "llm"; converted += 1; }
    seat.model_id = model_id;
    seat.thinking = thinking;
    if (instructions.trim()) seat.instructions = instructions;
    touched += 1;
  });
  if (!touched) { allStatus("no seats to apply to — tick the box to convert the others"); return; }
  syncControls();
  paint();
  allStatus("applied " + ((model || {}).label || model_id) + " / thinking " + thinking + " to " + touched
            + " seat" + (touched === 1 ? "" : "s")
            + (converted ? " (" + converted + " converted to model seats)" : "")
            + (instructions.trim() ? ", with the shared instructions" : ""));
  push();
}

/* ---------------------------------------------------------------- shuffling the lineup --- */
/* Randomize who plays which party. The SERVER permutes (`update_lobby({shuffle: true})`) and answers with the
   new lineup, which the page re-renders from like any other edit — so the permutation is recorded on the game
   that gets played rather than living only here, and there is no second shuffle implementation to keep in step.
   Seat names and parties do not move: only the occupant configurations do. */
async function shuffleSeats() {
  const btn = $("lobby-shuffle");
  if (btn) btn.disabled = true;
  try {
    const r = await fetch(ROUTES.lobby, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ shuffle: true }) });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) { status(body.error || ("shuffle refused (" + r.status + ")"), true); return; }
    applyState(body);                                  /* repaints the cards and the note */
    status("shuffled", false);
  } catch (e) {
    status("could not reach the server: " + e, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

/* What the last shuffle did, in the seats' own names — the same line the server rendered, rewritten as the
   state changes so a hand edit afterwards stops it claiming a permutation that no longer describes anything. */
function shuffleNote() {
  const note = $("lobby-shuffle-note");
  if (!note) return;
  const order = STATE.last_shuffle || [];
  const moved = order.map((src, i) => [i, src]).filter(([i, src]) => i !== src);
  note.textContent = !order.length ? "who plays which party is as you set it"
    : !moved.length ? "last shuffle left the lineup unchanged — every arrangement of it looks the same"
    : "last shuffle: " + moved.map(([i, src]) => seatName(i) + " ← " + seatName(src)).join(", ");
}

/* Debounced so typing into the instructions box is one POST at the end of a sentence rather than one per
   keystroke; the state on the page is already correct, this only catches the server up. */
function schedulePost() {
  if (postTimer) clearTimeout(postTimer);
  postTimer = setTimeout(push, 350);
}

/* The patch carries the whole seats list rather than a changed index — one shape for every edit. `overrides`
   (the provider's free-form extra configuration) is deliberately NOT sent: the endpoint takes a partial patch,
   so an omitted key is left alone, and this page has no controls for it. Sending it back would mean round
   tripping a value nothing here understands. */
async function push() {
  postTimer = null;
  const patch = { seats: seats() };
  LOBBY_FIELDS.forEach(k => { patch[k] = STATE[k] === undefined ? null : STATE[k]; });
  try {
    const r = await fetch(ROUTES.lobby, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) { status(body.error || ("lobby edit refused (" + r.status + ")"), true); return; }
    status("saved", false);
    applyState(body);
  } catch (e) {
    status("could not reach the server: " + e, true);
  }
}

/* The server's answer replaces the page's state. A response with a different number of seats is a SHAPE change
   — a bank with a different party count — and the server renders those cards, so the page reloads rather than
   growing a second card builder here. */
function applyState(next) {
  if (!next || !Array.isArray(next.seats)) return;
  if (next.seats.length !== seats().length) { location.reload(); return; }
  STATE = Object.assign({}, STATE, next);
  syncControls();
  paint();
}

async function refresh() {
  try {
    const r = await fetch(ROUTES.lobby, { headers: { "Accept": "application/json" } });
    if (r.ok) applyState(await r.json());
  } catch (e) { /* the server is gone; the page keeps what it has rather than blanking */ }
}

/* ---------------------------------------------------------------- starting --- */
async function start() {
  const problems = validate();
  if (problems.length) { status(problems[0], true); return; }
  const btn = $("lobby-start");
  if (btn) btn.disabled = true;
  status("starting…", false);
  /* Claimed before the request, not after: `episode_started` can arrive on the stream while the POST is still in
     flight, and the tab that clicked must follow the game either way. Released again on every failure path, so a
     refusal cannot leave a stale claim that a later replay would act on. */
  startedHere = true;
  try {
    const r = await fetch(ROUTES.start, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) { startedHere = false; status(body.error || ("could not start (" + r.status + ")"), true); paint(); return; }
    /* The session id is what says a game exists. `episode_id` is null here by design — the engine mints it
       inside run_episode, after the thread is spawned — so gating the redirect on it would strand the page on
       a lobby whose game is already running. */
    if (!body.sid) { startedHere = false; status("the server started nothing it could name; staying here", true); paint(); return; }
    location.href = ROUTES.play;
  } catch (e) {
    startedHere = false;
    status("could not reach the server: " + e, true);
    paint();
  }
}

async function reset() {
  status("ending the session…", false);
  try {
    await fetch(ROUTES.reset, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  } catch (e) { /* fall through to the reload, which shows whatever actually happened */ }
  location.reload();
}

/* ---------------------------------------------------------------- the stream --- */
/* Only a running session has a stream, so this attaches when one exists: a `lobby_state` broadcast keeps a
   second tab's lineup honest, and `episode_started` says a game is now on.

   That last one is REPLAYED to every new subscriber — the log replay is what makes a reconnect lossless — so it
   is not evidence that anything just happened. A tab that did not press Start therefore re-reads the lobby from
   the server and repaints (Start greys, the banner appears) instead of navigating; the banner's link and the `v`
   key are how someone gets to the game from here, and staying put is what keeps "End the session" reachable
   while one is in progress. */
function subscribe(sid) {
  if (!sid || source || typeof EventSource === "undefined") return;
  source = new EventSource(ROUTES.events(sid));
  source.addEventListener(EV.lobby_state, (ev) => {
    try { applyState(JSON.parse(ev.data)); } catch (e) { /* a malformed frame must not blank the lobby */ }
  });
  source.addEventListener(EV.episode_started, () => {
    if (startedHere) { location.href = ROUTES.play; return; }
    /* A replayed frame says a game STARTED, not that one is running now — the session it describes may already
       have finished. So the page asks the server what is true instead of setting `running` from the event, and
       repaints from the answer: the banner, the greyed Start and the phase cell all follow from that one fetch. */
    refresh();
  });
  source.addEventListener(EV.error, (ev) => {
    try { status(JSON.parse(ev.data).message, true); } catch (e) { /* unparseable: nothing useful to show */ }
  });
}

/* ---------------------------------------------------------------- wiring --- */
document.addEventListener("change", onEdit);
document.addEventListener("input", onEdit);
const startBtn = $("lobby-start");
if (startBtn) startBtn.addEventListener("click", start);
const resetBtn = $("lobby-reset");
if (resetBtn) resetBtn.addEventListener("click", reset);
const applyAllBtn = $("lobby-apply-all");
if (applyAllBtn) applyAllBtn.addEventListener("click", applyAll);
const shuffleBtn = $("lobby-shuffle");
if (shuffleBtn) shuffleBtn.addEventListener("click", shuffleSeats);
/* No polling: a lobby with no session has nothing to stream, so a tab catches up when it is looked at again. */
window.addEventListener("focus", refresh);
subscribe(STATE.sid);
if (STATE.error) status(STATE.error, true);
paint();

registerKeys([
  { keys: ["v"], what: "open the live page", run: () => { location.href = ROUTES.play; } },
  { keys: ["r"], what: "reload the lineup from the server", run: refresh },
  { keys: ["a"], what: "apply the all-model-seats row", run: applyAll },
  { keys: ["s"], what: "shuffle who plays which party", run: shuffleSeats },
  { keys: ["?"], what: "show or hide this help", run: () => { const h = $("help"); if (h) h.hidden = !h.hidden; } },
  { keys: ["Escape"], what: "", run: () => { const h = $("help"); if (h) h.hidden = true; } },
]);
"""

#: The lobby page's complete script: the visualizer's formatting helpers and its page shell (theme toggle,
#: keyboard bindings, help overlay), then this page's wiring. Composed the way ``viz.assets.JS_INDEX_PAGE`` is —
#: the lobby carries no episode payload, so none of the chart, hover, transcript or sidebar layers are loaded.
JS_LOBBY_PAGE = "\n".join((JS_UTIL, JS_SHELL, JS_LOBBY))
