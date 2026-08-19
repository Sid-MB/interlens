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
"""The lobby: choose a game and decide who plays each seat.

Built on ``viz.page._document``, the same shell the episode pages use, so the lobby inherits the visualizer's
CSS, its light/dark handling and its layout without a second stylesheet to keep in step. Pure string-building
like the rest of the visualizer: this module renders, it never fetches or mutates.

The one thing the lobby must get right is not offering a configuration that will fail. Model capabilities differ
in ways that are hard errors rather than degradations — the Claude-5 models reject a temperature outright, Fable
cannot turn thinking off, Haiku refuses adaptive thinking — so the seat cards are generated FROM each model's
declared ``thinking_modes`` and ``supports_temperature`` rather than from a fixed set of controls. A budget cap
is required before any metered seat can start, for the same reason: it is the only thing standing between a
click and an unbounded bill.

A seat nobody has configured opens on the provider's own defaults — the model it flagged
(:func:`~interlens.arena.live.provider.default_model_id`) with thinking on wherever that model allows it
(:func:`~interlens.arena.live.provider.default_thinking`) — and the "all model seats" row
(:func:`_all_seats_row`) sets a whole lineup at once. No model id is spelled anywhere in this module.

**Every control is rendered here, in Python, exactly once.** The browser layer changes the VALUES of controls
that already exist and rebuilds only option lists (the thinking modes a newly picked model allows, the instances
a newly picked bank contains); it never builds a seat card. When an edit changes the shape of the page — a bank
with a different party count, so a different number of seat cards — the browser reloads and this function
renders it again. A second copy of the card markup in JavaScript would be the obvious way to do it and the fast
way to end up with two lobbies that disagree about what a seat is.

Owned by lane C.
"""
from __future__ import annotations

import json

from ..viz.chrome import _e, topbar
from ..viz.page import _document
from .assets.js_lobby import JS_LOBBY_PAGE
from .provider import SEAT_KINDS, SeatConfig, default_model_id, default_thinking
from .style import CSS_LIVE

#: What each seat kind is called in the picker, and the one line under it that says what choosing it means. The
#: distinction between ``rational`` and ``oracle`` is the whole point of the arena's computable seats — same
#: policy zoo, different information — so it is spelled out here rather than left to the two words.
SEAT_KIND_LABELS = {
    "llm": ("model", "a hosted or local language model plays this seat"),
    "rational": ("rational policy", "a computable policy with only this seat's private information"),
    "oracle": ("oracle policy", "the same policy with the FULL payoff tables of every party"),
    "human": ("you", "this seat blocks on the browser and you play it"),
    "scripted": ("scripted", "a fixed reply, for smoke tests and demos"),
}

#: Seat kinds whose participant reads no prose, so a private-instruction override would go nowhere. The browser
#: layer greys the same set; this is the copy the server-rendered page starts from.
NO_INSTRUCTION_KINDS = ("rational", "oracle")

#: The lobby's own rules, spelled out on the page so a disabled Start button is never a mystery. The browser
#: layer checks the same conditions live (``js_lobby.validate``); the server checks them again and wins.
LOBBY_RULES = ("A budget cap is required whenever any seat is a metered model — the server refuses to start "
               "without one, since an idle live game with an API seat can spend for a long time.",
               "A model seat needs a model, and an unavailable model cannot be chosen.",
               "A seat played by you does NOT need a display name; without one the transcript records the "
               "default occupant label. The name is worth setting, not required.")

