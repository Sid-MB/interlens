# `ThresholdOracle`

The trivial hard-violation detector: accepting or proposing a deal below one's *own* threshold is a strict rationality error (agreeing below your BATNA is worse than no deal — Abdelnabi et al.'s "wrong deals" metric, which runs 7-20% even for strong models).

```python
ThresholdOracle(agent: int | None = None)
```

Defined in [`interlens.arena.negotiation.acceptance`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L282-L323)

**Inherits from:** [Oracle](../../oracles/Oracle.md)

Cheap (one surplus lookup per action); values
each action at the agent's own surplus (Walk/Reject at 0) and flags the individual-rationality violations.

This complements the stopping oracle: `AcceptanceOracle` says *when* holding out beats accepting a
good offer, while `ThresholdOracle` catches the strictly-dominated moves regardless of timing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `int \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `agent` |  |  |
| `name` |  |  |

## Methods {#methods}

## `evaluate` {#evaluate}

```python
evaluate(self, game, history, agent, legal)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L296-L323)

Value `Accept`/`Propose` at the agent's own surplus (Walk/Reject at 0); `best` is the surplus-maximizing individually-rational move.

Flags: `below_threshold_accept` (an available Accept
is below the agent's BATNA) and `below_threshold_propose` (proposing a deal below one's own BATNA).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |
| `agent` |  | *required* |  |
| `legal` |  | *required* |  |
