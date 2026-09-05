# `AcceptanceCurve`

One opponent model's fitted `P(accept | z, rounds_left)`.

```python
AcceptanceCurve(
	form: str,
	params: dict = dict(),
	rounds_feature: str = 'rounds_left',
	p_min: float = 0.0,
	p_max: float = 1.0,
	n_events: int = 0,
	n_accepts: int = 0,
	heldout_ece: float | None = None,
	low_power: bool = False,
	notes: str = '',
)
```

Defined in [`interlens.arena.negotiation.calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L124-L254)

Parameters
----------
form : str
    Functional form. `"step"` = the Bayesian agent's own model (1.0 iff `z >= 0`), kept so the
    calibrated policy can be driven back to exact Bayes equivalence for the regression test.
    `"logistic"` = `sigmoid(a + b*z)`. `"logistic_rounds"` = `sigmoid(a + b*z + c*r)` where `r` is
    the round position (see `rounds_feature`). `"bins"` = a piecewise-constant lookup over `z`
    edges, optionally one row per `rounds_left` bin — the assumption-free form, at the cost of needing
    enough events per cell.
params : dict
    Form-specific coefficients. logistic: `a`, `b` (and `c` with rounds). bins: `z_edges` (K-1
    ascending interior edges), `p` (K probabilities, or a list of K-wide rows when `r_edges` is given)
    and optional `r_edges`.
rounds_feature : str
    What `r` means in the logistic forms. `"rounds_left"` (the default) = the raw integer count of
    rounds remaining AFTER the current one, 0 on the forced final — this is the fitting lane's convention
    and the default is deliberately the same as theirs, because a curve fitted on raw counts and evaluated
    on a fraction is wrong by a silent rescaling that nothing would raise on.
    `"frac_elapsed"` = `1 - rounds_left/total` in `[0, 1]`, for a fit that chose scale-free pressure.
    Ignored by `step`/`logistic`.
p_min, p_max : float
    Clamp on the returned probability. The default floor/ceiling of 0/1 leaves the curve untouched; a small
    positive floor is worth setting when the fit is extrapolating far below the observed `z` range, since
    a hard 0 tells the expectimax that a deal is *impossible* rather than merely unlikely and can make the
    agent walk on a technicality.
n_events, n_accepts : int
    Sample size behind the fit. Carried so a ladder result can never be quoted without the reader being
    able to see it was fit on 30 events.
heldout_ece : float | None
    Held-out expected calibration error, if the fitting lane computed one.
low_power : bool
    The fitting lane's own flag that this curve is not quotable — too few events, too few game clusters,
    or no variation in the outcome. Carried through so a consumer can REFUSE it rather than discover the
    problem in a results table. The fit that motivated this (`Qwen3-8B:thinking-on`) has 60 events across
    3 games and zero below-threshold votes.
notes : str
    Free text from the fitting lane (run dirs, exclusions, caveats).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `form` | `str` | *required* |  |
| `params` | `dict` | `dict()` |  |
| `rounds_feature` | `str` | `'rounds_left'` |  |
| `p_min` | `float` | `0.0` |  |
| `p_max` | `float` | `1.0` |  |
| `n_events` | `int` | `0` |  |
| `n_accepts` | `int` | `0` |  |
| `heldout_ece` | `float \| None` | `None` |  |
| `low_power` | `bool` | `False` |  |
| `notes` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `form` | `str` |  |
| `heldout_ece` | `float \| None` |  |
| `is_step` | `bool` | Whether this curve IS the Bayesian agent's own step model (so a calibrated policy carrying only step curves must behave identically to :class:`BayesianRationalPolicy`). |
| `low_power` | `bool` |  |
| `n_accepts` | `int` |  |
| `n_events` | `int` |  |
| `notes` | `str` |  |
| `p_max` | `float` |  |
| `p_min` | `float` |  |
| `params` | `dict` |  |
| `rounds_feature` | `str` |  |

## Methods {#methods}

## `from_dict` {#from_dict}

```python
from_dict(cls, d: dict) -> 'AcceptanceCurve'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L248-L254)

Build from one model's JSON block, ignoring keys the schema does not define (the fitting lane is free to carry extra diagnostics alongside the coefficients).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `prob` {#prob}

```python
prob(self, z: np.ndarray, rounds_left: int = 1, total_rounds: int = 0) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L223-L246)

Vectorized `P(accept)` over an array of `z` values, clamped to `[p_min, p_max]`.

`rounds_left` is the number of rounds still playable INCLUDING the current one; `total_rounds` is
the episode's deadline in the same units, needed only by the `frac_elapsed` rounds feature.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `np.ndarray` | *required* |  |
| `rounds_left` | `int` | `1` |  |
| `total_rounds` | `int` | `0` |  |
