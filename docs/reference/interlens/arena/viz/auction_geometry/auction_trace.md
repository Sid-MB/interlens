# `auction_trace`

Replay one stored auction episode and return everything the auction panels plot.

```python
auction_trace(
	episode: dict,
	instance: dict,
	*,
	geometry: AuctionGeometry | None = None,
	counterfactuals: bool = True,
) -> dict | None
```

Defined in [`interlens.arena.viz.auction_geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L446-L551)

The replay is exact — the scenario is a pure state machine and the stored turns are its inputs — so every
field below is the state the seat actually decided in, not an inference from the turn log.

Parameters
----------
episode : dict
    A stored `Episode.to_json()` record.
instance : dict
    The `Instance` record it was played on.
geometry : AuctionGeometry, optional
    A prebuilt geometry to reuse (pass the same object for both sides of a comparison). Built from
    `episode["cell_cfg"]` when omitted.
counterfactuals : bool
    Compute the per-turn rational and oracle references. On by default because they are the campaign's
    headline instrumentation; `False` is the fast path for a bulk index build, and costs roughly 4x less
    on a ten-lot SAA episode.

Returns
-------
dict | None
    `{"geometry", "turns", "stages", "ladder", "channel", "onset", "replay"}`, or `None` if the
    episode is not an auction episode or the replay does not reconstruct (a missing panel is a much better
    outcome than a crashed export, so every failure mode here returns `None` with its reason on
    `replay`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `instance` | `dict` | *required* |  |
| `geometry` | [AuctionGeometry](AuctionGeometry.md) \| None | `None` |  |
| `counterfactuals` | `bool` | `True` |  |
