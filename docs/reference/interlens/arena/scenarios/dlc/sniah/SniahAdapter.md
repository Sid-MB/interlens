# `SniahAdapter`

```python
SniahAdapter()
```

Defined in [`interlens.arena.scenarios.dlc.sniah`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/sniah.py#L44-L64)

**Inherits from:** [TaskAdapter](../../longcontext/TaskAdapter.md)

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `discussion_cap` |  |  |
| `final_cap` |  |  |
| `provisional` |  |  |
| `solo_turn_cap` |  |  |
| `task` |  |  |

## Methods {#methods}

## `answer_instructions` {#answer_instructions}

```python
answer_instructions(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/sniah.py#L51-L52)

## `grade` {#grade}

```python
grade(self, answer, payload: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/sniah.py#L61-L64)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `answer` |  | *required* |  |
| `payload` | `dict` | *required* |  |

## `parse_answer` {#parse_answer}

```python
parse_answer(self, text: str, parsed)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/sniah.py#L54-L59)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
| `parsed` |  | *required* |  |
