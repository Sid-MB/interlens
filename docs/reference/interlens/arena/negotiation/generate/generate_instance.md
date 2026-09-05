# `generate_instance`

Generate one solver-verified arena :class:`~interlens.arena.schema.Instance` at difficulty `level` from `seed` -- the bridge a `ScorableNegotiation` scenario's `generate_instance` delegates to.

```python
generate_instance(
	level: int,
	seed: int,
	*,
	name: str = 'scorable_negotiation',
	ladder: list[dict] | None = None,
	**overrides={},
) -> Instance
```

Defined in [`interlens.arena.negotiation.generate`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/generate.py#L368-L383)

Maps `level` through `ladder` (default :data:`INSTANCE_LADDER`, shrinking feasible set with level) to
:func:`generate_game` knobs via :func:`game_at_level`, generates the game plus its enumeration-verified
analysis, and wraps them via :func:`build_instance`. The bank ships with per-round discount
:data:`LADDER_DISCOUNT` (< 1, so interior concession is rational rather than deadline brinkmanship
[sandholm_vulkan1999]); pass `discount=1.0` (or any other knob) via `**overrides` to change it -- e.g. a
brinkmanship-baseline ablation arm. Other overridable knobs: `n_parties`, `n_issues`, `n_options`,
`mix`, `max_tries`, `breakdown_risk`. `name` sets `Instance.scenario` so a scenario passes
`self.name`. The payload is deterministic per `(level, seed)` (the instance id is fresh each call, per the
arena convention).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `name` | `str` | `'scorable_negotiation'` |  |
| `ladder` | `list[dict] \| None` | `None` |  |
| `overrides` |  | `{}` |  |
