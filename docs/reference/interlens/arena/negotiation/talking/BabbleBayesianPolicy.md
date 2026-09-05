# `BabbleBayesianPolicy`

The babble control: the mute decision rule plus fluent, on-topic, state-INDEPENDENT boilerplate every turn.

```python
BabbleBayesianPolicy(
	*,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'babble-bayes-rational',
	**kwargs={},
)
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L485-L513)

**Inherits from:** [BayesianRationalPolicy](../strategies/BayesianRationalPolicy.md)

Sentences are length-matched to the talking variants' narrations and rotate deterministically by
round, so the channel is equally busy but carries zero information about this seat's state.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'babble-bayes-rational'` |  |
| `kwargs` |  | `{}` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `BABBLE` |  |  |

## Methods {#methods}

## `commentary` {#commentary}

```python
commentary(self, state: NegotiationState) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L511-L513)

One boilerplate sentence per turn, a pure function of the round number.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |
