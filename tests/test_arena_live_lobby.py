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
# [implement: live-play/laneC] 2026-08-16
# [implement: live-play/lobby-defaults] 2026-08-19
"""Tests for the live-play lobby page (``arena/live/lobby_page.py`` + ``assets/js_lobby.py``).

No browser: the lobby renders every control in Python, so the assertions are on real structure in the emitted
document — that each picker exists, that an unavailable model is present-but-disabled rather than missing, that
a model with one thinking mode is not offered a second, and that a computable seat's prose box is greyed.

Two of these are worth more than they look:

**The field-name round trip.** A seat control carries the ``SeatConfig`` field it edits as ``data-field``, and
the browser layer looks controls up by that attribute. Three copies of the same names therefore exist — the
dataclass, the markup, and the JS map — and the test pins all three to each other, so renaming a field fails
here instead of silently editing nothing in a browser.

**Self-containment.** The page is served off a cluster node behind a firewall and read over ``ssh -L``; one
stylesheet from a CDN and the lobby is unusable. Asserted as "no external reference of any kind", not as a
spot-check of the tags this version happens to emit.
"""
from __future__ import annotations

import dataclasses
import json
import re

import pytest

from interlens.arena.live import events
from interlens.arena.live.assets.js_lobby import JS_LOBBY, JS_LOBBY_PAGE
from interlens.arena.live.lobby_page import _notices, _problems, render_lobby_html
from interlens.arena.live.provider import (SEAT_KINDS, THINKING_PREFERENCE, BankInfo, ModelInfo, SeatConfig,
                                           default_model_id, default_thinking)

# A model per interesting capability shape: a metered hosted model that CANNOT turn thinking off (the Claude-5
# constraint the lobby exists to respect), a free local model that is currently unusable, an ordinary one, and
# the one the provider flags as what a new model seat should open on.
FABLE = ModelInfo("claude-fable-5", "Fable 5", "anthropic", thinking_modes=("on",), supports_temperature=False)
QWEN = ModelInfo("Qwen/Qwen3-8B", "Qwen3 8B", "local", thinking_modes=("off", "on"), available=False,
                 unavailable_reason="no GPU is visible on this host", metered=False)
HAIKU = ModelInfo("claude-haiku-4-5-20251001", "Haiku 4.5", "anthropic", thinking_modes=("off", "on"))
OPUS = ModelInfo("claude-opus-5", "Opus 5", "anthropic", thinking_modes=("off", "auto", "on"),
                 supports_temperature=False, default=True)

BANK = BankInfo("instances_realistic_demo", "Realistic demo", ("dc-01", "dc-02", "dc-03"), 4,
                "three data-center procurement games")


def _state(seats=None, **over) -> dict:
    """A representative lobby state: one bank, one framing, three models, and a four-seat lineup covering an
    LLM seat, a rational seat, an oracle seat and a human seat."""
    seats = seats if seats is not None else [
        SeatConfig(kind="llm", model_id=FABLE.model_id, thinking="on"),
        SeatConfig(kind="rational", policy="bayes-rational"),
        SeatConfig(kind="oracle", policy="bayes-rational", instructions="ignored by a policy"),
        SeatConfig(kind="human", display_name="Sid"),
    ]
    state = {
        "banks": [BANK.to_json()],
        "framings": [{"framing_id": "datacenter_realistic", "label": "Data center",
                      "description": "a procurement between two operators"}],
        "models": [FABLE.to_json(), QWEN.to_json(), HAIKU.to_json(), OPUS.to_json()],
        "policies": ["bayes-rational", "hardball"],
        "seat_names": ["Avery", "Blake", "Casey", "Devon"],
        "bank": BANK.bank_id,
        "framing": "datacenter_realistic",
        "instance_id": "",
        "seats": [s.to_json() if isinstance(s, SeatConfig) else s for s in seats],
        "budget_usd": 2.0,
        "running": False,
        "sid": None,
        "error": "",
    }
    state.update(over)
    return state


