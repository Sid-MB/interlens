# `AuctionGeometry`

One auction instance's full post-hoc geometry, ready to plot.

```python
AuctionGeometry(spec, *, difficulty: dict | None = None, screens: dict | None = None)
```

Defined in [`interlens.arena.viz.auction_geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L94-L219)

Built once per instance and shared by every episode played on it, so both sides of a paired contrast are
drawn against one identical set of draws. Cheap to build (no matrices are materialized), so unlike
:class:`~interlens.arena.viz.geometry.GameGeometry` the caching is a convenience rather than a necessity.

Parameters
----------
spec : AuctionSpec
    The spec the episode was ACTUALLY played on — the cell's mechanism, horizon, channel and card scramble
    applied on top of the frozen bank draws. Build it with
    :meth:`~interlens.arena.scenarios.auction.AuctionScenario.spec_for` rather than from the bank's
    nominal mechanism: a single-lot bank backs the sealed cells AND the Dutch ones, and replaying a Dutch
    episode against a sealed mechanism scores every turn against the wrong rule.
difficulty : dict, optional
    The instance's `solution.difficulty` record (scalar, components, tags) — carried opaquely so a
    generator can add a component without a schema change here. The index sorts on `scalar` and `tags`.
screens : dict, optional
    The bank's outcome-blind screen record, shown as provenance.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
| `difficulty` | `dict \| None` | `None` |  |
| `screens` | `dict \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `difficulty` |  |  |
| `horizon` | `int` | `T`, the number of stages this episode ran. |
| `n_bidders` | `int` | Number of seats. |
| `n_items` | `int` | Number of distinct lots per stage. |
| `screens` |  |  |
| `spec` |  |  |

## Methods {#methods}

## `from_instance` {#from_instance}

```python
from_instance(
	instance: dict | None,
	cell_cfg: dict | None = None,
) -> 'AuctionGeometry | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L122-L141)

The geometry of a stored auction `Instance` dict at a cell's config, or `None` if the payload is not an auction spec (so the caller renders a non-auction episode by its own path rather than crashing).

`cell_cfg` is the episode's own `cell_cfg`: it selects the value structure and carries the
mechanism/horizon/channel/scramble the cell overrode. Passing `None` reads the bank's nominal spec,
which is right for a bank browser and wrong for an episode page.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | `dict \| None` | *required* |  |
| `cell_cfg` | `dict \| None` | `None` |  |

## `lot_ids` {#lot_ids}

```python
lot_ids(self) -> list[str]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L159-L163)

The printed lot ids in slot order (`L01`, `L02`, …) — the same strings the action grammar and the transcript use, read from the prompt module so the page cannot invent a second naming.

## `price_ceiling` {#price_ceiling}

```python
price_ceiling(self) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L165-L170)

The top of the shared price axis every panel plots on: the largest realized valuation anywhere in the episode, or the clock ceiling where that is higher.

One scale across all stages is what makes the
staged ladder readable as one figure rather than `T` unrelated charts.

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L173-L219)

The whole instance geometry as one JSON payload for the browser.

Everything private is under `stages[].values` / `budgets` / `synergy_target` and is labelled as
the analyst's view by the page that renders it — no seat ever saw another seat's row.
