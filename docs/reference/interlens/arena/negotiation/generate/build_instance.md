# `build_instance`

Wrap a generated `(GameSpec, analysis)` into a solver-verified arena :class:`~interlens.arena.schema.Instance`.

```python
build_instance(
	game: GameSpec,
	analysis: dict,
	*,
	name: str,
	level: int,
	seed: int,
	id_prefix: str | None = None,
) -> Instance
```

Defined in [`interlens.arena.negotiation.generate`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/generate.py#L316-L345)

Primary-score convention (matching the shipped `negotiation` scenario): the episode's primary score is the
sum of per-party normalized surplus captures divided by its maximum over feasible deals (no deal = 0).
Thus the exact `ceiling` is `1.0` and the reference `floor` is the mean normalized primary over
feasible deals -- an average-feasible-deal policy. Both are invariant to independent positive affine
transformations of the parties' score sheets. `payload` is `GameSpec.to_json()` (round-trips back via
`GameSpec.from_json`); `solution` is the full
:func:`~interlens.arena.negotiation.solutions.analyze` dict (descriptors + every solution point), so scorers
and analyses read it straight from the stored Instance without re-solving. If the feasible set is empty
(no-deal is the rational outcome) ceiling/floor are both `0.0`. `name` is the scenario name the calling
scenario passes in, so `Instance.scenario` matches it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameSpec](../sheets/GameSpec.md) | *required* |  |
| `analysis` | `dict` | *required* |  |
| `name` | `str` | *required* |  |
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `id_prefix` | `str \| None` | `None` |  |