def _card(html: str, idx: int) -> str:
    """The markup of one seat card, sliced out of the page so a per-seat assertion cannot accidentally be
    satisfied by another seat's card."""
    start = html.index(f"<div class='seatcard' data-seat='{idx}'")
    end = html.index("<div class='seatcard'", start + 1) if f"<div class='seatcard' data-seat='{idx + 1}'" in html \
        else html.index("</div></section>", start)
    return html[start:end]


def _select_of(card: str, field: str) -> str:
    """One seat control's markup — a ``select``/``textarea`` through its closing tag, an ``input`` through its
    own, so an option list is never truncated at the opening tag."""
    for pattern in (rf"<select[^>]*data-field='{field}'.*?</select>",
                    rf"<textarea[^>]*data-field='{field}'.*?</textarea>",
                    rf"<input[^>]*data-field='{field}'[^>]*>"):
        m = re.search(pattern, card, re.S)
        if m:
            return m.group(0)
    raise AssertionError(f"no control for {field}")


# ------------------------------------------------------------------------------------------ pickers --
def test_game_pickers_and_budget_are_present():
    """Bank, framing and instance pickers, each populated, plus the budget field."""
    html = render_lobby_html(_state())
    assert "id='lobby-bank'" in html and "id='lobby-framing'" in html and "id='lobby-instance'" in html
    assert "id='lobby-budget'" in html
    assert "Realistic demo (3 instances)" in html
    assert "Data center" in html
    for iid in BANK.instance_ids:
        assert f'value="{iid}"' in html
    # An unnamed instance is a legitimate choice: prepare() reads "" as "choose one".
    assert "random — let the provider choose" in html


def test_instance_options_follow_the_selected_bank():
    """A second bank's instances are NOT offered while the first is selected — the picker is per bank."""
    other = BankInfo("instances_other", "Other", ("xx-99",), 2, "")
    html = render_lobby_html(_state(banks=[BANK.to_json(), other.to_json()]))
    assert 'value="dc-01"' in html
    assert 'value="xx-99"' not in html


def test_budget_is_required_only_when_a_metered_seat_is_present():
    """The cap is what stands between a click and an unbounded bill, so it is required exactly when some seat
    costs money — and not required when the lineup is all policies and people."""
    metered = render_lobby_html(_state())
    assert "required" in metered.split("id='lobby-budget'")[1].split(">")[0]
    assert "required: a metered model is seated" in metered

    free = render_lobby_html(_state(seats=[SeatConfig(kind="rational", policy="bayes-rational"),
                                           SeatConfig(kind="human", display_name="Sid")]))
    assert "required" not in free.split("id='lobby-budget'")[1].split(">")[0]
    assert "no metered seat" in free


# --------------------------------------------------------------------------------------- seat cards --
def test_one_card_per_party_named_in_seat_order():
    html = render_lobby_html(_state())
    assert html.count("class='seatcard'") == 4
    for i, name in enumerate(["Avery", "Blake", "Casey", "Devon"]):
        assert f'data-seat=\'{i}\' data-seat-name="{name}"' in html


def test_every_seat_kind_is_offered():
    card = _card(render_lobby_html(_state()), 0)
    kinds = re.findall(r'<option value="(\w+)"', _select_of(card, "kind"))
    assert kinds == list(SEAT_KINDS)


def test_a_server_that_narrows_the_seat_kinds_narrows_the_picker():
    """``seat_kinds`` lets a deployment drop a kind it will not build; the picker must not offer it anyway."""
    card = _card(render_lobby_html(_state(seat_kinds=["llm", "human"])), 0)
    assert re.findall(r'<option value="(\w+)"', _select_of(card, "kind")) == ["llm", "human"]


def test_unavailable_model_is_greyed_not_omitted_and_says_why():
    """A model that vanishes from the list reads as a model that does not exist; the reason is usually the fix."""
    card = _card(render_lobby_html(_state()), 0)
    models = _select_of(card, "model_id")
    assert QWEN.model_id in models
    option = re.search(rf'<option value="{re.escape(QWEN.model_id)}"[^>]*>[^<]*</option>', models).group(0)
    assert "disabled" in option
    assert "no GPU is visible on this host" in option
    # The available models are pickable.
    assert "disabled" not in re.search(rf'<option value="{FABLE.model_id}"[^>]*>', models).group(0)


