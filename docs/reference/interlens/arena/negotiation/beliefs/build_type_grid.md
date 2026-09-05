# `build_type_grid`

Enumerate the opponent-type hypothesis grid = weight-profiles x shape-assignments x tau-levels.

```python
build_type_grid(
	option_counts,
	tau_levels=(0.35, 0.55, 0.75),
	max_rankings: int = 24,
	seed: int = 0,
) -> list
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L124-L148)

Parameters
----------
option_counts : sequence[int]
    Per-issue option counts `(O_1, ..., O_J)`.
tau_levels : sequence[float]
    Candidate reservation thresholds on the `[0, 1]` utility scale.
max_rankings : int
    Cap on the number of weight-ranking hypotheses (all `J!` if fewer, else a deterministic sample).
seed : int
    Seed for the ranking sample (determinism).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `option_counts` |  | *required* |  |
| `tau_levels` |  | `(0.35, 0.55, 0.75)` |  |
| `max_rankings` | `int` | `24` |  |
| `seed` | `int` | `0` |  |
