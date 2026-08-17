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
# [implement: live-play/laneD] 2026-08-16
"""The live PLAY page: the episode view a person can act inside, and the badge that says who acted.

Three things are worth pinning here and the rest follows from them:

1. the page a browser is served mid-episode already contains the game — the transcript, the chart's numbers, the
   sidebar — because it is rendered server-side from the session snapshot rather than fetched by script. A page
   whose content only appears once its JS runs cannot be reloaded mid-game, which is the failure this design
   exists to avoid;
2. the dock renders what a person needs to make a legal, informed move: one selector per issue (so an
   unrepresentable deal cannot be expressed), their OWN sheet and threshold, and the action buttons — present
   and disabled when it is not their turn, so the layout does not jump when it becomes their turn;
3. the occupant badge appears on exactly the turns whose occupant is not the seat's routine one, and on NO turn
   of an episode recorded before the field existed. The last clause is the one with teeth: every other
   visualizer suite pins the static pages, so a badge that leaked onto ordinary turns would be a silent change
   to every page in every campaign export.

The fixtures reuse the visualizer suite's scored negotiation episode, so this suite and that one are pinned to
the same game rather than to two independently drifting fakes.
"""
from __future__ import annotations

import copy
import json
import re

import pytest

from interlens.arena import viz
from interlens.arena.live.play_page import render_live_html
from interlens.arena.viz import page as viz_page

from .test_arena_viz import _instance, _missing, _run

# Who plays what in the fixture lineup. Seat 0 is the person at the keyboard; the rest are models and policies,
# which is the mixed table live play exists to run.
LOBBY_SEATS = [{"kind": "human", "display_name": "Sid", "model_id": None, "policy": None},
               {"kind": "llm", "display_name": "", "model_id": "claude-fable-5", "policy": None},
               {"kind": "rational", "display_name": "", "model_id": None, "policy": "bayes-rational"},
               {"kind": "oracle", "display_name": "", "model_id": None, "policy": "bayes-rational"}]


@pytest.fixture(scope="module")
def episode():
    inst, cfg = _instance()
    return _run(inst, cfg)


@pytest.fixture(scope="module")
def payload(episode):
    ep, inst = episode
    return viz.episode_payload(ep, inst)


@pytest.fixture(scope="module")
def stamped(payload):
    """The same payload with live-play provenance on ONE turn: a person played it, and left a note.

    Stamped on a copy of a real payload rather than built by hand, so the badge is asserted against the row shape
    the live server actually streams (``viz.episode._turn_payload`` fills ``occupant``/``human_note`` from the
    turn record) instead of against a fixture that agrees with the renderer by construction."""
    out = copy.deepcopy(payload)
    seat = out["turns"][0]["seat"]
    for t in out["turns"]:
        # Every turn of the game has an occupant once it is played live; only the LAST turn of this seat changed
        # hands, which is the distinction the badge has to draw.
        t["occupant"] = "api:claude-fable-5" if t["seat"] == seat else "policy:bayes-rational"
    handed_over = [t for t in out["turns"] if t["seat"] == seat][-1]
    handed_over["occupant"] = "human:Sid"
    handed_over["human_note"] = "taking this one myself: the model was about to accept below my threshold"
    return out, handed_over


def _snapshot(payload, awaiting=None, occupants=None):
    """A session snapshot as ``LiveSession.snapshot()`` returns one."""
    return {"sid": "s1", "seq": 12, "phase": "awaiting_human" if awaiting else "running", "awaiting": awaiting,
            "occupants": occupants or {}, "payload": payload,
            "lobby": {"sid": "s1", "instance_id": "inst-1", "seats": LOBBY_SEATS, "budget_usd": 2.0,
                      "models": [{"model_id": "claude-fable-5", "label": "Fable 5", "available": True},
                                 {"model_id": "gone", "label": "Unavailable", "available": False}],
                      "policies": ["bayes-rational", "hardball"]}}