def test_thinking_offers_only_the_modes_the_model_accepts():
    """Fable cannot disable thinking, so the lobby must not offer an "off" that would 400 mid-game."""
    html = render_lobby_html(_state())
    fable_modes = re.findall(r'<option value="(\w+)"', _select_of(_card(html, 0), "thinking"))
    assert fable_modes == ["on"]
    assert "this model has one thinking mode" in _card(html, 0)

    on_haiku = render_lobby_html(_state(seats=[SeatConfig(kind="llm", model_id=HAIKU.model_id)]))
    assert re.findall(r'<option value="(\w+)"', _select_of(_card(on_haiku, 0), "thinking")) == ["off", "on"]


# ------------------------------------------------------------------------------------- the defaults --
def test_a_new_model_seat_opens_on_the_flagged_model_with_thinking_on():
    """The two defaults a live operator should never have to set: the provider's flagged model, and the best
    thinking mode that model accepts. An unconfigured card must show both as SELECTED, not merely offer them."""
    card = _card(render_lobby_html(_state(seats=[SeatConfig(kind="llm")])), 0)
    assert f'<option value="{OPUS.model_id}" selected' in _select_of(card, "model_id")
    assert '<option value="on" selected' in _select_of(card, "thinking")


def test_the_default_model_is_the_providers_flag_not_the_head_of_the_list():
    """No model id is spelled in the page: which one is default travels on ``ModelInfo.default``. A flagged model
    that cannot be used loses to one that can — pre-selecting a seat that would fail at start helps nobody — but
    wins when nothing at all is usable, so the lobby still opens on the right name and its reason."""
    assert default_model_id([FABLE, QWEN, HAIKU, OPUS]) == OPUS.model_id
    assert default_model_id([FABLE, HAIKU]) == FABLE.model_id           # nothing flagged: the first usable one
    assert default_model_id([QWEN, HAIKU]) == HAIKU.model_id            # the unavailable one is skipped
    gone = dataclasses.replace(OPUS, available=False, unavailable_reason="no key")
    assert default_model_id([gone, HAIKU]) == HAIKU.model_id
    assert default_model_id([gone, dataclasses.replace(QWEN, default=False)]) == gone.model_id
    assert default_model_id([]) == ""
    # And it reads the wire dicts the page renders from as happily as the objects the session validates against.
    assert default_model_id([m.to_json() for m in (FABLE, OPUS)]) == OPUS.model_id


@pytest.mark.parametrize("modes,expected", [
    (("off", "auto", "on"), "on"),        # the explicit adaptive request, so the episode records its condition
    (("off", "auto"), "auto"),            # Haiku: refuses the explicit request, so its best "on" is the default
    (("auto", "on"), "on"),               # Fable: cannot turn thinking off at all
    (("off",), "off"),                    # a model with nothing else stays off
    ((), "off"),
])
def test_thinking_defaults_to_the_best_mode_the_model_actually_accepts(modes, expected):
    assert default_thinking(ModelInfo("m", "M", "p", thinking_modes=modes)) == expected
    assert default_thinking({"model_id": "m", "thinking_modes": list(modes)}) == expected


def test_an_unset_seat_resolves_to_exactly_what_the_card_shows():
    """The page and the server resolve defaults through the same two functions, so a seat POSTed bare becomes the
    seat the operator was looking at. A mode chosen by hand — including ``off`` — survives resolution."""
    models = [FABLE, QWEN, HAIKU, OPUS]
    assert SeatConfig(kind="llm").resolved(models) == SeatConfig(kind="llm", model_id=OPUS.model_id, thinking="on")
    assert SeatConfig(kind="llm", model_id=HAIKU.model_id).resolved(models).thinking == "on"
    off = SeatConfig(kind="llm", model_id=HAIKU.model_id, thinking="off")
    assert off.resolved(models) is off                                  # deliberate, and idempotent
    policy = SeatConfig(kind="rational", policy="bayes-rational")
    assert policy.resolved(models) is policy                            # a policy has no model to default


