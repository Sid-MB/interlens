# `OfferCurveSet`

A fitted :class:`OfferCurve` per opponent model.

```python
OfferCurveSet(curves: dict, default: OfferCurve | None = None, provenance: dict = dict())
```

Defined in [`interlens.arena.negotiation.llm_calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L141-L169)

Same lookup contract as
:class:`~interlens.arena.negotiation.calibrated.AcceptanceCurveSet`: an unknown model with no default is an
ERROR at seat construction, never a silent fallback.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `curves` | `dict` | *required* |  |
| `default` | [OfferCurve](OfferCurve.md) \| None | `None` |  |
| `provenance` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `curves` | `dict` |  |
| `default` | [OfferCurve](OfferCurve.md) \| None |  |
| `provenance` | `dict` |  |

## Methods {#methods}

## `for_model` {#for_model}

```python
for_model(self, model_id: str) -> OfferCurve
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L151-L158)

The curve for `model_id`, or `default`; :class:`KeyError` naming the fitted models otherwise.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model_id` | `str` | *required* |  |

## `from_json_dict` {#from_json_dict}

```python
from_json_dict(cls, blob: dict) -> 'OfferCurveSet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L160-L169)

Read the fitting lane's `offers` block: `{"models": {id: {...}}, "default": {...}?}`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `blob` | `dict` | *required* |  |
