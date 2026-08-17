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
from interlens.arena.live.lobby_page import _problems, render_lobby_html
from interlens.arena.live.provider import SEAT_KINDS, BankInfo, ModelInfo, SeatConfig

# A model per interesting capability shape: a metered hosted model that CANNOT turn thinking off (the Claude-5
# constraint the lobby exists to respect), a free local model that is currently unusable, and an ordinary one.
FABLE = ModelInfo("claude-fable-5", "Fable 5", "anthropic", thinking_modes=("on",), supports_temperature=False)
QWEN = ModelInfo("Qwen/Qwen3-8B", "Qwen3 8B", "local", thinking_modes=("off", "on"), available=False,
                 unavailable_reason="no GPU is visible on this host", metered=False)
HAIKU = ModelInfo("claude-haiku-4-5-20251001", "Haiku 4.5", "anthropic", thinking_modes=("off", "on"))

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
        "models": [FABLE.to_json(), QWEN.to_json(), HAIKU.to_json()],
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


def test_display_name_is_marked_required_on_a_human_seat():
    html = render_lobby_html(_state())
    assert "required — the transcript calls you this" in _card(html, 3)
    assert "optional occupant label" in _card(html, 0)


# ------------------------------------------------------------------------------------- can it start --
def test_a_human_seat_without_a_name_blocks_the_start_button():
    html = render_lobby_html(_state(seats=[SeatConfig(kind="human"),
                                           SeatConfig(kind="rational", policy="bayes-rational")]))
    assert "id='lobby-start' class='primary' type='button' disabled" in html
    assert "needs a display name" in html


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