def test_thinking_defaults_do_not_offer_a_mode_the_model_rejects():
    """Fable has no ``off``; the default must be one of the modes on the card, never a mode invented for it."""
    card = _card(render_lobby_html(_state(seats=[SeatConfig(kind="llm", model_id=FABLE.model_id)])), 0)
    offered = re.findall(r'<option value="(\w+)"', _select_of(card, "thinking"))
    selected = re.search(r'<option value="(\w+)" selected', _select_of(card, "thinking")).group(1)
    assert offered == ["on"] and selected == "on"


# -------------------------------------------------------------------------------------- shuffle bar --
def test_the_shuffle_button_says_what_the_last_shuffle_did():
    """Who plays which party is an experimental variable — the proposer order rotates from the proposer base —
    so the page shows the applied permutation in the seats' own names rather than only scrambling the cards."""
    html = render_lobby_html(_state(last_shuffle=[2, 0, 1, 3]))
    assert "id='lobby-shuffle'" in html and "Shuffle seats" in html
    note = html.split("id='lobby-shuffle-note'>")[1].split("</span>")[0]
    assert note == "last shuffle: Avery ← Casey, Blake ← Avery, Casey ← Blake"     # Devon did not move
    assert "who plays which party is as you set it" in render_lobby_html(_state())
    assert "left the lineup unchanged" in render_lobby_html(_state(last_shuffle=[0, 1, 2, 3]))


def test_the_shuffle_button_asks_the_server_to_permute():
    """The permutation happens server-side so it can be recorded on the game that gets played; the button is a
    one-key POST and the page re-renders from the answer, so there is no second shuffle implementation."""
    body = re.search(r"async function shuffleSeats\(\) \{(.*?)\n\}", JS_LOBBY, re.S).group(1)
    assert 'JSON.stringify({ shuffle: true })' in body
    assert "applyState(body)" in body
    assert "Math.random" not in JS_LOBBY, "the lineup is permuted by the server, not by the browser"


# -------------------------------------------------------------------------------- all model seats row --
def test_the_all_seats_row_offers_the_same_choices_a_card_does():
    """One row configures the whole lineup, so it must not be able to express a seat a card could not."""
    html = render_lobby_html(_state())
    row = html.split("<div class='allseats'")[1].split("<div class='seatgrid'")[0]
    assert f'<option value="{OPUS.model_id}" selected' in row          # same default as a fresh card
    assert '<option value="on" selected' in row
    for field in ("model_id", "thinking", "instructions"):
        assert f"data-all='{field}'" in row
    assert "id='lobby-apply-all'" in row and "id='lobby-all-include'" in row
    assert "id='lobby-all-count'" in row
    # It says what Apply does, because a bulk write nobody can predict is worse than five dropdowns.
    assert "overwrites the model and thinking mode" in row
    assert "only when non-empty" in row


def test_the_all_seats_row_counts_the_seats_it_would_touch():
    """The pill is the "how many will this hit" the operator needs before pressing a bulk button."""
    html = render_lobby_html(_state())                                  # one llm seat of four
    assert "id='lobby-all-count'>1 model seat<" in html
    every = render_lobby_html(_state(seats=[SeatConfig(kind="llm", model_id=HAIKU.model_id)] * 3))
    assert "id='lobby-all-count'>3 model seats<" in every
    # And the browser rewrites the whole phrase, so the count cannot drift from its noun.
    assert '"lobby-all-count", n + " model seat"' in JS_LOBBY


def test_the_shared_instruction_box_starts_empty_rather_than_mirroring_a_seat():
    """It is a thing to send, not a view of any seat: populating it from one card would make Apply quietly
    rewrite the other cards with that card's persona."""
    seats = [SeatConfig(kind="llm", model_id=HAIKU.model_id, instructions="only Avery knows this")]
    row = render_lobby_html(_state(seats=seats)).split("<div class='allseats'")[1].split("<div class='seatgrid'")[0]
    assert "id='lobby-all-instructions' data-all='instructions' rows='2'" in row
    assert "only Avery knows this" not in row


def test_model_controls_are_disabled_off_an_llm_seat():
    """The controls stay in the document so the card's shape never changes as a kind is cycled."""
    card = _card(render_lobby_html(_state()), 1)          # a rational seat
    assert "disabled" in _select_of(card, "model_id")
    assert "disabled" in _select_of(card, "thinking")
    assert "disabled" not in _select_of(card, "policy")
    assert "class='field off' data-field-for='model_id'" in card


