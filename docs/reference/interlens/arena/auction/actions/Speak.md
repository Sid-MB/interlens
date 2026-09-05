# `Speak`

Public broadcast cheap talk.

```python
Speak(text: str)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L157-L166)

**Inherits from:** [Action](../../actions/Action.md)

Available only when `channel != "silent"`; carried alongside the
binding move rather than instead of it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `kind` | `str` |  |
| `text` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L165-L166)
