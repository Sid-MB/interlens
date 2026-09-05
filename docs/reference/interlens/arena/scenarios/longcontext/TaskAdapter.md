# `TaskAdapter`

Per-task behavior plugged into `DistributedLongContext`.

```python
TaskAdapter()
```

Defined in [`interlens.arena.scenarios.longcontext`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L69-L90)

Implementations live in
`interlens.arena.scenarios.dlc`.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `discussion_cap` | `int` |  |
| `final_cap` | `int` |  |
| `provisional` | `bool` |  |
| `solo_turn_cap` | `int` |  |
| `task` | `str` |  |

## Methods {#methods}

## `answer_instructions` {#answer_instructions}

```python
answer_instructions(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L79-L81)

How the finalizer must format its fenced-JSON answer.

## `grade` {#grade}

```python
grade(self, answer, payload: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L87-L90)

`-> {'primary': float, 'success': bool, ...task fields}`.

Must be a pure function of
`(answer, payload)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `answer` |  | *required* |  |
| `payload` | `dict` | *required* |  |

## `parse_answer` {#parse_answer}

```python
parse_answer(self, text: str, parsed) -> object | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L83-L85)

Extract an answer object from a completion; `None` if absent.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
| `parsed` |  | *required* |  |