def test_instructions_are_greyed_for_computable_seats_only():
    """A policy reads no prose, so the override box is greyed for rational/oracle seats and live everywhere else."""
    html = render_lobby_html(_state())
    for idx in (1, 2):
        card = _card(html, idx)
        assert "disabled" in _select_of(card, "instructions")
        assert "class='field off' data-field-for='instructions'" in card
        assert "a policy reads no prose" in card
    for idx in (0, 3):
        assert "disabled" not in _select_of(_card(html, idx), "instructions")


def test_policy_picker_is_populated_and_disabled_for_non_computable_seats():
    html = render_lobby_html(_state())
    oracle = _select_of(_card(html, 2), "policy")
    assert 'value="bayes-rational"' in oracle and 'value="hardball"' in oracle
    assert "disabled" in _select_of(_card(html, 0), "policy")


def test_a_human_seat_names_the_label_it_gets_without_a_name():
    """Derived from ``SeatConfig`` rather than spelled out, so the lobby cannot promise a label the router does
    not stamp."""
    html = render_lobby_html(_state())
    assert SeatConfig(kind="human").occupant_label() in _card(html, 3)
    assert "optional occupant label" in _card(html, 0)


# ------------------------------------------------------------------------------------- can it start --
def test_a_human_seat_without_a_name_is_a_notice_not_a_blocker():
    """The server ACCEPTS a nameless human seat and records it under a default label, so the lobby says which
    label rather than refusing — a front end that forbids what its back end allows is the failure mode here."""
    state = _state(seats=[SeatConfig(kind="human"), SeatConfig(kind="rational", policy="bayes-rational")])
    html = render_lobby_html(state)
    assert "disabled" not in html.split("id='lobby-start'")[1].split(">")[0]
    assert _problems(state) == []
    assert _notices(state) == [f"Seat 0 (Avery) has no display name — the transcript will record it as "
                               f"{SeatConfig(kind='human').occupant_label()}."]
    assert "id='lobby-notices'" in html and "has no display name" in html


def test_a_metered_seat_without_a_cap_blocks_the_start_button():
    html = render_lobby_html(_state(budget_usd=None))
    assert "disabled" in html.split("id='lobby-start'")[1].split(">")[0]
    assert "A budget cap above $0 is required" in html


def test_a_valid_lineup_leaves_start_live():
    html = render_lobby_html(_state())
    assert "disabled" not in html.split("id='lobby-start'")[1].split(">")[0]
    assert _problems(_state()) == []


def test_no_banks_degrades_to_an_explanation_rather_than_an_exception():
    """A lobby that 500s is a lobby nobody can use to fix the configuration that broke it."""
    html = render_lobby_html({"banks": [], "seats": []})
    assert "offers no instance banks" in html
    assert "No seats yet" in html
    assert "disabled" in html.split("id='lobby-start'")[1].split(">")[0]


def test_a_running_session_offers_the_live_page_and_an_end_button():
    html = render_lobby_html(_state(running=True, sid="s1", phase="running"))
    assert "A session is already running" in html
    assert "href='/play'" in html and "id='lobby-reset'" in html


# ------------------------------------------------------------------------------- the JS/HTML contract --
def _js_list(name: str) -> list[str]:
    """One of the browser layer's field-name arrays, read out of the script source."""
    m = re.search(rf"const {name} = \[(.*?)\];", JS_LOBBY, re.S)
    assert m, f"{name} is not declared in JS_LOBBY"
    return re.findall(r'"([^"]+)"', m.group(1))


def test_seat_field_names_round_trip_between_the_dataclass_the_markup_and_the_script():
    """The three copies of a seat's field names are pinned to each other, so a rename fails a test rather than
    silently editing nothing in the browser."""
    declared = {f.name for f in dataclasses.fields(SeatConfig)}
    js = _js_list("SEAT_FIELDS")
    assert set(js) == declared
    card = _card(render_lobby_html(_state()), 0)
    assert set(re.findall(r"data-field='(\w+)'", card)) == declared
    assert set(re.findall(r"data-field-for='(\w+)'", card)) == declared


