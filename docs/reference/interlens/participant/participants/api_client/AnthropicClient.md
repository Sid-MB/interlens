# `AnthropicClient`

Claude via the `anthropic` SDK (the default provider).

```python
AnthropicClient(**kwargs={})
```

Defined in [`interlens.participant.participants.api_client`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L200-L322)

**Inherits from:** `_RetryingClient`

Uses Anthropic's separate `system` param.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `kwargs` |  | `{}` |  |

## Methods {#methods}

## `submit_batch` {#submit_batch}

```python
submit_batch(
	self,
	requests: list[dict],
	*,
	poll_interval: float = 30.0,
) -> 'list[Completion]'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L290-L322)

Anthropic **Message Batches API**: one `messages.batches.create` submits every request (tagged with a positional `custom_id`), then poll `retrieve` until `processing_status == 'ended'` and stream `results` back, reassembled into input order.

A non-succeeded per-request result raises.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `requests` | `list[dict]` | *required* |  |
| `poll_interval` | `float` | `30.0` |  |
