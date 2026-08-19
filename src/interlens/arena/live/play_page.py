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
# [implement: live-play/lobby-defaults] 2026-08-19
"""The live episode page: the visualizer's episode view, plus the controls to play in it.

This is deliberately the EXISTING episode page and not a new one. The body is assembled from the same fragments
the static page uses (``viz.page._chat_bubbles``/``_sidebar``/``_game_cards``/``_issue_pane``, ``viz.chrome``'s
topbar and summary strip) inside the same ``viz.page._document`` shell, and the same chart/transcript/hover JS
runs on the same ``PAYLOAD`` object. What live play adds is a live UPDATE path (``assets/js_live.py``) and two
docks; everything a reader already knows how to read stays exactly where it was.

Rendering server-side from a snapshot, rather than booting an empty page that fetches, is what makes a reload
mid-episode land on the full transcript immediately and then attach to the stream — no flash of an empty game,
no divergence between what was rendered and what is being streamed.

The two docks:

- the HUMAN CONTROL DOCK — an offer builder generated from the deal space (one selector per issue, so an
  unrepresentable deal cannot be expressed), accept/reject/walk/pass buttons enabled from the server's own
  legality verdict, a public message box, a private scratchpad recorded as ``TurnRecord.human_note``, and the
  seat's PRIVATE score sheet with its values and threshold. The player negotiates under exactly the information
  a model seat has, which is the only way a human turn is comparable to a model one.
- the SWAP DOCK — reassign any seat mid-game.

Everything on both docks that the moment decides — which offers may be accepted, which buttons are legal, what
the package under construction is worth — is filled by the browser from the ``awaiting_human`` event. What the
GAME decides — the issues, the options, the sheet — is rendered here, once, so the page does not rearrange
itself when a turn becomes the player's.

Owned by lane D.
"""
from __future__ import annotations

import json

from ..viz.assets import JS
from ..viz.chrome import _e, _num, quick_stats, summary_strip, topbar
from ..viz.page import _document, _legend, _reference_table, _sidebar, _threshold
from .assets import JS_LIVE
from .provider import SEAT_KINDS, default_model_id
from .style import CSS_LIVE

__all__ = ["render_live_html"]

#: What each seat kind is called in the swap dock. Only the LABELS live here: the kinds themselves come from the
#: session's own ``lobby["seat_kinds"]`` (falling back to ``provider.SEAT_KINDS``), so the form offers exactly what
#: the server can build — a kind it grows appears here unlabelled rather than missing, and a kind it drops cannot
#: be picked.
SEAT_KIND_LABELS = {"llm": "model (API)", "rational": "rational policy", "oracle": "omniscient oracle",
                    "human": "human (you)", "scripted": "scripted"}


def _config_script(snapshot: dict) -> str:
    """The live session's non-payload state as an inert JSON tag, read once by ``js_live``.

    Separate from the visualizer payload because it is a different KIND of thing: the payload is the episode (and
    is exactly what a static export carries), this is the session around it — which id to POST to, where in the
    event sequence the render happened, and whether a seat is waiting on a person right now. ``</`` is escaped so
    nothing inside can end the tag, as in ``viz.page._payload_script``."""
    lobby = snapshot.get("lobby") or {}
    data = {"sid": snapshot.get("sid") or lobby.get("sid") or "",
            "seq": snapshot.get("seq") or 0,
            "phase": snapshot.get("phase") or "running",
            "awaiting": snapshot.get("awaiting"),
            "occupants": snapshot.get("occupants") or {}}
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
    return f'<script type="application/json" id="live-config">{body}</script>'


def _status_strips() -> str:
    """The three live read-outs the stream fills: who is being waited on, spend against the cap, and the closing
    banner. Rendered empty rather than omitted so their arrival does not push the page around."""
    return ("<div class='livebar'><div id='live-status'><div class='livestatus'>Attaching to the live "
            "stream…</div></div><div class='pills' id='live-usage'></div></div><div id='live-banner'></div>")


def _seat_sheet(game: dict, seat_idx: int) -> dict | None:
    """One seat's score sheet out of the game record, or ``None`` when the instance carries none."""
    sheets = (game or {}).get("sheets") or []
    return sheets[seat_idx] if 0 <= seat_idx < len(sheets) else None