def _awaiting(payload):
    """An ``awaiting_human`` event for seat 0, with the two live offers it may vote on.

    The legal block is built through the protocol's own builder, so this fixture carries exactly the keys a real
    event carries — including any ratified later — rather than a hand-written subset that would let the page
    tests pass against a shape the browser never actually receives."""
    from interlens.arena.live import events
    sheet = payload["game"]["sheets"][0]
    # Accept and reject are separate lists on purpose: the forced-final proposal turn permits accept and NOT
    # reject, so the dock cannot read one from the other. P2 is rejectable here, P1 is not.
    _type, data = events.awaiting_human(
        seat=payload["seats"][0]["name"], seat_idx=0, turn_idx=9, round_=2, phase="proposal",
        state={"offers": {"P1": [0, 0, 0], "P2": [1, 2, 0]}, "standing": "P2", "round": 2},
        sheet={"values": sheet["values"], "threshold": sheet["threshold"]},
        legal={"can_accept": ["P1", "P2"], "can_reject": ["P2"], "can_offer": True, "can_walk": True},
        deadline=6)
    return data


# ------------------------------------------------------------------------------- the page --
def test_the_live_page_renders_the_game_server_side(payload):
    """A browser attaching mid-episode gets the game, not a shell that will fetch one.

    Asserted on the panels a reader would look for and on the transcript's actual content: the chart's numeric
    table, the sidebar's tabs, and every published turn's chat bubble are all in the document before any script
    runs, which is what makes reloading mid-game land where the reader was."""
    html = render_live_html(_snapshot(payload))
    assert not _missing(html, "id='chart'", "id='regret'", "id='turns'", "id='chart-table'",
                        "class='sidebar' id='sidebar'", "id='chatlog'", "id='live-status'", "id='live-usage'",
                        "id='live-banner'")
    published = [t for t in payload["turns"] if t.get("published", True)]
    assert published, "the fixture episode published no turns"
    assert not _missing(html, *[f"id='bub-{t['idx']}'" for t in published])


def test_the_page_is_self_contained(payload):
    """No CDN, no external stylesheet, no font: a live page is opened over an ssh tunnel to a cluster node that
    may reach nothing at all, and one external reference would leave the chart blank."""
    html = render_live_html(_snapshot(payload))
    assert not re.search(r'(src|href)\s*=\s*[\'"](?!#)(https?:)?//', html)
    assert "<link" not in html
    assert "@import" not in html


def test_the_session_config_travels_as_inert_json(payload):
    """The session's own state (which id to POST to, where in the sequence this render happened, whether a seat
    is waiting) is data in a data position — never interpolated into executable code — and a closing-tag
    sequence inside it cannot end the tag."""
    awaiting = _awaiting(payload)
    awaiting["state"]["note"] = "</script><script>alert(1)</script>"
    html = render_live_html(_snapshot(payload, awaiting=awaiting))
    block = re.search(r'<script type="application/json" id="live-config">(.*?)</script>', html, re.S)
    assert block, "the live config tag is missing"
    config = json.loads(block.group(1).replace("<\\/", "</"))
    assert config["sid"] == "s1" and config["seq"] == 12
    assert config["awaiting"]["legal"]["can_accept"] == ["P1", "P2"]
    assert "<script>alert(1)</script>" not in block.group(1)


# ------------------------------------------------------------------------------- the dock --
def test_the_dock_offers_one_selector_per_issue_and_nothing_unrepresentable(payload):
    """The offer builder is generated FROM the deal space, so every option a person can pick is a legal option
    and no option outside it can be expressed. A free-text deal box would put the space's syntax between the
    player and the game."""
    html = render_live_html(_snapshot(payload))
    issues = payload["game"]["issues"]
    dock = html.split("id='dock'")[1].split("</section>")[0]
    assert dock.count("<select data-issue=") == len(issues)
    for j, issue in enumerate(issues):
        assert f"data-issue='{j}'" in dock
        for o in range(len(issue["options"])):
            assert f"<option value='{o}'>" in dock
        for option in issue["options"]:
            assert option in dock


