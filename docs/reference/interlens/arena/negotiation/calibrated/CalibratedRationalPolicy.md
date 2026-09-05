# `CalibratedRationalPolicy`

:class:`BayesianRationalPolicy` with its opponent acceptance model replaced by fitted behavioural curves.

```python
CalibratedRationalPolicy(
	*,
	curves: AcceptanceCurveSet,
	opponent_model: str,
	seat_models: dict[int, str] | None = None,
	vote_curves: AcceptanceCurveSet | None = None,
	endgame_rounds: int = 0,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'calibrated-rational',
)
```

Defined in [`interlens.arena.negotiation.calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L459-L557)

**Inherits from:** [BayesianRationalPolicy](../strategies/BayesianRationalPolicy.md)

Optimal stopping, expectimax best-response, the IR floor on its own acceptances and the
walk-if-hopeless rule are inherited unchanged.

Parameters
----------
curves : AcceptanceCurveSet
    The fitted curves and their `z` convention.
opponent_model : str
    Model id filling the OTHER seats, used to look up the curve. The lineup knows this (the run's
    `--models`); the policy cannot infer it from the state, which is why it is required.
seat_models : dict[int, str] | None
    Per-seat override when the table is heterogeneous — seat index to model id. Seats absent here use
    `opponent_model`. Supply this for any mixed-model lineup; with a homogeneous lineup leave it `None`.
discount, walk_if_hopeless, name
    As :class:`BayesianRationalPolicy`.

Attributes
----------
last_path : str | None
    `"calibrated"` or `"belief"` — which acceptance model the most recent turn actually used. Set every
    turn so a run can be AUDITED for whether the calibrated path was live, instead of the cell's label
    being taken on trust. A full-info run whose policy reports `"belief"` is mislabelled.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `curves` | [AcceptanceCurveSet](AcceptanceCurveSet.md) | *required* |  |
| `opponent_model` | `str` | *required* |  |
| `seat_models` | `dict[int, str] \| None` | `None` |  |
| `vote_curves` | [AcceptanceCurveSet](AcceptanceCurveSet.md) \| None | `None` |  |
| `endgame_rounds` | `int` | `0` |  |
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'calibrated-rational'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `curves` |  |  |
| `endgame_rounds` |  |  |
| `last_path` | `str \| None` |  |
| `opponent_model` |  |  |
| `seat_models` |  |  |
| `vote_curves` |  |  |

## Methods {#methods}

## `model_for_seat` {#model_for_seat}

```python
model_for_seat(self, seat: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/calibrated.py#L505-L507)

Model id seated at `seat` — the per-seat override if given, else `opponent_model`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
