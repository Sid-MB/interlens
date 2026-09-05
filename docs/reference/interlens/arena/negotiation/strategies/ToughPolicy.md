# `ToughPolicy`

Hardliner: always demand the own optimum; accept only offers within `accept_frac` of the own max (and above reservation).

```python
ToughPolicy(*, accept_frac: float = 0.95, name: str = 'tough')
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L552-L569)

**Inherits from:** [Policy](Policy.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `accept_frac` | `float` | `0.95` |  |
| `name` | `str` | `'tough'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accept_frac` |  |  |
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L561-L569)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