# Lobby-only styling. It lives here rather than in ``viz.assets.css`` because the visualizer's stylesheet is
# shared by every exported page and should not grow controls that only one server-rendered page has. Everything
# structural (cards, strips, pills, buttons, selects, the type scale, both themes) comes from that stylesheet.
#: The lobby's own layout. The form furniture the shared stylesheet never needed — labelled fields, text and
#: number inputs, the disabled-control look, the seat card — is what the PLAY page needs too, so it lives in
#: :data:`~interlens.arena.live.style.CSS_LIVE` and is inlined beside this rather than copied into both pages.
CSS_LOBBY = """
.lobbyrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:var(--sp-3);align-items:start}
.seatgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:var(--sp-3);margin-top:var(--sp-2)}
.startbar{display:flex;gap:var(--sp-3);align-items:center;flex-wrap:wrap;margin-top:var(--sp-3)}
.startbar button.primary{border-color:var(--s1);color:var(--s1);font-weight:600;padding:6px 18px}
.allseats{border:1px dashed var(--ring-2);border-radius:var(--r-2);padding:var(--sp-2) var(--sp-3);margin-top:var(--sp-2)}
.allseats .hd{display:flex;gap:var(--sp-2);align-items:baseline;flex-wrap:wrap}
.allseats .applybar{display:flex;gap:var(--sp-3);align-items:center;flex-wrap:wrap;margin-top:var(--sp-2)}
.allseats label.inline{display:flex;gap:6px;align-items:center;font-size:var(--t-sm);color:var(--ink-2)}
.problems{margin:var(--sp-2) 0 0;padding-left:1.15em;font-size:var(--t-sm);color:var(--critical)}
.problems:empty{display:none}
.notices{margin:var(--sp-2) 0 0;padding-left:1.15em;font-size:var(--t-sm);color:var(--ink-2)}
.notices:empty{display:none}
"""


def render_lobby_html(state: dict) -> str:
    """The complete lobby page.

    ``state`` is ``SessionManager.lobby_state()``: the provider's listings (``banks``, ``framings``, ``models``,
    ``policies``) plus the current selection (``bank``, ``framing``, ``instance_id``, ``seats``, ``budget_usd``)
    and whether a session is already running (``running``, ``sid``). Self-contained — inline CSS and JS, no
    network fetches on load — so it opens the same way the exported visualizer pages do.

    Every key is read defensively: a provider with no banks, a state recorded before a key existed, or a bank
    whose party count is not yet known all render a page that says so rather than raising. A lobby that 500s is
    a lobby nobody can use to fix the configuration that broke it.

    Parameters
    ----------
    state : dict
        The lobby state described above. Embedded verbatim into the document as an inert JSON script tag, which
        is what the browser layer edits and POSTs back — so the page needs no fetch to become interactive.
    """
    seats = list(state.get("seats") or [])
    models = [m for m in (state.get("models") or []) if isinstance(m, dict)]
    policies = [str(p) for p in (state.get("policies") or [])]
    # The server may narrow the kinds this deployment offers (``seat_kinds``); the library's full set is the
    # fallback, so a state that predates the key still renders every kind rather than none.
    kinds = [str(k) for k in (state.get("seat_kinds") or SEAT_KINDS)]
    names = _seat_names(state, len(seats))
    cards = "".join(_seat_card(i, names[i], seats[i], models, policies, kinds=kinds)
                    for i in range(len(seats)))
    seats_body = cards or ("<div class='sub muted'>No seats yet — choose an instance bank whose party count is "
                           "known, and the seat cards appear here.</div>")
    body = (f"<style>{CSS_LIVE}{CSS_LOBBY}</style>"
            "<h1>Live play</h1>"
            "<div class='sub'>Pick a game, decide who sits in each seat, then start. Turns stream into the "
            "visualizer's episode page as they are played, and any seat can be handed to someone else mid-game."
            "</div>"
            f"{_running_banner(state)}"
            f"{_strip(state)}"
            f"{_game_picker(state)}"
            f"<section class='card'><h2>Seats</h2>"
            "<div class='sub muted'>One card per party. A seat's kind decides which of its controls apply; the "
            "rest are greyed rather than hidden, so the lineup is readable at a glance.</div>"
            f"{_all_seats_row(state, models)}"
            f"<div class='seatgrid' id='lobby-seats'>{seats_body}</div></section>"
            f"{_start_bar(state)}"
            f"{_state_script(state)}")
    quick = (f"<span><span class='k'>seats</span> <b>{len(seats)}</b></span>"
             f"<span><span class='k'>phase</span> <b>{_e(state.get('phase') or ('running' if state.get('running') else 'lobby'))}</b></span>")
    return _document("Live play — lobby", topbar("live play", None, quick, brand_title="interlens live play",
                                                 nav=False),
                     body, None, JS_LOBBY_PAGE)


