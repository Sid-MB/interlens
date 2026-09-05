# `OpenAIClient`

OpenAI directly via the `openai` SDK (`provider="openai"`).

```python
OpenAIClient()
```

Defined in [`interlens.participant.participants.api_client`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L389-L440)

**Inherits from:** `_OpenAICompatClient`

Reads `OPENAI_API_KEY`. Supports the
asynchronous **Batch API** for large rollouts.

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L397-L440)

OpenAI **Batch API**: upload a JSONL of `/v1/chat/completions` requests (positional `custom_id`), `batches.create` with a 24h window, poll until `status == 'completed'`, then download + parse the output file back into input order.

A failed/expired/cancelled batch raises.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `requests` | `list[dict]` | *required* |  |
| `poll_interval` | `float` | `30.0` |  |
