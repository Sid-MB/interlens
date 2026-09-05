# `RolloutEnv`

The negotiation transition a rollout needs.

```python
RolloutEnv()
```

Defined in [`interlens.arena.negotiation.analysis.rollout`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L34-L48)

**Inherits from:** `Protocol`

Implementations must not mutate the input state in `step`
(return a fresh/cloned state) so a single state can seed many counterfactual branches.

## Methods {#methods}

## `legal_actions` {#legal_actions}

```python
legal_actions(self, state: State, seat: str) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L41-L42)

Legal actions for `seat` at `state` (used to validate / enumerate; may be empty if unbounded).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `State` | *required* |  |
| `seat` | `str` | *required* |  |

## `next_seat` {#next_seat}

```python
next_seat(self, state: State) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L38-L39)

The seat to move now, or `None` if the state is terminal.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `State` | *required* |  |

## `step` {#step}

```python
step(self, state: State, seat: str, action: Action) -> State
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L44-L45)

Apply `action` by `seat`; return the successor state (no in-place mutation).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `State` | *required* |  |
| `seat` | `str` | *required* |  |
| `action` | `Action` | *required* |  |

## `surplus` {#surplus}

```python
surplus(self, state: State, agent: str) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L47-L48)

Terminal surplus for `agent` (call only at a terminal state).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `State` | *required* |  |
| `agent` | `str` | *required* |  |