def _seat_card(idx: int, seat_name: str, config: dict, models: list[dict], policies: list[str], *,
               kinds: tuple[str, ...] | list[str] = SEAT_KINDS) -> str:
    """One seat's configuration card: kind picker, then the controls that kind needs — model + thinking mode for
    an LLM seat (generated from that model's declared capabilities), policy for a computable one, player name for
    a human — plus the private-instructions box, greyed out for computable seats since a policy reads no prose.

    Parameters
    ----------
    idx : int
        Seat index, in seat order. Stamped on every control as ``data-seat`` so one delegated listener in the
        browser can attribute a change to a seat without a per-card closure.
    seat_name : str
        The party's display name (``arena.schema.PERSONAS`` for negotiation), used as the card's heading.
    config : dict
        This seat's ``SeatConfig.to_json()``. Each control carries the ``SeatConfig`` field it edits as
        ``data-field``, which is the whole contract between this markup and the browser layer.
    models : list[dict]
        Every model the provider offers, as ``ModelInfo.to_json()`` dicts. Unavailable ones are rendered as
        DISABLED options carrying their reason, never omitted — a model that silently vanishes from the list
        reads as a model that does not exist, and the reason ("ANTHROPIC_API_KEY is not set") is usually the
        fix.
    policies : list[str]
        Policy names for a ``rational``/``oracle`` seat.
    kinds : tuple[str, ...] | list[str]
        Which seat kinds this deployment offers, in display order. Defaults to the library's full
        :data:`~interlens.arena.live.provider.SEAT_KINDS`; a server that narrows the set (no scripted seats, say)
        passes its own, so the picker cannot offer a kind the session would refuse to build.
    """
    kind = str(config.get("kind") or "llm")
    # An unconfigured seat shows the provider's defaults rather than the head of the list: the model the provider
    # flagged, at that model's best thinking mode. Resolved here AND in ``SeatConfig.resolved`` on the server —
    # same two functions, so the card the operator sees is the seat the session would build from it.
    model_id = config.get("model_id") or default_model_id(models)
    chosen = next((m for m in models if m.get("model_id") == model_id), None)
    modes = [str(t) for t in ((chosen or {}).get("thinking_modes") or ("off",))]
    thinking = str(config.get("thinking") or default_thinking(chosen))
    is_llm, is_policy = kind == "llm", kind in ("rational", "oracle")

    kind_opts = [(k, SEAT_KIND_LABELS.get(k, (k, ""))[0], False) for k in kinds]
    model_opts = [(m.get("model_id"), _model_label(m), not m.get("available", True)) for m in models]
    if not model_opts:
        model_opts = [("", "no models offered", True)]
    thinking_opts = [(t, t, False) for t in modes]
    policy_opts = [(p, p, False) for p in policies] or [("", "no policies offered", True)]

    kind_hint = SEAT_KIND_LABELS.get(kind, ("", ""))[1]
    thinking_hint = ("this model has one thinking mode" if len(modes) < 2
                     else "only the modes this model accepts are offered; defaults to on")
    name_hint = (f"the transcript calls you this; left empty it records {_default_label(kind)}"
                 if kind == "human" else "optional occupant label")
    instr_hint = ("a policy reads no prose" if is_policy
                  else "appended to this seat's private context as one labelled segment")
    return (f"<div class='seatcard' data-seat='{idx}' data-seat-name=\"{_e(seat_name)}\">"
            f"<div class='hd'><span class='who'>{_e(seat_name)}</span>"
            f"<span class='pill'>seat <b>{idx}</b></span></div>"
            f"{_field(idx, 'kind', 'plays as', _select(idx, 'kind', kind_opts, kind), kind_hint)}"
            f"{_field(idx, 'model_id', 'model', _select(idx, 'model_id', model_opts, model_id, not is_llm), '', not is_llm)}"
            f"{_field(idx, 'thinking', 'thinking', _select(idx, 'thinking', thinking_opts, thinking, not is_llm), thinking_hint, not is_llm)}"
            f"{_field(idx, 'policy', 'policy', _select(idx, 'policy', policy_opts, str(config.get('policy') or ''), not is_policy), '', not is_policy)}"
            f"{_field(idx, 'display_name', 'display name', _text(idx, 'display_name', config.get('display_name') or '', 'name shown in the transcript'), name_hint)}"
            f"{_field(idx, 'instructions', 'private instructions', _textarea(idx, 'instructions', config.get('instructions') or '', is_policy), instr_hint, is_policy)}"
            "</div>")


def _all_seats_row(state: dict, models: list[dict]) -> str:
    """The "all model seats" row: set a model, a thinking mode and one shared instruction block once, then push
    them into every model seat with one click.

    A five-seat lineup is five identical dropdowns to change by hand, and the interesting live configurations
    (every seat the same model; every seat the same model but one) start from "make them all X". So this row
    exists — but it is a WRITE, not a binding: nothing here is part of the lobby state, nothing is sent to the
    server, and the values only reach the server as ordinary per-seat edits when Apply is pressed. That is the
    whole reason a later per-card edit is not fighting an invisible master value, and the reason the wire
    contract is unchanged (``js_lobby.applyAll`` writes the seat cards and the usual whole-seats POST follows).

    Two rules, both stated on the row rather than inferred:

    - **Apply overwrites the model and the thinking mode of every targeted seat.** No merge, no "only the ones
      that look unset" — a bulk control whose effect depends on each target's current value is a bulk control
      nobody can predict.
    - **The shared instructions are appended-to-the-target only when the box is non-empty**, so pressing Apply to
      change the model does not silently wipe per-seat personas that were typed earlier.

    Targets are the seats that are ALREADY model seats. The checkbox widens that to every seat, converting
    policy/human/scripted seats to model seats — off by default, because turning the person's own seat into an
    API model is not something a click labelled "apply" should do by surprise.

    Parameters
    ----------
    state : dict
        The lobby state, for the seat list the row reports its target count from.
    models : list[dict]
        The same ``ModelInfo.to_json()`` list the seat cards are built from, so the master picker cannot offer a
        model a seat could not take.
    """
    model_id = default_model_id(models)
    chosen = next((m for m in models if m.get("model_id") == model_id), None)
    modes = [str(t) for t in ((chosen or {}).get("thinking_modes") or ("off",))]
    model_opts = [(m.get("model_id"), _model_label(m), not m.get("available", True)) for m in models] \
        or [("", "no models offered", True)]
    n_llm = sum(1 for s in (state.get("seats") or []) if s.get("kind") == "llm")
    return ("<div class='allseats' id='lobby-all'>"
            "<div class='hd'><span class='who'>all model seats</span>"
            f"<span class='pill' id='lobby-all-count'>{_seat_count(n_llm)}</span>"
            "<span class='sub muted'>set the lineup once instead of card by card</span></div>"
            "<div class='lobbyrow'>"
            f"{_all_field('model_id', 'model', _select_all('model_id', model_opts, model_id), 'every targeted seat is set to this model')}"
            f"{_all_field('thinking', 'thinking', _select_all('thinking', [(t, t, False) for t in modes], default_thinking(chosen)), 'the modes the chosen model accepts')}"
            f"{_all_field('instructions', 'shared private instructions', _textarea_all('instructions'), 'applied only when non-empty, so Apply never wipes per-seat text')}"
            "</div>"
            "<div class='applybar'>"
            "<button id='lobby-apply-all' type='button'>Apply to all model seats</button>"
            "<label class='inline' for='lobby-all-include'>"
            "<input type='checkbox' id='lobby-all-include' data-all='include_non_llm'>"
            "also convert seats that are not model seats</label>"
            "<span class='sub' id='lobby-all-status' role='status' aria-live='polite'></span></div>"
            "<div class='sub muted'>Apply overwrites the model and thinking mode of every seat it touches. Edit "
            "any card afterwards — nothing here keeps writing to it.</div>"
            "</div>")


def _game_picker(state: dict) -> str:
    """The bank / framing / instance pickers and the budget cap field.

    The instance list is the SELECTED bank's, with a "let the provider choose" entry first — an empty
    ``instance_id`` is what :meth:`ScenarioProvider.prepare` reads as "choose one", so the picker offers that
    choice rather than pretending an instance must be named. The budget field is marked required exactly when
    some seat is a metered model, which is the same condition the server enforces at start.
    """
    banks = [b for b in (state.get("banks") or []) if isinstance(b, dict)]
    framings = [f for f in (state.get("framings") or []) if isinstance(f, dict)]
    bank_id = str(state.get("bank") or (banks[0].get("bank_id") if banks else ""))
    bank = next((b for b in banks if b.get("bank_id") == bank_id), None)
    if not banks:
        return ("<section class='card'><h2>Game</h2><div class='warn danger'><b>This provider offers no instance "
                "banks.</b> Nothing can be started until it does — check the launcher's instance directories.</div>"
                "</section>")

    bank_opts = [(b.get("bank_id"), _bank_label(b), False) for b in banks]
    framing_opts = [(f.get("framing_id"), f.get("label") or f.get("framing_id"), False) for f in framings] \
        or [("", "no framings offered", True)]
    instance_opts = [("", "random — let the provider choose", False)] + \
                    [(i, i, False) for i in ((bank or {}).get("instance_ids") or [])]
    needs = _needs_budget(state)
    cap = state.get("budget_usd")
    budget = (f"<input type='number' id='{_lobby_control_id('budget_usd')}' data-lobby='budget_usd' "
              f"min='0' step='0.5' "
              f"value=\"{_e('' if cap is None else cap)}\" placeholder='2.00' "
              f"aria-label='budget cap in US dollars'{' required' if needs else ''}>")
    budget_hint = ("required: a metered model is seated" if needs
                   else "no metered seat — no cap needed, but one is harmless")
    return ("<section class='card'><h2>Game</h2>"
            "<div class='lobbyrow'>"
            f"{_lobby_field('bank', 'instance bank', _select_lobby('bank', bank_opts, bank_id), (bank or {}).get('description') or '')}"
            f"{_lobby_field('framing', 'framing', _select_lobby('framing', framing_opts, str(state.get('framing') or '')), _framing_hint(framings, state.get('framing')))}"
            f"{_lobby_field('instance_id', 'instance', _select_lobby('instance_id', instance_opts, str(state.get('instance_id') or '')), 'which game from the bank')}"
            f"{_lobby_field('budget_usd', 'budget cap (USD)', budget, budget_hint, mark_required=needs)}"
            "</div></section>")


# ------------------------------------------------------------------------------------ page furniture --
def _strip(state: dict) -> str:
    """The status strip: where the session is, how many seats cost money, and what the cap is.

    Its cells are ids rather than a re-render target — the browser layer writes their values as the state
    changes, which is the whole reason a metered-seat count is worth having on screen at all."""
    seats = list(state.get("seats") or [])
    metered = _metered_seats(state)
    cap = state.get("budget_usd")
    phase = state.get("phase") or ("running" if state.get("running") else "lobby")
    cells = (("phase", "lobby-stat-phase", _e(phase), "of this server's single session"),
             ("seats", "lobby-stat-seats", str(len(seats)), "one card each"),
             ("metered seats", "lobby-stat-metered", str(metered), "these spend money"),
             ("budget cap", "lobby-stat-budget", "—" if cap is None else f"${float(cap):.2f}", "hard stop"))
    stats = "".join(f"<div class='stat'><div class='k'>{_e(k)}</div>"
                    f"<div class='v' id='{sid}'>{v}</div><div class='n'>{_e(note)}</div></div>"
                    for k, sid, v, note in cells)
    return f"<div class='strip' id='lobby-strip'>{stats}</div>"