def test_the_dock_shows_the_players_own_sheet_and_threshold(payload):
    """"What am I maximizing" is on the page. A model seat is given its sheet and threshold in its prompt; a
    person without them is not playing the same game, and their turn is not comparable to a model's."""
    html = render_live_html(_snapshot(payload))
    sheet = payload["game"]["sheets"][0]
    assert "Your private sheet" in html
    assert f"threshold τ {viz_page._threshold(sheet['threshold'])}" in html
    # every option value on the human seat's sheet, on the card
    for row in sheet["values"]:
        for v in row:
            assert f"<b>{v:.1f}</b>" in html or f"<b>{v:g}</b>" in html


def test_the_dock_is_present_and_disabled_when_it_is_not_your_turn(payload):
    """Rendered always, enabled only when a seat is actually waiting — so the page does not rearrange itself at
    the moment a person has to make a decision. Enabling is the browser's job, from the server's own legality
    verdict; nothing here decides legality a second time."""
    idle = render_live_html(_snapshot(payload))
    dock = idle.split("id='dock'")[1].split("</section>")[0]
    assert "Waiting — the dock opens when it is your seat" in dock
    for control in ("dock-propose", "dock-walk", "dock-pass", "dock-msg", "dock-note"):
        assert re.search(rf"id='{control}'[^>]*disabled", dock), f"{control} is not disabled while idle"

    live = render_live_html(_snapshot(payload, awaiting=_awaiting(payload)))
    open_dock = live.split("id='dock'")[1].split("</section>")[0]
    assert "Your move" in open_dock and "round 2 of 6" in open_dock
    assert "class='card dock open'" in live


def test_the_dock_carries_a_public_message_and_a_private_scratchpad(payload):
    """Two text channels, labelled by who can see them. Conflating them is the one mistake in this UI that
    cannot be taken back: a note meant for nobody would be republished to every seat."""
    html = render_live_html(_snapshot(payload))
    assert "Public message — every seat sees this" in html
    assert "Private scratchpad — recorded on the turn, shown to nobody" in html
    assert "id='dock-msg'" in html and "id='dock-note'" in html


# ------------------------------------------------------------------------------- the swap dock --
def test_the_swap_dock_offers_every_buildable_seat_kind_and_the_current_occupant(payload):
    """One card per seat, the kinds taken from the provider's own vocabulary, and unavailable models kept out of
    the picker — a form that can only produce configurations the server can build."""
    names = [s["name"] for s in payload["seats"]]
    html = render_live_html(_snapshot(payload, occupants={names[0]: "human:Sid",
                                                          names[1]: "api:claude-fable-5"}))
    assert "Who is playing what" in html
    # A seat is identified by the name it SPEAKS under — the occupant map, the transcript and this strip are all
    # keyed by it, so a strip keyed by anything else would show "—" for every seat that has a player.
    assert not _missing(html, *names)
    assert "human:Sid" in html and "api:claude-fable-5" in html
    for i in range(len(LOBBY_SEATS)):
        assert f"data-swap-seat='{i}'" in html
        assert f"id='occupant-{i}'" in html
        assert f"id='swap-kind-{i}'" in html
    assert not _missing(html, "model (API)", "rational policy", "omniscient oracle")
    assert "Fable 5" in html
    assert "Unavailable" not in html


def test_a_swap_refusal_has_somewhere_to_land(payload):
    """The server refuses a swap while that seat's human prompt is open, and v1 surfaces the refusal rather than
    pre-blocking the control — two places deciding legality is how they come to disagree."""
    html = render_live_html(_snapshot(payload, awaiting=_awaiting(payload)))
    for i in range(len(LOBBY_SEATS)):
        assert f"id='swap-error-{i}'" in html
    assert "cannot be swapped" in html