def _sheet_card(game: dict, seat_idx: int, seat_name: str) -> str:
    """The player's PRIVATE score sheet: what each option on each issue is worth to them, and the threshold they
    have to clear. This is the answer to "what am I maximizing", and the reason a human turn is comparable to a
    model turn at all — a model seat is given exactly this in its prompt.

    Reads ``game.sheets[seat_idx]``, the same structure ``viz.page._issue_bars_svg`` plots, so the numbers on the
    card and the bars in the sidebar cannot disagree."""
    sheets = (game or {}).get("sheets") or []
    issues = (game or {}).get("issues") or []
    if seat_idx >= len(sheets) or not issues:
        return "<div class='gap'>No score sheet is recorded for this seat.</div>"
    sheet = sheets[seat_idx]
    values = sheet.get("values") or []
    rows = []
    for j, issue in enumerate(issues):
        row = values[j] if j < len(values) else []
        cells = " · ".join(f"{_e(opt)} <b>{_num(row[o], 1) if o < len(row) else '—'}</b>"
                           for o, opt in enumerate(issue.get("options") or []))
        rows.append(f"<tr><td>{_e(issue.get('name'))}</td><td>{cells}</td></tr>")
    return (f"<details class='sheetcard' open><summary>Your private sheet — {_e(seat_name)} "
            f"({_e(sheet.get('agent'))}), threshold τ {_threshold(sheet.get('threshold'))}</summary>"
            "<div class='body'><div class='sub'>Your score for a package is the sum of the option you get on "
            "each issue. A package is worth taking only if that total clears your threshold — below it you do "
            "better walking away. Nobody else can see this.</div>"
            f"<div class='tablewrap'><table><tbody>{''.join(rows)}</tbody></table></div></div></details>")


def _offer_builder(game: dict) -> str:
    """One selector per issue, options in the deal space's own order.

    Generated from the space rather than free text, so a package that does not exist cannot be expressed — the
    server validates anyway (``DealSpace.parse``), but a form that can only produce legal deals is the difference
    between playing a game and guessing at a syntax."""
    issues = (game or {}).get("issues") or []
    if not issues:
        return "<div class='gap'>No deal space is available, so there is nothing to build an offer over.</div>"
    fields = []
    for j, issue in enumerate(issues):
        options = "".join(f"<option value='{o}'>{_e(opt)}</option>"
                          for o, opt in enumerate(issue.get("options") or []))
        fields.append(f"<label class='sub'>{_e(issue.get('name'))}"
                      f"<select data-issue='{j}' disabled>{options}</select></label>")
    return f"<div class='offerbuild' id='dock-offer'>{''.join(fields)}</div>"


def _human_dock(awaiting: dict | None, game: dict, sheet: dict | None, *, seat_idx: int = 0,
                seat_name: str = "") -> str:
    """The player's control dock: offer builder over ``game``'s issues and options, action buttons enabled from
    ``awaiting["legal"]``, message box, private scratchpad, and the private score sheet. Rendered (disabled) even
    when ``awaiting`` is ``None``, so the layout does not jump when it is this seat's turn.

    ``sheet`` is this seat's score sheet, used only to decide whether there is one to show — the numbers on the
    card come from ``game.sheets[seat_idx]`` so it and the sidebar's bars read one record. ``seat_idx``/``seat_name``
    identify the seat this dock plays — the browser overrides both from the ``awaiting_human`` event, which is
    authoritative, so a dock rendered for one human seat follows a second one correctly."""
    if awaiting:
        seat_idx = int(awaiting.get("seat_idx", seat_idx))
        seat_name = awaiting.get("seat") or seat_name
    head = ("Waiting — the dock opens when it is your seat's turn." if not awaiting else
            f"Your move — {seat_name}, round {awaiting.get('round')} of {awaiting.get('deadline')}, "
            f"{awaiting.get('phase')}")
    return f"""<section class='card dock{' open' if awaiting else ''}' id='dock' data-seat-idx='{seat_idx}'>
 <h2 id='dock-head'>{_e(head)}</h2>
 <div class='sub'>You are playing <b>{_e(seat_name)}</b> under the same information a model seat has: your own
  sheet, the public conversation, and the offers on the table. Your public message is republished to every other
  seat exactly as a model's is; your scratchpad is private and is stored on the turn.</div>
 <div id='dock-error'></div>
 {_sheet_card(game, seat_idx, seat_name) if sheet else ''}
 <h3>Offers on the table</h3>
 <div id='dock-offers'><div class='sub muted'>No offer on the table is yours to vote on right now.</div></div>
 <h3>Build a package</h3>
 {_offer_builder(game)}
 <div class='pills' id='dock-value'></div>
 <label class='sub'>Public message — every seat sees this
  <textarea id='dock-msg' rows='3' disabled placeholder='what you say to the table'></textarea></label>
 <label class='sub'>Private scratchpad — recorded on the turn, shown to nobody
  <textarea id='dock-note' rows='2' disabled placeholder='why you are doing this'></textarea></label>
 <div class='bar' id='dock-actions'>
  <button id='dock-propose' disabled>Propose this package</button>
  <button id='dock-talk' disabled>Say this and nothing else</button>
  <button id='dock-pass' disabled>Pass</button>
  <button id='dock-walk' disabled>Walk away</button>
 </div>
</section>"""


