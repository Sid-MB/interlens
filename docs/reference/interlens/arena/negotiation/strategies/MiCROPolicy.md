# `MiCROPolicy`

MiCRO (de Jonge 2022; multilateral variant arXiv:2510.17401): minimal-concession, parameter-free.

```python
MiCROPolicy(*, seed: int = 0, name: str = 'micro')
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L472-L513)

**Inherits from:** [Policy](Policy.md)

Concede one new outcome iff distinct-offers-made `m <= n_min` (min distinct offers across opponents),
else repeat a previous offer; accept iff the standing offer is at least as good as the next outcome you
would propose.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seed` | `int` | `0` |  |
| `name` | `str` | `'micro'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L495-L513)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