# ------------------------------------------------------------------------------- the occupant badge --
def test_the_badge_marks_the_stamped_turn_and_only_it(stamped):
    """A badge on the turn a person took over, none on the turns the seat played under its usual occupant.

    Badging every turn of a live game would be noise (a seat that never changed hands says the same thing thirty
    times); badging none would lose the one fact a mixed human/model transcript has to carry."""
    payload, handed_over = stamped
    bubbles = viz_page._chat_bubbles(payload)
    assert bubbles.count("class='badge occupant") == 1
    assert "played by Sid" in bubbles
    badged = [chunk.split("'")[0] for chunk in bubbles.split("id='bub-")[1:] if "played by Sid" in chunk]
    assert badged == [str(handed_over["idx"])]


def test_the_badge_is_absent_from_every_episode_recorded_before_occupants_existed(payload):
    """The claim with teeth: an episode with no occupant field renders byte-identically to what it rendered
    before the field existed. Every campaign export in the project is such an episode."""
    assert "badge occupant" not in viz_page._chat_bubbles(payload)
    # The rendered-badge spelling, not the browser script's: the page carries the transcript renderer that KNOWS
    # how to badge, and must simply never have found a turn to badge.
    assert "class='badge occupant" not in viz.render_episode_html(payload)
    assert viz_page.occupant_defaults(payload) == {}


def test_a_bubble_rendered_alone_agrees_with_the_bubble_rendered_in_the_list(stamped):
    """The live server renders ONE arriving bubble (``live.payload.bubble_html`` -> ``_chat_bubble``) while a
    reload renders the whole list. They must be the same bytes, badge included — which is why the defaults map
    is derived from the payload rather than passed by whichever caller happens to have one."""
    payload, handed_over = stamped
    alone = viz_page._chat_bubble(payload, handed_over)
    assert alone in viz_page._chat_bubbles(payload)
    assert "played by Sid" in alone


def test_the_human_note_renders_as_the_players_scratchpad_not_as_reasoning(stamped):
    """A person's note is recorded and shown where a model's reasoning is shown, labelled as what it is. It must
    never be presented as a reasoning trace, and its presence must replace the "no reasoning recorded" line —
    which would otherwise sit directly above the note it is denying."""
    from interlens.arena.viz.assets import JS_TRANSCRIPT
    assert "t.human_note" in JS_TRANSCRIPT
    assert "Scratchpad [the player's own note]" in JS_TRANSCRIPT
    fallback = JS_TRANSCRIPT.split("No reasoning recorded")[0]
    assert fallback.rstrip().endswith("(t.human_note ? \"\" : `<div class=\"sub muted\">")


def test_the_turn_card_badges_a_departure_and_needs_the_defaults_map_to_see_one():
    """The transcript card's badge rule, read off the shipped script: a human turn always badges, and anything
    else badges only against a map of what each seat normally is. Pinned as source because the alternative is a
    browser in the test suite."""
    from interlens.arena.viz.assets import JS_TRANSCRIPT
    assert "function occupantBadge(t, defaults)" in JS_TRANSCRIPT
    assert "occupantBadge(t, opts.occupantDefaults)" in JS_TRANSCRIPT
    assert 'String(occupant).indexOf("human:") === 0' in JS_TRANSCRIPT


# ------------------------------------------------------------------------------- the live script --
def test_the_live_script_merges_in_place_and_never_replaces_the_payload():
    """The merge rule the whole page rests on: push onto ``PAYLOAD.turns``, redraw. Replacing the array (or the
    const) would strand every draw function on the old one."""
    from interlens.arena.live.assets import JS_LIVE
    assert "P.turns.push(t)" in JS_LIVE
    assert "PAYLOAD =" not in JS_LIVE.replace("const P = PAYLOAD", "")
    assert "P.turns =" not in JS_LIVE


def test_the_live_script_subscribes_from_the_rendered_sequence_number():
    """The page renders at a sequence number and subscribes from it, so nothing that happened between the render
    and the attach is lost. EventSource cannot set a header, so the initial position travels as a query
    parameter; the browser's own reconnects use ``Last-Event-ID``."""
    from interlens.arena.live.assets import JS_LIVE
    assert "last_event_id=" in JS_LIVE
    assert "new EventSource" in JS_LIVE