def _swap_dock(occupants: dict, lobby: dict, seat_names: list | None = None) -> str:
    """The mid-game seat-reassignment dock: current occupant per seat and the controls to hand it to somebody
    else. Swaps take effect on the seat's NEXT turn.

    ``seat_names`` are the GAME's seat names in seat order (the payload's, i.e. the personas the transcript and
    the occupant map are keyed by) — a seat is identified here by the name it speaks under, not by whatever the
    lobby form called its occupant, or the occupant lookup would miss on every seat whose player is unnamed.

    The kind picker is generated from ``lobby["seat_kinds"]`` — the session's own list of what it can build — so
    the form and the server cannot come to disagree about the vocabulary.

    The server is the authority on whether a swap is allowed — it refuses one while that seat's human prompt is
    open, because the person is mid-decision and the turn is already theirs — so the form always submits and
    surfaces a refusal, rather than deciding legality a second time in the browser and getting it subtly
    differently."""
    seats = lobby.get("seats") or []
    models = [m for m in (lobby.get("models") or []) if m.get("available", True)]
    policies = lobby.get("policies") or []
    names = list(seat_names or [])
    buildable = lobby.get("seat_kinds") or SEAT_KINDS
    # A seat that is not a model seat has no model to pre-select, and the browser would silently select whichever
    # option happens to be first. Handing a seat to a model mid-game should offer the same model the lobby would
    # have — the provider's flagged default — so the dock asks the same function the lobby card does.
    fallback_model = default_model_id(models)
    cards = []
    for i, config in enumerate(seats):
        name = (names[i] if i < len(names) else None) or config.get("display_name") or f"seat {i}"
        kinds = "".join(f"<option value='{_e(k)}'{' selected' if config.get('kind') == k else ''}>"
                        f"{_e(SEAT_KIND_LABELS.get(k, k))}</option>" for k in buildable)
        seat_model = config.get("model_id") or fallback_model
        model_options = "".join(
            f"<option value='{_e(m.get('model_id'))}'{' selected' if seat_model == m.get('model_id') else ''}>"
            f"{_e(m.get('label') or m.get('model_id'))}</option>" for m in models)
        policy_options = "".join(
            f"<option value='{_e(p)}'{' selected' if config.get('policy') == p else ''}>{_e(p)}</option>"
            for p in policies)
        cards.append(
            f"<div class='seatswap' data-seat-idx='{i}'>"
            f"<div class='hd'>{_e(name)} <span class='badge' id='occupant-{i}'>"
            f"{_e(occupants.get(name) or config.get('kind') or '—')}</span></div>"
            f"<label class='sub'>plays as<select id='swap-kind-{i}'>{kinds}</select></label>"
            f"<label class='sub'>model<select id='swap-model-{i}'>{model_options}</select></label>"
            f"<label class='sub'>policy<select id='swap-policy-{i}'>{policy_options}</select></label>"
            f"<label class='sub'>player name<input id='swap-name-{i}' value='{_e(config.get('display_name') or '')}'></label>"
            f"<button data-swap-seat='{i}'>Hand this seat over</button>"
            f"<span class='sub' id='swap-error-{i}'></span></div>")
    if not cards:
        return ""
    return (f"<section class='card swapdock'><h2>Who is playing what</h2>"
            "<div class='sub'>A swap takes effect on that seat's next turn, and every turn records who held the "
            "seat when it was played — so a game that changed hands stays readable as one. A seat whose human "
            "prompt is open cannot be swapped: that turn already belongs to the person deciding it.</div>"
            f"<div class='seatswaps'>{''.join(cards)}</div></section>")


