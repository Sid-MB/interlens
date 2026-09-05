# `GreedyAnchorPolicy`

Maximally selfish proposals plus the same reservation gate: always tables its OWN best deal `argmax_d u_self(d)` (canonical tie-break, tabled once and held), and accepts any standing offer with surplus >= 0, declining below.

```python
GreedyAnchorPolicy()
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L617-L642)

**Inherits from:** [Policy](Policy.md)

Against :class:`BayesianRationalPolicy` this isolates the proposal rule: the Bayesian agent best-responds
against a model of what opponents will accept and therefore proposes GENEROUSLY, while this one never
concedes an inch on its own ask yet is just as willing to sign anything that beats no-deal. If the seat
captures MORE here than under the Bayesian anchor, the anchor's proposals were leaving surplus on the
table out of opponent-model conservatism.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L636-L642)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
