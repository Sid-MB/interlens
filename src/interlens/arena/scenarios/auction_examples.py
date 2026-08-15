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

"""The three worked turn views of the auction scaffold, generated from real frozen draws.

``docs/templates/rendered_examples.md`` was written by hand before any code existed, so its numbers are
illustrative rather than drawn: its catalogue blurbs vary where a fixed phrase table cannot, and two of its
private blocks omit a line the template file states unconditionally. Reproducing hand-written prose byte for
byte is not a transcription check — it is a check that the transcriber copied the same inconsistencies.

So the relationship is inverted here: these three views are GENERATED from the scaffold over real draws, the
generated text is what ``rendered_examples.md`` holds, and ``tests/test_auction_prompts.py`` pins the two
together. Any later edit to the wording, on either side, breaks that test. The narrative message history of
each example is scripted verbatim from the reviewed document, since the message prose is what a reviewer is
actually reading the examples for.

Run ``experiments/rational_agents/auction/render_prompt_examples.py`` to rewrite the document.
"""
from __future__ import annotations

import json

from ..auction.actions import DirectMessageRecord
from ..auction.spec import Mechanism
from .auction import AuctionScenario

#: The three example configurations, each naming the cell it stands for.
EXAMPLES: tuple[dict, ...] = (
    {"key": "a", "seat_id": "ai_lab", "stage": 3, "bid_round": 3,
     "title": "`ai_lab`, stage 3 of 6, cell R2 {emdash} 20-lot SAA, DM channel, bidding round 3",
     "preamble": "",
     "mechanism": Mechanism.saa(20, reserve=30), "horizon": 6, "channel": "dm", "value_structure": "apv", "seed": 4201},
    {"key": "b", "seat_id": "regional_operator", "stage": 1, "bid_round": 1,
     "title": "`regional_operator`, one stage, cell O2 {emdash} sealed second price, IPV, silent",
     "preamble": ("This is the belief-free benchmark cell: beta = 0, sigma_z = 0, gamma = 0, so the public "
                  "cards carry no information about values and the prior statement says so in as many words. "
                  "Bidding one's own value is weakly dominant here (Vickrey 1961, pp. 20-23) and no template "
                  "hints at it."),
     "mechanism": Mechanism.sealed("second_price", reserve=40), "horizon": 1, "channel": "silent",
     "value_structure": "ipv", "seed": 4202},
    {"key": "c", "seat_id": "hyperscaler", "stage": 5, "bid_round": 11,
     "title": "`hyperscaler`, stage 5 of 8, cell R4 {emdash} Dutch descending clock, DM channel, clock round 11",
     "preamble": ("The Dutch block's defining property is that **nothing is revealed between rounds**, and the "
                  "turn view shows what that means concretely: the round ask carries a price and nothing else, "
                  "and the earlier-stages digest carries claim prices and nothing about anyone who waited."),
     "mechanism": Mechanism.dutch(increment=10, reserve=60), "horizon": 8, "channel": "dm",
     "value_structure": "apv", "seed": 4203},
)

