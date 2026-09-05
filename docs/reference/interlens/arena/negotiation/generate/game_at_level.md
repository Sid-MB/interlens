# `game_at_level`

The `(GameSpec, analysis)` at difficulty `level` from `seed` -- the level -> generator-knob mapping shared by :func:`generate_instance` and the `games.scorable` preset, so the difficulty ladder and the per-round discount default live in exactly one place (never re-defaulted at a call site).

```python
game_at_level(
	level: int,
	seed: int,
	*,
	ladder: list[dict] | None = None,
	**overrides={},
) -> tuple[GameSpec, dict]
```

Defined in [`interlens.arena.negotiation.generate`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/generate.py#L348-L365)

Maps `level` through `ladder` (default :data:`INSTANCE_LADDER`, shrinking feasible set with level) to
:func:`generate_game` knobs -- the bank's per-round discount :data:`LADDER_DISCOUNT` (< 1, so interior
concession is rational rather than deadline brinkmanship [sandholm_vulkan1999]) plus the level's
feasible-fraction/dominated-target -- then generates the game and its enumeration-verified analysis.
`**overrides` win over the ladder knobs (e.g. `discount=1.0` for a brinkmanship-baseline arm, or
`n_parties`/`n_issues`/`n_options`/`mix`/`info`). No `Instance` wrapping -- see
:func:`generate_instance` for that.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `ladder` | `list[dict] \| None` | `None` |  |
| `overrides` |  | `{}` |  |