def test_the_live_script_handles_every_event_the_protocol_defines():
    """One handler per event type, read off ``events.EVENT_TYPES`` — so an event added to the protocol and not
    handled here fails a test rather than being silently dropped by the browser."""
    from interlens.arena.live import events
    from interlens.arena.live.assets import JS_LIVE
    handled = set(re.findall(r'SOURCE\.addEventListener\("(\w+)"', JS_LIVE))
    # ``lobby_state`` belongs to the lobby page; the play page is attached to a session that has already started.
    expected = set(events.EVENT_TYPES) - {events.LOBBY_STATE}
    assert not expected - handled, f"unhandled live events: {sorted(expected - handled)}"


def test_a_retried_turn_resynchronises_instead_of_being_merged():
    """A retry retroactively unpublishes the row it superseded — a correction to an EARLIER row that an
    append-only event cannot carry. The client detects the slot collision and re-reads from the server rather
    than patching a transcript it has no renderer for."""
    from interlens.arena.live.assets import JS_LIVE
    assert "function slotTaken(turn)" in JS_LIVE
    assert "if (slotTaken(t)) { resync(" in JS_LIVE
    # Rate-limited across the reload itself — a guard held in a page variable would be wiped by the very thing it
    # limits, which is how a resync becomes a reload loop.
    assert "sessionStorage.setItem(RESYNC_KEY" in JS_LIVE


def test_accept_and_reject_are_gated_from_their_own_lists():
    """Not two halves of one permission: on the forced-final vote an offer can be acceptable and not rejectable.
    Deriving reject from accept — or from the phase string — offers a move the server is about to refuse, which
    costs the player a turn and teaches them the wrong rules."""
    from interlens.arena.live.assets import JS_LIVE
    assert "legal.can_reject || []" in JS_LIVE
    assert "accept.indexOf(id) >= 0, reject.indexOf(id) >= 0" in JS_LIVE


def test_the_dock_draws_a_control_from_every_ratified_capability():
    """Every key of the contract's ``LEGAL_ACTION_DEFAULTS`` is read by the dock.

    Iterated from the constant rather than listed here, so a capability ratified into the protocol and never
    wired to a control fails THIS test instead of shipping as a move the player is silently never offered — the
    exact failure ``can_reject`` was, caught by hand. The fixture's own legal block is held to the same key set,
    so a lane that later synthesizes the event by hand cannot quietly drop one either."""
    from interlens.arena.live import events
    from interlens.arena.live.assets import JS_LIVE
    unread = [key for key in events.LEGAL_ACTION_DEFAULTS if f"legal.{key}" not in JS_LIVE]
    assert not unread, f"capabilities the dock offers no control for: {unread}"


def test_a_talk_turn_cannot_be_submitted_empty():
    """Talk is a PASS carrying a message, so an empty one is not a quiet no-op — the engine reads it as a
    well-formed pass and the player would have said nothing while believing they spoke. The server refuses it;
    the button does not offer it until there is something to say."""
    from interlens.arena.live.assets import JS_LIVE
    assert "const said = Boolean(msg && msg.value.trim());" in JS_LIVE
    assert "btn.disabled = !(open && said && (legal.can_offer || legal.can_pass));" in JS_LIVE
    assert 'msg.addEventListener("input", gateTalk)' in JS_LIVE


def test_the_chart_trajectory_grows_with_the_game():
    """A proposal played live becomes a numbered point on the frontier, from the same four fields
    ``episode_payload`` builds a trajectory entry out of — otherwise the transcript moves and the chart does
    not."""
    from interlens.arena.live.assets import JS_LIVE
    assert "P.trajectory.push({ turn_idx: t.idx, ordinal: P.trajectory.length + 1" in JS_LIVE