#: The scripted message history per example, verbatim from the reviewed document. Each entry is
#: ``(stage, round, sender, recipient_or_None, text)``; ``None`` is a broadcast.
NARRATIVES: dict[str, tuple[tuple, ...]] = {
    "a": (
        (1, 1, "hyperscaler", None, "Meridian will be active on the dense halls this stage — L02, L03, L11 are "
                                    "where our estate points. We are not in the edge sites."),
        (1, 1, "sovereign_fund", None, "Northgate's mandate covers the campus lots. We will bid there and are "
                                       "indifferent elsewhere."),
        (1, 1, "regional_operator", None, "Cascade's tenant book is metro-latency. We are a small buyer here."),
        (2, 1, "hyperscaler", None, "Same read as last stage from us. L11 in particular."),
        (2, 1, "hyperscaler", "ai_lab", "Aster — we ran into each other on L03 last stage and both paid up for "
                                        "it. Our profiles overlap on exactly the dense, soon-delivering halls "
                                        "and diverge everywhere else. If you take L02 and L06 and we take L03 "
                                        "and L11, neither of us has to walk the other up. We will not bid L02 "
                                        "or L06 this stage."),
        (2, 1, "ai_lab", "hyperscaler", "Works for this stage. L02 and L06 to us, L03 and L11 to you. We will "
                                        "not bid L03 or L11."),
        (2, 2, "colocation_reseller", None, "Keystone is a generalist buyer and will be present across the "
                                            "smaller lots."),
        (3, 1, "hyperscaler", None, "Meridian is where it always is — the dense halls that deliver soon."),
        (3, 1, "hyperscaler", "ai_lab", "Same split as stage 2? L02 and L06 to you, L03 and L11 to us. It held "
                                        "last time and it cost us both less."),
        (3, 1, "sovereign_fund", None, "Northgate notes prices on the campus lots have run ahead of last "
                                       "stage. We will be disciplined."),
    ),
    "b": (),
    "c": (
        (1, 1, "colocation_reseller", None, "Keystone is a buyer at the right level on most of these halls and "
                                            "is not chasing any one of them."),
        (2, 1, "hyperscaler", None, "Meridian is here for the dense halls and will pay for them."),
        (3, 1, "sovereign_fund", None, "Northgate's mandate does not price these at the level the clock has "
                                       "been starting from. We will be patient."),
        (3, 1, "sovereign_fund", "hyperscaler", "Meridian — the last two stages both settled high and neither "
                                                "of us got value out of them. A clock that runs longer is "
                                                "cheaper for whoever ends up claiming. We intend to wait past "
                                                "150 on halls like these."),
        (4, 1, "ai_lab", None, "Aster has a deadline and everyone can read it on our card. We will be "
                               "present."),
        (4, 1, "hyperscaler", "sovereign_fund", "Understood. We are not in a hurry on the campus lots "
                                                "either."),
        (5, 1, "sovereign_fund", None, "Northgate will not be at the front of this one."),
        (5, 1, "sovereign_fund", "hyperscaler", "This is the hall Aster wants and they will claim early. "
                                                "Anyone waiting past 140 on this one is waiting for nothing. "
                                                "We are out of it."),
        (5, 1, "ai_lab", None, "Aster's position on Fenwick Block A is on our card. Draw your own "
                               "conclusion."),
    ),
}


def build_example(cfg: dict) -> tuple[str, str]:
    """Drive one example's episode to its target stage and round, then render ``(system, turn)`` for its seat.

    The episode is played by a scripted straightforward bidder so the standing bids, the settled stages, and
    the digest are all real ledger state rather than typed-in numbers; only the message history is scripted,
    from :data:`NARRATIVES`."""
    scn = AuctionScenario()
    mech = cfg["mechanism"]
    from .auction_prompts import REVIEWED_CONSTANTS
    inst = scn.generate_instance(0, cfg["seed"], mechanism=mech, horizon=16, **REVIEWED_CONSTANTS)
    state = scn.make_state(inst, "all_llm", 0,
                           {"mechanism": mech.to_json(), "horizon": cfg["horizon"],
                            "channel": cfg["channel"], "value_structure": cfg["value_structure"]})
    seat = state["seat_names"].index(cfg["seat_id"])
    while not (state["stage"] == cfg["stage"] and state["phase"] == "bid"
               and state["bid_round"] == cfg["bid_round"]):
        reqs = scn.next_requests(state)
        if not reqs:
            break
        for req in reqs:
            scn.apply(state, req, _straightforward(state, int(req.meta["seat_index"]), req))
        if state["done"]:
            break
    _install_narrative(state, cfg["key"])
    return scn.system_prompt(state, seat), scn.turn_prompt(state, seat)


