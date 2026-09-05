# `SendMessageTool`

Native-tool surface for sending: `send_message(content, recipient, priority)`.

```python
SendMessageTool(policy: 'MessagingPolicy', sender: str)
```

Defined in [`interlens.communication.messaging`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L78-L100)

**Inherits from:** [Tool](../../tools/tool/Tool.md)

Bound to one sender.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `policy` | `'MessagingPolicy'` | *required* |  |
| `sender` | `str` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |
| `schema` | `dict` |  |
