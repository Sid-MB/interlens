# `Mail`

One mailbox item.

```python
Mail(
	sender: str,
	recipient: str,
	content: str,
	priority: str = 'normal',
	sent_at_turn: int = 0,
	read: bool = False,
)
```

Defined in [`interlens.communication.messaging`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L63-L75)

`read` flips when the recipient reads; delivered mail renders into its views.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sender` | `str` | *required* |  |
| `recipient` | `str` | *required* |  |
| `content` | `str` | *required* |  |
| `priority` | `str` | `'normal'` |  |
| `sent_at_turn` | `int` | `0` |  |
| `read` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `content` | `str` |  |
| `priority` | `str` |  |
| `read` | `bool` |  |
| `recipient` | `str` |  |
| `sender` | `str` |  |
| `sent_at_turn` | `int` |  |

## Methods {#methods}

## `to_dict` {#to_dict}

```python
to_dict(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L73-L75)
