# `auction_geometry`

Module `interlens.arena.viz.auction_geometry`

The plottable geometry of one repeated-auction episode — the `AuctionSpec`-shaped sibling of
:class:`~interlens.arena.viz.geometry.GameGeometry`.

`GameGeometry` does not transfer and was never going to: it materializes the whole `|D| x n` utility matrix
of an enumerable deal space, and an auction has neither (bids are effectively continuous, multi-item
allocation is combinatorial). `GameGeometry.from_instance` returns `None` on an auction payload, at which
point every negotiation panel degrades away — so this module supplies what replaces them, in the same shape:
one object built per instance, one `to_json` the browser reads, and a per-episode trace beside it.

Two things live here.

:class:`AuctionGeometry` is **instance-scoped and episode-independent**: the mechanism, the five public cards,
the lot catalogue with its public attribute loadings, and every stage's frozen draw (realized valuations,
budgets, synergy targets, tie-break, clock ceiling). It is the post-hoc analyst's view — the private draws are
on it, which is exactly why the page that renders it says so in as many words.

:func:`auction_trace` is **episode-scoped** and is the part that needs a replay. A stored auction turn records
its `parsed_action` but not the stage it fell in, nor the standing-bid table it was decided against, nor the
remaining budget: all three live in the scenario's state machine. Rather than re-deriving them with a heuristic
(a seat's second move in a stage is NOT a new stage under SAA, where a stage runs many bidding rounds), the
trace replays the episode through :class:`~interlens.arena.scenarios.auction.AuctionScenario` and reads the
real state at every turn. That is also what makes the per-turn counterfactuals honest: the two computable
rules are evaluated against the *pre-move* state block the seat itself decided in, via
:mod:`~interlens.arena.scenarios.auction_policy`, which is the same path the campaign's replay-integrity gate
uses on computable seats. Every turn of every arm gets both, `all_llm` included, because both are arithmetic
given the spec.

Example:

```python
geo = AuctionGeometry.from_instance(instance, cell_cfg=episode["cell_cfg"])
geo.spec.mechanism.family                       # 'saa'
trace = auction_trace(episode, instance, geometry=geo)
trace["turns"][7]["counterfactual"]["rational"] # {'action': 'bid', 'bids': [...]}
trace["stages"][0]["winners"]                   # per-lot winning seat index
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `COORDINATION_TALK_TERMS` | `tuple[str, ...]` |  |
| `COUNTERFACTUAL_RULES` | `tuple[tuple[str, str], ...]` |  |

## Classes

| Name | Summary |
|---|---|
| [`AuctionGeometry`](AuctionGeometry.md) | One auction instance's full post-hoc geometry, ready to plot. |

## Functions

| Name | Summary |
|---|---|
| [`agreement_in_force_row`](agreement_in_force_row.md) | :func:`~interlens.arena.auction.metrics.detect_agreement`'s rule applied to a STORED stage row instead of a live `StageOutcome` — whether an agreement was in force at the stage this row records. |
| [`auction_trace`](auction_trace.md) | Replay one stored auction episode and return everything the auction panels plot. |
| [`index_row`](index_row.md) | The auction index's columns for one episode, derived from the STORED record with no replay. |
| [`is_auction_instance`](is_auction_instance.md) | Whether a stored `Instance` dict carries an auction spec — the discriminator the viz layer branches on. |
| [`json_safe`](json_safe.md) | `value` with every non-finite float replaced by `None`, recursively through dicts and lists. |
