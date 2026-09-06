# `auction`

Module `interlens.arena.scenarios.auction`

Repeated multi-bidder auctions as one :class:`~interlens.arena.scenario.Scenario`.

An episode is `T` auction stages played by the same five bidders over one frozen
:class:`~interlens.arena.auction.spec.AuctionSpec`. **Formats are mechanism configs and repetition is the
horizon; neither forks a runner** — the failure mode that rule prevents (divergent per-format runners drifting
apart) is exactly what a format x channel x horizon factorial cannot survive.

The stage loop (design.md §3.1):

```python
for t in 1..T:
    publish the stage catalogue (B_jt, blurbs, tie-break permutation, stages remaining)
    render each seat's private block for stage t
    for r in 1..talk_rounds:   message round (broadcast and/or DM, per channel)
    run the format's bidding rounds
    settle: allocation, payments, executed transfers (dm_transfers only)
    publish the stage result under the format's disclosure rule
    append to the carried history
```

Privacy is structural, not a property of the wording: a turn view is assembled here from a shared public part
plus exactly one private block belonging to the reading seat, and a DM reaches only the seats
:class:`~interlens.arena.auction.actions.DMRouter` delivers it to. `tests/test_auction_scenario.py` asserts
that programmatically over a whole episode rather than trusting the templates.

All prose lives in :mod:`.auction_prompts`, which transcribes the reviewed and frozen templates. Nothing in
this module originates model-facing wording.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `BID_PHASE` |  |  |
| `DEFAULT_TURN_MAX_TOKENS` |  |  |
| `MID_STAGE_TALK_FAMILIES` |  |  |
| `TALK_PHASE` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`AuctionScenario`](AuctionScenario.md) | Five bidders, `T` stages, one mechanism config, one communication rung. |

## Functions

| Name | Summary |
|---|---|
| [`clock_round_cap`](clock_round_cap.md) | Number of clock rounds needed to walk from the start price to the reserve (or back), inclusive. |
| [`clock_start`](clock_start.md) | The clock start price used by every stage of a clock-family episode. |
| [`opening_clock_price`](opening_clock_price.md) | Where a clock family's price starts in each stage. |