def _running_banner(state: dict) -> str:
    """Shown when a session is already live: this server runs ONE at a time, so the honest options are to watch
    it or to end it, and both are offered rather than letting Start fail with a message about it."""
    if not state.get("running"):
        return ""
    return ("<div class='warn' id='lobby-running'><b>A session is already running.</b> This server plays one game "
            "at a time. <a href='/play'>Open the live page</a> to watch or play it, or end it to configure a new "
            "one. <button id='lobby-reset' type='button'>End the session</button></div>")


def _start_bar(state: dict) -> str:
    """The Start button, the live validation list, and the status line the browser layer writes into.

    Start is rendered DISABLED whenever the server-side state already violates a rule, so the page is correct
    before its script runs; the browser layer re-evaluates the same rules on every edit."""
    problems, notices = _problems(state), _notices(state)
    rules = "".join(f"<li>{_e(r)}</li>" for r in LOBBY_RULES)
    return ("<section class='card'>"
            "<div class='startbar'>"
            f"<button id='lobby-start' class='primary' type='button'{' disabled' if problems else ''}>"
            "Start the game</button>"
            "<span class='sub' id='lobby-status' role='status' aria-live='polite'></span></div>"
            f"<ul class='problems' id='lobby-problems'>{''.join(f'<li>{_e(p)}</li>' for p in problems)}</ul>"
            f"<ul class='notices' id='lobby-notices'>{''.join(f'<li>{_e(n)}</li>' for n in notices)}</ul>"
            f"<details><summary>What must be true before a game can start</summary>"
            f"<div class='body'><ul class='sub'>{rules}</ul></div></details>"
            "</section>")


def _state_script(state: dict) -> str:
    """The lobby state as an inert JSON script tag — the same "data in a data position" rule the visualizer's
    payload follows, with ``</`` escaped so nothing inside the data can end the tag.

    Embedding it is what lets the page be interactive without a fetch on load, and it is the ONE copy the
    browser layer edits: every control's value is read back out of this object, never out of the DOM."""
    data = json.dumps(state, ensure_ascii=False, default=str).replace("</", "<\\/")
    return f'<script type="application/json" id="lobby-state">{data}</script>'


# ------------------------------------------------------------------------------------------ controls --
def _field(idx: int, field: str, label: str, control: str, hint: str = "", off: bool = False) -> str:
    """One labelled seat control. ``off`` dims the whole field when the control does not apply to the seat's
    current kind — the control stays in the document (disabled) so the card's shape never changes as a kind is
    cycled, and the browser layer only has to toggle a class and a property."""
    hint_html = f"<span class='hint' id='hint-{idx}-{_e(field)}'>{_e(hint)}</span>" if hint else ""
    return (f"<div class='field{' off' if off else ''}' data-field-for='{_e(field)}' data-seat='{idx}'>"
            f"<label for='seat-{idx}-{_e(field)}'>{_e(label)}</label>{control}{hint_html}</div>")


def _lobby_field(key: str, label: str, control: str, hint: str = "", mark_required: bool = False) -> str:
    """One labelled game-level control, ``key`` being the lobby-state key it edits (``bank``, ``framing``,
    ``instance_id``, ``budget_usd``)."""
    req = " <span class='req' title='required'>*</span>" if mark_required else ""
    hint_html = f"<span class='hint'>{_e(hint)}</span>" if hint else ""
    return (f"<div class='field' data-lobby-field='{_e(key)}'>"
            f"<label for='{_lobby_control_id(key)}'>{_e(label)}{req}</label>{control}{hint_html}</div>")


def _seat_count(n: int) -> str:
    """"3 model seats" — how many seats Apply would touch. One function because the browser layer rewrites this
    text as the lineup changes and a count that stops agreeing with its noun reads as a bug in the count."""
    return f"{n} model seat{'' if n == 1 else 's'}"


def _all_field(field: str, label: str, control: str, hint: str = "") -> str:
    """One labelled control on the "all model seats" row. ``field`` is the ``SeatConfig`` field it will WRITE
    into each targeted seat when Apply is pressed — the same names the per-seat cards carry, so the row and the
    cards cannot mean different things by ``thinking``."""
    hint_html = f"<span class='hint'>{_e(hint)}</span>" if hint else ""
    return (f"<div class='field' data-all-field='{_e(field)}'>"
            f"<label for='{_all_control_id(field)}'>{_e(label)}</label>{control}{hint_html}</div>")


def _all_control_id(field: str) -> str:
    """The DOM id of the master row's control for ``field``. Same reason as :func:`_lobby_control_id`: a label's
    ``for`` and its control's ``id`` are written in different places and must not drift."""
    return f"lobby-all-{field}"


def _select_all(field: str, options: list, selected) -> str:
    """A master-row ``<select>``. ``data-all`` names the seat field it writes, mirroring ``data-field`` on a
    card and ``data-lobby`` on a game control."""
    return (f"<select id='{_all_control_id(field)}' data-all='{_e(field)}'>"
            f"{_options(options, selected)}</select>")


def _textarea_all(field: str) -> str:
    """The master row's shared-instructions box. Starts empty and is never populated from the state: it is a
    thing to send, not a mirror of what any seat currently holds."""
    return (f"<textarea id='{_all_control_id(field)}' data-all='{_e(field)}' rows='2' "
            f"placeholder='private instructions given to every seat this applies to'></textarea>")


def _lobby_control_id(key: str) -> str:
    """The DOM id of the game-level control that edits ``key``. One function so a label's ``for`` and its
    control's ``id`` cannot drift apart — the two are written in different places and would otherwise be two
    copies of the same naming rule."""
    return {"instance_id": "lobby-instance", "budget_usd": "lobby-budget"}.get(key, f"lobby-{key}")


def _select(idx: int, field: str, options: list, selected, disabled: bool = False) -> str:
    """A seat-level ``<select>``, tagged with the seat and the ``SeatConfig`` field it edits."""
    return (f"<select id='seat-{idx}-{_e(field)}' data-seat='{idx}' data-field='{_e(field)}'"
            f"{' disabled' if disabled else ''}>{_options(options, selected)}</select>")


def _select_lobby(key: str, options: list, selected) -> str:
    """A game-level ``<select>``. ``data-lobby`` names the lobby-state key it edits, the same way ``data-field``
    names a seat's."""
    return (f"<select id='{_lobby_control_id(key)}' data-lobby='{_e(key)}'>"
            f"{_options(options, selected)}</select>")


def _text(idx: int, field: str, value, placeholder: str = "") -> str:
    """A seat-level single-line text input."""
    return (f"<input type='text' id='seat-{idx}-{_e(field)}' data-seat='{idx}' data-field='{_e(field)}' "
            f"value=\"{_e(value)}\" placeholder=\"{_e(placeholder)}\">")


def _textarea(idx: int, field: str, value, disabled: bool = False) -> str:
    """A seat-level multi-line input, for the private-instruction override."""
    return (f"<textarea id='seat-{idx}-{_e(field)}' data-seat='{idx}' data-field='{_e(field)}'"
            f"{' disabled' if disabled else ''} rows='3' "
            f"placeholder='extra private instructions for this seat'>{_e(value)}</textarea>")


def _options(options: list, selected) -> str:
    """``<option>`` markup for ``(value, label, disabled)`` triples, with ``selected`` marked. A disabled option
    is how an unavailable model stays visible and unpickable at the same time."""
    out = []
    for value, label, disabled in options:
        value = "" if value is None else str(value)
        sel = " selected" if value == ("" if selected is None else str(selected)) else ""
        out.append(f"<option value=\"{_e(value)}\"{sel}{' disabled' if disabled else ''}>{_e(label)}</option>")
    return "".join(out)


