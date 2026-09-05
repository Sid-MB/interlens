# `LLMCalibratedRationalPolicy`

:class:`BayesianRationalPolicy` for PRIVATE-information tables with both rationalistic priors replaced by the fitted :class:`LLMOpponentModel` (module docstring).

```python
LLMCalibratedRationalPolicy(
	*,
	model: LLMOpponentModel,
	opponent_model: str,
	seat_models: dict[int, str] | None = None,
	endgame_rounds: int = 1,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'llm-calibrated-rational',
)
```

Defined in [`interlens.arena.negotiation.llm_calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L237-L446)

**Inherits from:** [BayesianRationalPolicy](../strategies/BayesianRationalPolicy.md)

Inherits the belief posterior, the IR floor on
its own acceptances, the quorum-aware vote valuation and the walk rule unchanged.

Parameters
----------
model : LLMOpponentModel
    The fitted opponent model.
opponent_model : str
    Model id filling the other seats (the fitting key, e.g. `"claude-opus-5"`). Required because the
    policy cannot infer from the state who it is playing.
seat_models : dict[int, str] | None
    Per-seat override for heterogeneous tables. A seat mapped to a key starting with `"policy:"` is a
    computable seat: it keeps the parent's step-posterior acceptance column and contributes no offer
    curve, since the fitted curves describe LLMs, not the project's own agents.
endgame_rounds : int
    How many final regular rounds (plus the forced final itself) are priced at the vote grain when
    `model.acceptance_vote` exists. 1 covers the last regular round + forced final.
discount, walk_if_hopeless, name
    As :class:`BayesianRationalPolicy`.

Attributes
----------
last_path : str | None
    `"calibrated"`, `"calibrated-vote"` or `"belief"` (an opponent column that fell back to the
    parent's model) — set every turn so a run can be audited for which model was live.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | [LLMOpponentModel](LLMOpponentModel.md) | *required* |  |
| `opponent_model` | `str` | *required* |  |
| `seat_models` | `dict[int, str] \| None` | `None` |  |
| `endgame_rounds` | `int` | `1` |  |
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'llm-calibrated-rational'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `endgame_rounds` |  |  |
| `last_path` | `str \| None` |  |
| `model` |  |  |
| `opponent_model` |  |  |
| `seat_models` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L412-L446)

Parent machinery with the fitted acceptance table when no offer model is fitted (the acceptance-only ablation, and the exact-Bayes regression path under step curves); otherwise the same accept / propose / walk skeleton with the reservation and the proposal continuation both priced on the empirical incoming-offer distribution.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |

## `model_for_seat` {#model_for_seat}

```python
model_for_seat(self, seat: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L288-L290)

Fitting key seated at `seat` — the per-seat override if given, else `opponent_model`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |

## `reservation` {#reservation}

```python
reservation(self, state) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L398-L409)

The reservation surplus this policy holds at `state` — the number an offline audit plots against a standing offer's surplus.

Under the empirical offer model when fitted, else the parent's.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |
