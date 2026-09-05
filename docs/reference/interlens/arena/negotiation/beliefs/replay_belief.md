# `replay_belief`

A :class:`BeliefState` that has observed `offers` in order — reusing the longest cached prefix.

```python
replay_belief(option_counts, offers, **kwargs={}) -> BeliefState
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L519-L559)

`observe` is a pure left fold: the state after `[d1 ... dk]` depends on nothing but that sequence, so
replaying a prefix and then folding in the remaining offers gives *exactly* the state a from-scratch
replay would (same operations, same order, same float64). A negotiation turn extends its opponent's offer
list by at most one entry, so the cached prefix is almost always all but the last offer, and each turn
folds ONE observation instead of the whole history — which is what stops a seat's per-turn belief cost
growing with the round number.

Returns a private :meth:`BeliefState.copy` every time, so the caller may mutate or further `observe` on
the result without touching the cache. Grid-identity `kwargs` (`sigma`/`lam`/`floor`/`mode`/
`anchor_first`/`seed`/`tau_levels`/`max_rankings`) are part of the cache key; passing an explicit
`types=` grid bypasses the cache entirely, since a caller-supplied grid has no stable identity.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `option_counts` |  | *required* |  |
| `offers` |  | *required* |  |
| `kwargs` |  | `{}` |  |
