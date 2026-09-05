# `BayesianRationalPolicy`

The composed rational negotiator = belief oracle + acceptance oracle + best-response oracle.

```python
BayesianRationalPolicy(
	*,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'bayes-rational',
)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L793-L1007)

**Inherits from:** [Policy](Policy.md)

Each turn: (1) update beliefs over opponents from observed offers (private info) or read them off known
sheets (full info); (2) build the opponent acceptance-probability table; (3) accept the standing offer if
its surplus clears the optimal-stopping reservation, else propose the best-response deal; (4) walk if no
individually-rational deal can plausibly close before the deadline.

Parameters
----------
discount : float | None
    Per-round discount `delta` OVERRIDE for the acceptance and best-response oracles. Default `None` =
    use `state.discount` (which scenario-runner sets from the game's `discount`/`breakdown_risk`) —
    the state is a policy's single source of truth, analogous to the game for an oracle.
walk_if_hopeless : bool
    If True, `Walk` when the best-response proposal value is <= 0 at the final round.
name : str
    Display name.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'bayes-rational'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `discount` |  |  |
| `name` |  |  |
| `walk_if_hopeless` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L946-L991)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `vote` {#vote}

```python
vote(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L993-L1007)

Terminal quorum-aware vote; Reject when yes cannot pass or has lower EV than no.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
