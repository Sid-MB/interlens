# `Action`

Base class for the four formal moves.

```python
Action()
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L70-L78)

`kind` is the wire tag; `to_json` is the canonical surface a
model emits inside a fenced `{"action": ...}` object.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `kind` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L77-L78)
