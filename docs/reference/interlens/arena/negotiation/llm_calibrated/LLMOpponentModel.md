# `LLMOpponentModel`

Everything the calibrated policy consumes, loaded from ONE fitted artifact.

```python
LLMOpponentModel(
	acceptance: AcceptanceCurveSet,
	acceptance_vote: AcceptanceCurveSet | None = None,
	offers: OfferCurveSet | None = None,
	provenance: dict = dict(),
)
```

Defined in [`interlens.arena.negotiation.llm_calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L175-L231)

Parameters
----------
acceptance : AcceptanceCurveSet
    Panel-grain `P(accept | z, rounds_left)` per opponent model ("next time this seat moves, does it
    take this offer" — folds in crowding).
acceptance_vote : AcceptanceCurveSet | None
    Vote-conditional grain, applied in the endgame (the forced final and the `endgame_rounds` before
    it). Measured LLM vote acceptance is ~0.99 even below the voter's own reservation, an order of
    magnitude above the panel rate, and pricing the endgame at the panel grain tells the agent closure is
    near-impossible exactly where it is near-certain (the lesson of the full-info calibrated lane).
offers : OfferCurveSet | None
    The empirical incoming-offer distribution per opponent model. `None` = keep the parent's
    belief-induced offer distribution (the acceptance-only variant, a legitimate ablation arm).
provenance : dict
    The fitting lane's record (runs, fit/held-out instance split, invocation).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `acceptance` | [AcceptanceCurveSet](../calibrated/AcceptanceCurveSet.md) | *required* |  |
| `acceptance_vote` | [AcceptanceCurveSet](../calibrated/AcceptanceCurveSet.md) \| None | `None` |  |
| `offers` | [OfferCurveSet](OfferCurveSet.md) \| None | `None` |  |
| `provenance` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `SCHEMA` |  |  |
| `acceptance` | [AcceptanceCurveSet](../calibrated/AcceptanceCurveSet.md) |  |
| `acceptance_vote` | [AcceptanceCurveSet](../calibrated/AcceptanceCurveSet.md) \| None |  |
| `offers` | [OfferCurveSet](OfferCurveSet.md) \| None |  |
| `provenance` | `dict` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(cls, path: str | Path) -> 'LLMOpponentModel'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L203-L224)

Load the fitting lane's combined artifact (schema :data:`SCHEMA`); see the fitter for the shape.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | *required* |  |

## `step` {#step}

```python
step(cls) -> 'LLMOpponentModel'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L226-L231)

The degenerate model that drives :class:`LLMCalibratedRationalPolicy` back to exact Bayes behaviour (step acceptance, no offer model) — the equivalence-test control.