def render_live_html(snapshot: dict) -> str:
    """The complete live page for a session.

    ``snapshot`` is ``LiveSession.snapshot()``: ``{seq, payload, phase, awaiting, occupants, lobby}``. The
    ``payload`` is a full ``viz.episode_payload`` — the same object the exported page is built from — so the page
    is a correct static rendering of the game so far even before its JS runs, and ``seq`` is the sequence number
    the page then subscribes from so nothing is missed between render and attach.
    """
    payload = snapshot.get("payload") or {}
    lobby = snapshot.get("lobby") or {}
    awaiting = snapshot.get("awaiting")
    occupants = snapshot.get("occupants") or {}
    ep = payload.get("episode") or {}
    game = payload.get("game") or {}
    oracles = payload.get("oracle_names") or []
    counterfactual = payload.get("counterfactual_oracles") or []
    ordered = counterfactual + [o for o in oracles if o not in counterfactual]
    options = "".join(f'<option value="{_e(o)}">{_e(o)}</option>' for o in ordered)
    selector = (f"<label class='sub'>detailed counterfactual <select id='oracle-select'>{options}</select></label>"
                if oracles else "")
    # WHICH seat this browser plays. The first human seat in the lineup is the one the dock is rendered for; the
    # `awaiting_human` event overrides it per ask, so a lineup with two human seats still works — the dock
    # follows whichever one the engine is waiting on.
    seat_names = [s.get("name") for s in payload.get("seats") or []]
    human = next((i for i, s in enumerate(lobby.get("seats") or []) if s.get("kind") == "human"), 0)
    seat_idx = int(awaiting.get("seat_idx") if awaiting else human)
    seat_name = (awaiting.get("seat") if awaiting else
                 (seat_names[seat_idx] if seat_idx < len(seat_names) else ""))
    chart = (f"""<section class='card' id='frontier'><h2>Where every deal sits, and where this game is going</h2>
 <div class='sub'>Joint welfare (mean normalized surplus) across, the worst-off party's normalized surplus up —
  both scale-invariant, so the two axes carry the normative content of a deal whatever the sheets are worth. Up
  and to the right is better for everyone. Every move redraws this as it is played.</div>
 {_legend('episode')}
 <div id='chart'></div>
 <div class='bar'><button id='table-toggle' aria-pressed='false'>Show the numbers as a table</button>
  <span class='sub muted'>every reference point, exactly</span></div>
 <div id='chart-table' hidden>{_reference_table(game)}</div>
 <div class='detail' id='detail'></div></section>""" if game else "")
    regret = (f"""<section class='card'><h2>Per-turn value gap against the oracle</h2>
 <div class='sub'>Each bar is the oracle's value of its own best move minus its value of the move the seat
  played, in that oracle's units. It fills in as the game goes; on a private-information game it is an omniscient
  hindsight gap, not regret against a policy the seat could have implemented.</div>
 <div class='bar'>{selector}</div><div id='regret'></div></section>""" if oracles else "")
    body = f"""<style>{CSS_LIVE}</style>
<h1>{_e(ep.get('scenario') or lobby.get('instance_id') or 'live game')} —
 <code>{_e(ep.get('episode_id'))}</code></h1>
{_status_strips()}
{summary_strip(payload)}
{_human_dock(awaiting, game, _seat_sheet(game, seat_idx), seat_idx=seat_idx, seat_name=seat_name or '')}
{_swap_dock(occupants, lobby, seat_names)}
<div class='layout'><div>
{chart}{regret}
<section class='card'><h2>Transcript — every turn as it is played</h2>
 <div class='sub'>Every panel is expandable: the reasoning recorded for the turn, the exact prompt the seat saw,
  the raw turn text, and every action each oracle scored. A turn played by somebody other than the seat's usual
  occupant is badged with who played it. The rail below is every turn — click a chip to jump to it.</div>
 <div class='bar'><button id='expand-all'>Expand all panels</button>
  <button id='collapse-all'>Collapse all</button>
  <span class='sub muted'>or press <kbd>e</kbd> / <kbd>c</kbd>; <kbd>j</kbd> <kbd>k</kbd> walk the turns;
   <kbd>p</kbd> jumps to your dock</span></div>
 <div id='turns'></div></section>
</div>{_sidebar(payload)}</div>
{_config_script(snapshot)}"""
    return _document(f"{ep.get('episode_id') or 'live'} — live play",
                     topbar(_e(lobby.get('instance_id') or ep.get('scenario') or 'live play'), "/",
                            quick_stats(payload), brand_title="back to the lobby"),
                     body, payload, JS + "\n" + JS_LIVE)