def test_lobby_field_names_match_the_keys_the_page_renders_from():
    js = _js_list("LOBBY_FIELDS")
    assert js == ["bank", "framing", "instance_id", "budget_usd"]
    html = render_lobby_html(_state())
    for key in js:
        assert f"data-lobby='{key}'" in html


def test_the_kinds_the_script_greys_match_the_page():
    """The browser re-applies the greying rules on every edit; it must grey the same set the server rendered."""
    from interlens.arena.live.lobby_page import NO_INSTRUCTION_KINDS
    assert _js_list("NO_INSTRUCTION_KINDS") == list(NO_INSTRUCTION_KINDS)
    assert _js_list("POLICY_KINDS") == ["rational", "oracle"]
    assert set(_js_list("POLICY_KINDS")) <= set(SEAT_KINDS)


def test_the_script_mirrors_the_thinking_preference_rather_than_choosing_its_own():
    """Which mode a seat defaults to is decided in ``provider.THINKING_PREFERENCE``; the browser re-applies it
    when a model changes, so the two orders must be the same order."""
    assert _js_list("THINKING_PREFERENCE") == list(THINKING_PREFERENCE)
    assert "defaultThinking" in JS_LOBBY and "defaultModelId" in JS_LOBBY
    # The flag, not a model id: nothing in the browser layer may name anybody's favourite model.
    assert "claude" not in JS_LOBBY.lower()
    assert "m.default" in JS_LOBBY


def test_the_all_seats_row_writes_only_fields_a_seat_has():
    """``data-all`` names the ``SeatConfig`` field it will write, so the bulk row cannot invent a field the cards
    and the server do not share."""
    all_fields = _js_list("ALL_FIELDS")
    assert set(all_fields) < {f.name for f in dataclasses.fields(SeatConfig)}
    assert set(all_fields) == {"model_id", "thinking", "instructions"}
    html = render_lobby_html(_state())
    for field in all_fields:
        assert f"data-all='{field}'" in html


def test_apply_all_overwrites_the_lineup_and_leaves_the_wire_shape_alone():
    """The bulk row is a client-side write followed by the ordinary whole-seats POST: it must reach for ``push``
    rather than a route of its own, or the server would grow a second way to configure a lineup."""
    body = re.search(r"function applyAll\(\) \{(.*?)\n\}", JS_LOBBY, re.S).group(1)
    assert "seat.model_id = model_id" in body and "seat.thinking = thinking" in body
    assert "instructions.trim()" in body                 # empty box leaves per-seat prose alone
    assert 'seat.kind = "llm"' in body and "include" in body
    assert "push()" in body and "fetch(" not in body


def test_the_script_keeps_blockers_and_notices_apart_the_same_way_the_page_does():
    """``validate`` is what disables Start, ``notices`` is what merely says something. The display-name case
    must sit in the second: the server accepts it, so blocking on it would make the lobby stricter than the
    thing it is a front end for."""
    blocking = re.search(r"function validate\(\) \{(.*?)\n\}", JS_LOBBY, re.S).group(1)
    informational = re.search(r"function notices\(\) \{(.*?)\n\}", JS_LOBBY, re.S).group(1)
    assert "display_name" not in blocking
    assert "display_name" in informational
    assert "budget cap" in blocking


def test_the_script_mirrors_event_names_rather_than_inventing_them():
    for name in (events.LOBBY_STATE, events.EPISODE_STARTED, events.ERROR):
        assert f'{name}: "{name}"' in JS_LOBBY
    # And the routes are the plan's, spelled once.
    for route in ("/api/lobby", "/api/start", "/api/reset", "/play", "/api/session/"):
        assert route in JS_LOBBY


def test_the_bundle_carries_the_shared_shell():
    """Composed like ``JS_INDEX_PAGE``: the shell's theme toggle and keyboard help, none of the episode layers."""
    assert "function registerKeys" in JS_LOBBY_PAGE          # from viz.assets.JS_SHELL
    assert "const E = (s)" in JS_LOBBY_PAGE                  # from viz.assets.JS_UTIL
    assert JS_LOBBY in JS_LOBBY_PAGE
    assert "frontierChart" not in JS_LOBBY_PAGE              # no chart layer on a page with no payload


