# `AcceptanceCurveSet`

A fitted curve per opponent model, plus the `z` convention they were all fit in.

```python
AcceptanceCurveSet(
	z_space: str,
	curves: dict[str, AcceptanceCurve],
	default: AcceptanceCurve | None = None,
	provenance: dict = dict(),
)
```

Defined in [`interlens.arena.negotiation.calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L257-L453)

Parameters
----------
z_space : str
    Which of :data:`Z_SPACES` the curves are functions of. Set by the fitting lane; the policy computes
    `z` the same way or the numbers mean nothing.
curves : dict[str, AcceptanceCurve]
    Model id (as it appears in the lineup, e.g. `"Qwen/Qwen3-8B"`) to its fitted curve.
default : AcceptanceCurve | None
    Curve for a model with no entry of its own. `None` (the default) makes an unknown model an ERROR
    rather than a silent fallback — seating a calibrated agent against a model nobody fit a curve for is a
    design mistake, not a runtime condition to paper over.
provenance : dict
    Whatever the fitting lane recorded about how these were produced (run dirs, episode counts, date).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z_space` | `str` | *required* |  |
| `curves` | dict[str, [AcceptanceCurve](AcceptanceCurve.md)] | *required* |  |
| `default` | [AcceptanceCurve](AcceptanceCurve.md) \| None | `None` |  |
| `provenance` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `all_step` | `bool` | Whether every curve here (including the default) is a step function — i.e. this set drives :class:`CalibratedRationalPolicy` back to exact Bayes behaviour. |
| `curves` | dict[str, [AcceptanceCurve](AcceptanceCurve.md)] |  |
| `default` | [AcceptanceCurve](AcceptanceCurve.md) \| None |  |
| `provenance` | `dict` |  |
| `z_space` | `str` |  |

## Methods {#methods}

## `for_model` {#for_model}

```python
for_model(self, model_id: str) -> AcceptanceCurve
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L292-L301)

The curve for `model_id`, or `default`.

Raises :class:`KeyError` when neither exists, naming the
models that ARE fit — a calibrated cell run against an uncalibrated opponent is uninterpretable, so
this fails at seat-construction time rather than quietly reverting to the step model.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model_id` | `str` | *required* |  |

## `from_fit_artifact` {#from_fit_artifact}

```python
from_fit_artifact(cls, path: str | Path, *, spec: str = 'base') -> 'AcceptanceCurveSet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L328-L398)

Load the acceptance-curve fitting lane's NATIVE artifact (`schema == "rational_agents/acceptance_curves/v1"`), as written by `experiments/rational_agents/self_benefit/fit_acceptance.py`.

That artifact is organised around the fit rather than around the consumer: each responder carries
several candidate `specs` plus validation blocks, coefficients are a flat
`[intercept, *slopes]` list, and the regressors are named in `base_features`. This adapter reads it
as-is rather than asking the fitting lane to reshape its output — the artifact of record should stay
the fitter's own.

Parameters
----------
path : str | Path
    The fitted JSON.
spec : str
    Which candidate fit to consume. `"base"` (`logit p = b0 + b_z z + b_r rounds_left`) is the
    preregistered one and the default; `"interaction"` adds `z * rounds_left`. Selecting a
    non-preregistered spec is a deliberate act and is recorded in `provenance["spec"]`.

The fit's `z` is `(u_i(d) - tau_i) / (max_d' u_i(d') - tau_i)` — this module's `surplus_norm` —
and its `rounds_left` is the count AFTER the current round. Both are asserted against the artifact's
own `base_features` so a change of regressors upstream fails loudly here instead of being evaluated
under the old meaning.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | *required* |  |
| `spec` | `str` | `'base'` |  |

## `from_json` {#from_json}

```python
from_json(cls, path: str | Path) -> 'AcceptanceCurveSet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L307-L326)

Load the fitting lane's artifact.

Expected shape (extra keys are ignored, so the fitting lane can carry diagnostics):

```python
{"schema_version": 1,
 "z_space": "surplus_norm",
 "models": {"Qwen/Qwen3-8B": {"form": "logistic_rounds", "params": {"a": .., "b": .., "c": ..},
                              "n_events": 1234, "n_accepts": 456, "heldout_ece": 0.03}},
 "default": {...},                       # optional
 "provenance": {"run_dirs": [...], ...}} # optional
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | *required* |  |

## `step` {#step}

```python
step(cls, z_space: str = 'surplus') -> 'AcceptanceCurveSet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L447-L453)

The degenerate set every model of which is the Bayesian agent's own step model.

Exists for the
equivalence regression test and as a sanity control cell (a "calibrated" run that must reproduce the
Bayes replication exactly).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z_space` | `str` | `'surplus'` |  |

## `vote_grain_from_fit_artifact` {#vote_grain_from_fit_artifact}

```python
vote_grain_from_fit_artifact(cls, path: str | Path) -> 'AcceptanceCurveSet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L400-L445)

Build the **vote-conditional** curve set from the fit artifact's `empirical` block.

WHY A SECOND GRAIN EXISTS. The fitted logistic is a **panel-grain** quantity: "next time this seat
moves, does it accept this offer" — which folds in crowding and inattention, because a seat facing five
standing offers can formally take at most one. Measured panel acceptance is 0.15-0.45. But the protocol
ends in a **forced vote**, and among offers actually voted on, acceptance is ~0.99 (Qwen3-8B 0.992 over
n=7,420; gemma 0.991 over n=8,971) — even *below* the voter's own reservation it is 0.81 and 0.96
respectively. Feeding the panel curve into the endgame therefore tells the agent that closure is nearly
impossible exactly where it is nearly certain, which is a large and one-directional error.

No new fit is needed: the three vote-conditional rates the artifact already reports
(`accept_rate_below_ir_when_voted` for `z < 0`, `accept_rate_high_z_when_voted` for `z >= 0.5`,
and `accept_rate_when_voted` over all votes) determine the middle bin exactly, since the overall rate
is their count-weighted mixture. The result is a three-bin step in `z` per responder — assumption-free
and reported rather than extrapolated.

Use with :class:`CalibratedRationalPolicy`'s `vote_curves` argument, which applies it only in the
endgame; during regular rounds the panel curve is the right object.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | *required* |  |

## `z_of` {#z_of}

```python
z_of(self, utility: np.ndarray, thresholds: np.ndarray, seat: int) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L303-L305)

`z` for every deal from `seat`'s point of view, under this set's declared convention.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `utility` | `np.ndarray` | *required* |  |
| `thresholds` | `np.ndarray` | *required* |  |
| `seat` | `int` | *required* |  |