# ------------------------------------------------------------------------------------------- reading --
def _model_label(model: dict) -> str:
    """A model's option text: its label, its backend, and — when it cannot be used — why not, because the reason
    is what tells the reader whether this is a missing key or a missing GPU."""
    label = model.get("label") or model.get("model_id") or "?"
    provider = model.get("provider")
    base = f"{label} ({provider})" if provider else str(label)
    if model.get("available", True):
        return base
    return f"{base} — unavailable: {model.get('unavailable_reason') or 'no reason given'}"


def _bank_label(bank: dict) -> str:
    """A bank's option text: its name and how many instances it holds."""
    n = len(bank.get("instance_ids") or [])
    label = bank.get("label") or bank.get("bank_id") or "?"
    return f"{label} ({n} instance{'' if n == 1 else 's'})"


def _framing_hint(framings: list[dict], chosen) -> str:
    """The selected framing's one-line description, or a neutral line when it has none."""
    f = next((f for f in framings if f.get("framing_id") == chosen), None)
    return (f or {}).get("description") or "the surface story; payoffs are unchanged"


def _seat_names(state: dict, n: int) -> list[str]:
    """Seat display names in seat order, padded when the provider gave fewer than there are seats — a card
    without a name is still a card that has to render."""
    names = [str(s) for s in (state.get("seat_names") or [])]
    return [names[i] if i < len(names) else f"seat {i}" for i in range(n)]


def _metered_seats(state: dict) -> int:
    """How many seats are models that cost money — the count that decides whether a budget cap is required."""
    by_id = {m.get("model_id"): m for m in (state.get("models") or []) if isinstance(m, dict)}
    return sum(1 for s in (state.get("seats") or [])
               if s.get("kind") == "llm" and (by_id.get(s.get("model_id")) or {}).get("metered", True))


def _needs_budget(state: dict) -> bool:
    """Whether this lineup may not start without a cap. Mirrored in the browser layer and enforced by the
    server, which is the one that actually refuses."""
    return _metered_seats(state) > 0


def _problems(state: dict) -> list[str]:
    """Every reason this configuration cannot start, in the words the page shows.

    The same list the browser layer recomputes on each edit (``js_lobby.validate``) and a subset of what the
    server refuses — a lobby that lets a click fail on the server has wasted the one click that costs money."""
    out = []
    if not (state.get("banks") or []):
        out.append("This provider offers no instance banks.")
    if not (state.get("seats") or []):
        out.append("No seats are configured yet.")
    cap = state.get("budget_usd")
    if _needs_budget(state) and not (isinstance(cap, (int, float)) and cap > 0):
        out.append("A budget cap above $0 is required while a metered model is seated.")
    names = _seat_names(state, len(state.get("seats") or []))
    for i, seat in enumerate(state.get("seats") or []):
        if seat.get("kind") == "llm" and not seat.get("model_id"):
            out.append(f"Seat {i} ({names[i]}) is a model seat with no model chosen.")
    return out


def _notices(state: dict) -> list[str]:
    """Things worth saying that do NOT block the game.

    Kept apart from :func:`_problems` on purpose. A human seat with no display name is the case in point: the
    server accepts it and records the seat under a default occupant label, so refusing to start on it would make
    the lobby stricter than the thing it is a front end for — the classic way a client ends up forbidding a
    configuration that works. Saying which label the transcript will carry is the useful half; blocking is not.
    """
    out = []
    names = _seat_names(state, len(state.get("seats") or []))
    for i, seat in enumerate(state.get("seats") or []):
        if seat.get("kind") == "human" and not str(seat.get("display_name") or "").strip():
            out.append(f"Seat {i} ({names[i]}) has no display name — the transcript will record it as "
                       f"{_default_label('human')}.")
    return out


def _default_label(kind: str) -> str:
    """The occupant label a seat of this kind gets with nothing filled in.

    Derived by asking :class:`SeatConfig` rather than spelled out here, so the lobby cannot promise a label the
    router does not actually stamp."""
    return SeatConfig(kind=kind).occupant_label()