# ------------------------------------------------------------------------------------ the document --
def test_the_state_travels_as_an_inert_json_tag_and_round_trips():
    state = _state()
    html = render_lobby_html(state)
    body = html.split('<script type="application/json" id="lobby-state">')[1].split("</script>")[0]
    assert json.loads(body.replace("<\\/", "</")) == state


def test_a_closing_tag_inside_the_state_cannot_end_the_script():
    """Data in a data position: the one thing that could break out of the tag is escaped."""
    hostile = _state(seats=[SeatConfig(kind="llm", model_id=FABLE.model_id,
                                       instructions="</script><script>alert(1)</script>")])
    html = render_lobby_html(hostile)
    tag = html.split('id="lobby-state">')[1].split("</script>")[0]
    assert "</script>" not in tag and "<\\/script>" in tag   # the only sequence that could end the tag is escaped
    assert json.loads(tag.replace("<\\/", "</"))["seats"][0]["instructions"].endswith("</script>")
    # And the same text in the textarea is escaped rather than parsed as markup.
    assert "&lt;/script&gt;&lt;script&gt;alert(1)" in html


def test_the_page_is_self_contained():
    """Served off a firewalled node and read over ``ssh -L``: one CDN reference and the lobby is unusable."""
    html = render_lobby_html(_state())
    assert html.startswith("<!doctype html>")
    assert "<style>" in html and "<script>" in html
    assert not re.search(r"""(src\s*=|<link\b|@import|https?://(?!www\.gnu))""", html)


def test_it_renders_from_the_state_the_server_actually_hands_over():
    """The fixtures above are hand-built, which is exactly how a page keeps passing its own tests while
    disagreeing with the server. This one renders from a real ``SessionManager.lobby_state()`` — the same object
    ``GET /api/lobby`` returns — so a key the session renames is caught here rather than in a browser."""
    from .test_arena_live_session import make_manager

    import tempfile
    from pathlib import Path

    manager = make_manager(Path(tempfile.mkdtemp()))
    state = manager.lobby_state()
    html = render_lobby_html(state)
    assert html.startswith("<!doctype html>")
    assert html.count("class='seatcard'") == len(state["seats"])
    # The opening lineup is all computable seats, so the first click is free: nothing blocks it.
    assert _problems(state) == [] and _notices(state) == []
    # An unavailable model is listed with its reason rather than omitted.
    gone = next(m for m in state["models"] if not m["available"])
    assert gone["unavailable_reason"] in html

    # And a lineup that violates both rules produces one blocker and one notice, not two of either.
    metered = next(m for m in state["models"] if m["available"] and m["metered"])
    manager.update_lobby({"seats": [SeatConfig(kind="human").to_json(),
                                    SeatConfig(kind="llm", model_id=metered["model_id"]).to_json(),
                                    SeatConfig(kind="oracle", policy="bayes-rational").to_json()],
                          "budget_usd": None})
    edited = manager.lobby_state()
    assert _problems(edited) == ["A budget cap above $0 is required while a metered model is seated."]
    assert len(_notices(edited)) == 1 and "human:player" in _notices(edited)[0]
    assert "disabled" in render_lobby_html(edited).split("id='lobby-start'")[1].split(">")[0]


def test_every_label_points_at_a_control_that_exists():
    """A ``for`` that names nothing is a label a screen reader cannot attach and a click that does not focus."""
    html = render_lobby_html(_state())
    ids = set(re.findall(r"id='([\w-]+)'", html))
    for target in re.findall(r"<label for='([\w-]+)'>", html):
        assert target in ids, f"label points at a missing control: {target}"


@pytest.mark.parametrize("state", [{}, {"seats": []}, {"banks": [BANK.to_json()], "seats": [{}]}])
def test_a_thin_state_still_renders(state):
    """Every key is read defensively — a state written before a key existed must not take the lobby down."""
    html = render_lobby_html(state)
    assert html.startswith("<!doctype html>") and "Live play" in html
