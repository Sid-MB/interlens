# `scorable`

The default multi-party, multi-issue **scorable** game -- a thin alias to the existing generator so the whole preset machinery has one uniform entry point.

```python
scorable(
	*,
	level: int = 0,
	seed: int = 0,
	ladder: list[dict] | None = None,
	**overrides={},
) -> tuple[GameSpec, dict, dict]
```

Defined in [`interlens.arena.negotiation.games`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/games.py#L216-L237)

Delegates to :func:`~interlens.arena.negotiation.generate.game_at_level`, which maps the difficulty `level`
through the shipped :data:`~interlens.arena.negotiation.generate.INSTANCE_LADDER` (feasible-set size, the
dominated-acceptable repair, the per-round discount) to :func:`generate_game`. **Every default lives in
generate.py** and is never re-set here; `**overrides` (e.g. `n_parties`, `n_issues`, `n_options`,
`info`, `dominated_target`) pass straight through. Standard protocol (`protocol_cfg = {}`).

Parameters
----------
level : difficulty ladder index (0 = easiest / largest acceptable set).
seed : generator seed.
ladder : optional custom difficulty ladder (default :data:`INSTANCE_LADDER`).
**overrides : any :func:`generate_game` knob (overrides the ladder's).

Returns `(GameSpec, analysis, protocol_cfg)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | `0` |  |
| `seed` | `int` | `0` |  |
| `ladder` | `list[dict] \| None` | `None` |  |
| `overrides` |  | `{}` |  |
