# `bilateral_multiissue`

A **DoND-style bilateral, multi-issue, private-value** negotiation [lewis2017]: two parties bargain over `n_issues` item types, each with private per-item values -- the classic "Deal or No Deal" item-division game, reproduced here as the scorable generator restricted to `n_parties=2`.

```python
bilateral_multiissue(
	*,
	n_issues: int = 3,
	n_options: int = 5,
	info: str = 'private',
	seed: int = 0,
	**overrides={},
) -> tuple[GameSpec, dict, dict]
```

Defined in [`interlens.arena.negotiation.games`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/games.py#L187-L212)

This is a thin call into :func:`~interlens.arena.negotiation.generate.generate_game` with `n_parties=2`, so
it inherits every score-sheet repair (the Pareto-slack / feasible-size / sparsity-IoU knobs) and its verified
analysis; no repair is re-implemented. Standard multi-round protocol (`protocol_cfg = {}`).

Parameters
----------
n_issues : number of item-type issues `J` (Hua et al. / DoND use ~3).
n_options : options per issue (the item-count levels).
info : `"private"` (each party's values are private -- the DoND setting, where some inefficiency is rational
    by Myerson-Satterthwaite) or `"full"` (common knowledge, an efficiency upper bound).
seed : generator seed (the game IS randomized here -- different seeds give different value sheets).
**overrides : any other :func:`generate_game` knob (`dominated_target`, `mix`, `feasible_fraction`,
    `rounds`, `discount`, ...); defaults come from `generate_game` and are never re-set here.

Returns `(GameSpec, analysis, protocol_cfg)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_issues` | `int` | `3` |  |
| `n_options` | `int` | `5` |  |
| `info` | `str` | `'private'` |  |
| `seed` | `int` | `0` |  |
| `overrides` |  | `{}` |  |
