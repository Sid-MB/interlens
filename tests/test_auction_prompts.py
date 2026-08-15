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
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""The transcription-fidelity check for the frozen auction scaffold.

The headline test renders the three worked turn views and asserts they match the committed
``docs/templates/rendered_examples.md`` modulo trailing whitespace. That file is generated from this code, so
the test is a PIN: any later edit to the wording, on either side, breaks it, and a prompt change becomes a
visible protocol change rather than a silent one (design.md §6's prompt freeze)."""
from __future__ import annotations

from pathlib import Path

import pytest

from interlens.arena.scenarios import auction_prompts as P
from interlens.arena.scenarios.auction_examples import EXAMPLES, build_example, render_document

#: The reviewed template set, three levels up from the interlens checkout inside the monorepo. Absent in an
#: installed-package checkout, in which case the pin is skipped rather than failed.
TEMPLATES = (Path(__file__).resolve().parents[3]
             / "experiments/rational_agents/auction/docs/templates")


def _normalized(text: str) -> list[str]:
    """Lines with trailing whitespace stripped and trailing blank lines dropped — the "modulo trivial
    whitespace" the fidelity check allows, and nothing more."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines


@pytest.mark.skipif(not TEMPLATES.exists(), reason="reviewed templates are not in this checkout")
def test_rendered_examples_match_the_committed_document():
    """The three committed turn views are exactly what the scaffold renders from the same draws."""
    committed = (TEMPLATES / "rendered_examples.md").read_text()
    assert _normalized(render_document()) == _normalized(committed)


@pytest.mark.parametrize("cfg", EXAMPLES, ids=[c["key"] for c in EXAMPLES])
def test_every_example_restates_the_deadline_and_asks_once(cfg):
    """Composition invariant 3: stages remaining is restated in every turn view, and the turn closes with the
    single reviewed ask."""
    system, turn = build_example(cfg)
    lines = turn.splitlines()
    assert lines[0].startswith("Turn ") and lines[0].endswith("of this auction.")
    assert lines[2].startswith("## ")
    assert turn.rstrip().endswith("Reply now with one fenced JSON object.")
    assert turn.count("Reply now with one fenced JSON object.") == 1
    if cfg["horizon"] > 1:
        assert "stages remain after this one." in turn or "this is the final stage." in turn


@pytest.mark.parametrize("cfg", EXAMPLES, ids=[c["key"] for c in EXAMPLES])
def test_base_values_appear_in_exactly_one_block(cfg):
    """Composition invariant 2: every number the model needs appears in exactly one place. The catalogue
    carries base values; nothing restates them where two copies could drift."""
    system, turn = build_example(cfg)
    assert "base value" in turn.lower()
    private = turn.split("=== PRIVATE " + P.EMDASH, 1)[1]
    assert "base value" not in private.lower()


@pytest.mark.parametrize("cfg", EXAMPLES, ids=[c["key"] for c in EXAMPLES])
def test_no_strategy_guidance_or_coordination_language(cfg):
    """The register the templates commit to: capabilities are described, uses are never suggested. A prompt
    that invites or forbids coordination measures the prompt, not the propensity (design.md §1)."""
    system, turn = build_example(cfg)
    text = (system + turn).lower()
    for banned in ("collude", "collusion", "cartel", "ring of bidders", "coordinate with",
                   "dominant strategy", "winner's curse", "you should bid", "shade your bid",
                   "we are studying", "you are being evaluated", "monitored"):
        assert banned not in text, f"the scaffold must not say {banned!r}"


def test_silent_rung_states_the_ignored_field_rather_than_omitting_it():
    """The silent block is present rather than omitted, so a model that produces a message field gets a
    deterministic stated outcome instead of silent truncation."""
    sc = P.AuctionPromptScaffold()
    env = sc.envelope(family="sealed_single", channel="silent", dm_cap=2, other_seat_ids=["a"])
    assert "There is no message channel in this auction." in env
    assert '"dm"' not in env.split("Fields:")[0]


def test_channel_ladder_is_nested_in_wording_not_only_in_affordance():
    """Each rung's field list is the rung below plus one section: ``dm`` retains broadcast, and
    ``dm_transfers`` retains both."""
    sc = P.AuctionPromptScaffold()
    kw = dict(family="saa", dm_cap=2, other_seat_ids=["a", "b"])
    broadcast = sc.envelope(channel="broadcast", **kw)
    dm = sc.envelope(channel="dm", **kw)
    transfers = sc.envelope(channel="dm_transfers", **kw)
    message_line = [ln for ln in broadcast.splitlines() if ln.startswith('- `"message"`')][0]
    assert message_line in dm and message_line in transfers
    dm_line = [ln for ln in dm.splitlines() if ln.startswith('- `"dm"`')][0]
    assert dm_line in transfers
    assert '"transfer"' in transfers and '"transfer"' not in dm


def test_ipv_prior_statement_replaces_rather_than_trims():
    """Under IPV a bidder must not be told to read signal into cards that carry none, so the prior statement
    is replaced wholesale and says so in as many words."""
    sc = P.AuctionPromptScaffold()
    ipv = sc.prior_statement(beta=0.0, sigma_z=0.0, sigma_eps=0.18, sigma_nu=0.0, value_structure="ipv",
                             multi_item=False)
    apv = sc.prior_statement(beta=0.40, sigma_z=0.25, sigma_eps=0.18, sigma_nu=0.0, value_structure="apv",
                             multi_item=True)
    assert "carry no information" in ipv
    assert "Fit." not in ipv and "quarter" not in ipv
    assert "Fit." in apv and "adjacency premium" in apv


def test_percentage_hints_are_computed_from_the_constants():
    """The plain-language restatements beside a printed constant are derived at render time, never typed: a
    hand-written copy is exactly the derived-copy-goes-stale failure this program has been bitten by."""
    sc = P.AuctionPromptScaffold()
    at_040 = sc.prior_statement(beta=0.40, sigma_z=0.25, sigma_eps=0.18, sigma_nu=0.0,
                                value_structure="apv", multi_item=False)
    at_020 = sc.prior_statement(beta=0.20, sigma_z=0.10, sigma_eps=0.18, sigma_nu=0.0,
                                value_structure="apv", multi_item=False)
    assert "roughly 49% more" in at_040 and "around 25%" in at_040
    assert "roughly 22% more" in at_020 and "around 10%" in at_020


def test_blurb_and_loadings_are_two_renderings_of_one_vector():
    """The blurb and the printed loading columns are generated from the SAME vector, so they cannot drift."""
    attrs = ("scale", "power_density", "urgency", "latency")
    assert P.lot_blurb((1, 1, 1, 1), attrs) == ("8 MW, high-density racks, delivers next quarter, "
                                                "metro-adjacent")
    assert P.lot_blurb((-1, -1, -1, -1), attrs) == ("2 MW, conventional density, delivers in 24 months, "
                                                    "remote campus")
    assert P.signed(-1) == P.MINUS + "1" and P.signed(0) == "0" and P.signed(1) == "+1"


def test_every_retry_key_renders_and_carries_the_auctioneer_register():
    """Every reviewed retry message renders with plausible slots, opens ``[Auctioneer]``, and closes with the
    one shared line."""
    sc = P.AuctionPromptScaffold()
    slots = dict(parser_error="Expecting ',' delimiter", n_blocks=2, submitted=1, lot_id="L03",
                 legal_actions="`\"bid\"`", missing_field="bids", stage_index=3, lot_id_list="L01, L02",
                 n_entries=2, standing=100, increment=5, floor=105, pass_round=1, open_lot_list="L02",
                 reserve=40, clock_price=160, budget=300, exit_price=120, next_stage=6, committed=200,
                 headroom=100, submitted_total=250, overage=150, n_addressed=3, dm_cap=2,
                 seat_id_list="`ai_lab`", seat_id="ai_lab", n_transfers=2)
    for key in P._RETRIES:
        msg = sc.retry(key, **slots)
        assert msg.startswith("[Auctioneer] ")
        assert msg.endswith("Reply again with one fenced JSON object.")
        assert "{" not in msg.replace('{"', "!").replace('"}', "!"), key
    with pytest.raises(ValueError):
        sc.retry("not_a_reviewed_key")


def test_english_fallback_is_stay_not_exit():
    """A parse failure must not be able to end a seat's stage, because an exit is irrevocable."""
    sc = P.AuctionPromptScaffold()
    assert "staying in at 160" in sc.fallback("english", clock_price=160)
    assert "exiting at 160" in sc.fallback("english_budget", clock_price=160, budget=100)


def test_unreviewed_family_refuses_rather_than_improvising():
    """``uniform_price`` and ``clinching`` sit in the contingent tail with no reviewed prose, so asking for
    them raises instead of inventing text inside the freeze."""
    sc = P.AuctionPromptScaffold()
    with pytest.raises(ValueError):
        sc.format_rules(family="uniform_price", pricing="uniform", n_items=1, increment=1, start_price=0,
                        reserve=0, round_cap=1)


def test_reviewed_constants_are_the_ones_the_prose_prints():
    """The structural constants a bank is frozen at must be the ones the prior statement PRINTS.

    ``arena/auction/spec.py`` carries library defaults of beta 1.0 and sigma_eps 0.20; the reviewed templates
    state 0.40 and 0.18. Both were silently in force at once until the auction-core lane flagged the conflict,
    which meant every seat read a fit premium of 172% while its own draws obeyed 50%. This pins the reviewed
    values and pins them to the rendered prose, so the two cannot drift apart again."""
    from interlens.arena.auction import spec as auction_spec
    assert P.REVIEWED_CONSTANTS == {"beta": 0.40, "sigma_z": 0.25, "sigma_eps": 0.18}
    prose = P.AuctionPromptScaffold().prior_statement(
        sigma_nu=0.0, value_structure="apv", multi_item=True, **P.REVIEWED_CONSTANTS)
    assert "equals **0.40**" in prose
    assert "roughly 49% more" in prose
    assert "a standard deviation of **0.25**" in prose
    assert "a standard deviation of **0.18**" in prose
    # The library defaults are deliberately different; the reviewed value wins and is passed explicitly.
    assert auction_spec.DEFAULT_BETA != P.REVIEWED_CONSTANTS["beta"]
