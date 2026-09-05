# `generate_game`

Generate one scorable-negotiation game plus its enumeration-verified analysis dict.

```python
generate_game(
	n_parties: int = 6,
	n_issues: int = 5,
	n_options: int | Sequence[int] = 4,
	mix: tuple[float, float, float] = (0.4, 0.4, 0.2),
	issue_types: Sequence[str] | None = None,
	feasible_fraction: float = 0.1,
	feasible_tol: float = 0.6,
	dominated_target: float | None = 0.6,
	dominated_tol: float = 0.12,
	auto_mix: bool = True,
	decorrelate: bool = True,
	rounds: int = 4,
	info: str = 'full',
	chat: bool = True,
	proposer: int = 0,
	veto: int | None = 1,
	discount: float = 1.0,
	breakdown_risk: float = 0.0,
	max_tries: int = 600,
	seed: int = 0,
) -> tuple[GameSpec, dict]
```

Defined in [`interlens.arena.negotiation.generate`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/generate.py#L174-L307)

Parameters
----------
n_parties : number of negotiating parties `n`.
n_issues : number of issues `J`.
n_options : options per issue -- one int (same for all issues) or a per-issue sequence of length `n_issues`.
    Deal space size is `prod` of these; keep it enumerable (<= ~3125).
mix : `(distributive, integrative, compatible)` fractions used to assign each issue a type (normalized
    internally). The geometric lever on the dominated-acceptable fraction: more compatible/integrative
    content -> more dominated-but-acceptable slack; more distributive content -> nearer zero-sum.
issue_types : explicit per-issue type list (strings/`IssueType`); overrides `mix` when given.
feasible_fraction : target size of the unanimity acceptable (IR) set as a fraction of `|D|` -- the
    difficulty dial (smaller = harder to find a deal). Thresholds are calibrated to hit it.
feasible_tol : relative tolerance on the acceptable count; a candidate counts as size-OK when its count is
    within `feasible_tol` of the target (always at least +/-1 deal of slack).
dominated_target : target fraction of acceptable deals that are Pareto-dominated (the central repair). Set
    `None` to skip the search and just return the first size-OK candidate.
dominated_tol : accept-and-stop tolerance on the dominated fraction; otherwise the closest candidate over
    `max_tries` seeds is returned.
auto_mix : when True and `dominated_target` is set and `issue_types` is not given, also sweep the
    distributive fraction of the issue mix (more distributive -> nearer zero-sum -> lower dominated fraction)
    so a low or high target is reachable that a single fixed mix could not hit by reseeding alone. `mix` is
    the sweep center; set `auto_mix=False` to hold `mix` fixed.
decorrelate : when True, permute each issue's option order and use neutral option labels so no public role
    text can leak preferences (the mandatory control from Study A) [reproA2025].
rounds, info, chat, proposer, veto : protocol knobs stored on the returned `GameSpec` (see
    :class:`~interlens.arena.negotiation.sheets.GameSpec`). Acceptable-set analysis uses unanimity IR.
discount : per-round discount `delta` in (0, 1] stored on the game (default 1.0 = no impatience). With
    only a hard deadline and `delta = 1`, the rational baseline is deadline brinkmanship, so a game meant
    to elicit interior concession should set `delta < 1` [sandholm_vulkan1999] (the instance ladder does).
    The equilibrium/acceptance oracles read this as their single source of truth.
breakdown_risk : per-round exogenous-breakdown probability in [0, 1) stored on the game (default 0.0). An
    alternative to discounting for making interior concession rational.
max_tries : rejection-sampling budget (distinct seeds tried) when `dominated_target` is set.
seed : base RNG seed; try `t` uses `seed*100003 + t` so different base seeds give different games.

Returns
-------
`(GameSpec, analysis)` where `analysis` is :func:`solutions.analyze`'s dict (all descriptors verified by
enumeration). `GameSpec.meta` records the generator provenance and the achieved fractions, and
`analysis["generator"]` mirrors the request/achievement so failures to hit a target are visible, never
silent.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_parties` | `int` | `6` |  |
| `n_issues` | `int` | `5` |  |
| `n_options` | `int \| Sequence[int]` | `4` |  |
| `mix` | `tuple[float, float, float]` | `(0.4, 0.4, 0.2)` |  |
| `issue_types` | `Sequence[str] \| None` | `None` |  |
| `feasible_fraction` | `float` | `0.1` |  |
| `feasible_tol` | `float` | `0.6` |  |
| `dominated_target` | `float \| None` | `0.6` |  |
| `dominated_tol` | `float` | `0.12` |  |
| `auto_mix` | `bool` | `True` |  |
| `decorrelate` | `bool` | `True` |  |
| `rounds` | `int` | `4` |  |
| `info` | `str` | `'full'` |  |
| `chat` | `bool` | `True` |  |
| `proposer` | `int` | `0` |  |
| `veto` | `int \| None` | `1` |  |
| `discount` | `float` | `1.0` |  |
| `breakdown_risk` | `float` | `0.0` |  |
| `max_tries` | `int` | `600` |  |
| `seed` | `int` | `0` |  |