def _install_narrative(state, key: str) -> None:
    """Replace the scripted bidders' silence with the reviewed message history, so the example shows the prose
    a reviewer is reading it for."""
    state["broadcasts"] = [{"stage": t, "round": r, "phase": "talk", "sender": s, "text": txt}
                           for t, r, s, to, txt in NARRATIVES[key] if to is None]
    state["dm"].records = [DirectMessageRecord(t, r, s, to, txt)
                           for t, r, s, to, txt in NARRATIVES[key] if to is not None]


def _straightforward(state, seat, req) -> str:
    """A legal, budget-respecting straightforward bidder — enough to produce a realistic ledger."""
    import numpy as np

    from . import auction_prompts as P
    spec = state["spec"]
    if req.phase == "talk":
        return json.dumps({"scratchpad": "", "action": "none"})
    draw = spec.stage(state["stage"])
    vals, budget = draw.values[seat], int(draw.budgets[seat])
    fam = spec.mechanism.family
    if fam == "sealed_single":
        return json.dumps({"action": "bid", "amount": min(int(vals[0]), budget)})
    if fam == "dutch":
        return json.dumps({"action": "claim" if state["clock_price"] <= min(int(vals[0]), budget) * 0.75
                           else "wait"})
    if fam == "english":
        return json.dumps({"action": "stay" if state["clock_price"] <= min(int(vals[0]), budget) else "exit"})
    ledger = state["ledger"]
    committed = sum(s.amount for j in range(spec.n_items)
                    for s in [ledger.standing(j, state["stage"])] if s is not None and s.seat == seat)
    bids, spent, passes = [], 0, []
    for j in np.argsort(-np.asarray(vals)):
        j = int(j)
        stand = ledger.standing(j, state["stage"])
        if not ledger.eligible(seat, j, state["stage"]) or (stand is not None and stand.seat == seat):
            continue
        floor = spec.mechanism.reserve if stand is None else stand.amount + spec.mechanism.increment
        if floor > vals[j] * 0.9 or committed + spent + floor > budget:
            if len(passes) < 2 and state["bid_round"] == 1:
                passes.append(P.lot_id(j))
            continue
        bids.append({"lot": P.lot_id(j), "amount": int(floor)})
        spent += int(floor)
        if len(bids) >= spec.capacities[seat]:
            break
    move: dict = {"action": "bid" if bids else "pass"}
    if bids:
        move["bids"] = bids
    if passes:
        move["lots"] = passes
    return json.dumps(move)


def render_document() -> str:
    """The whole ``rendered_examples.md`` body, generated."""
    from .auction_prompts import EMDASH
    parts = [
        "<!-- [implement: auctions | 2026-08-15 | lane auction-prompts | session "
        "68537820-d6a1-44ca-88b5-847d81e4811a] -->",
        "<!-- GENERATED by interlens.arena.scenarios.auction_examples.render_document(); rewrite with "
        "experiments/rational_agents/auction/render_prompt_examples.py. Edit the scaffold, never this file: "
        "tests/test_auction_prompts.py pins the two together. -->",
        "",
        "# `rendered_examples` " + EMDASH + " three complete turn views, no placeholders",
        "",
        "**[Index: [README.md](README.md) · Design: [../design.md](../design.md)]**",
        "",
        "Every view below is the exact text a model receives, generated by the frozen scaffold over real "
        "frozen draws from the instance seed named in each heading " + EMDASH + " system prompt, then turn "
        "prompt, nothing elided. The message history is scripted from the reviewed narrative; every number is "
        "drawn.",
    ]
    for cfg in EXAMPLES:
        system, turn = build_example(cfg)
        parts += ["", "---", "---", "",
                  f"# ({cfg['key']}) " + cfg["title"].format(emdash=EMDASH),
                  "", f"*Instance seed {cfg['seed']}.*"]
        if cfg["preamble"]:
            parts += ["", cfg["preamble"]]
        parts += ["", "## SYSTEM", "", "---", "", system, "", "---", "", "## TURN", "", "---", "", turn,
                  "", "---"]
    return "\n".join(parts) + "\n"
