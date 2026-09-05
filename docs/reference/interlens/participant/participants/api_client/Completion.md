# `Completion`

A completion string that also carries the call's **usage telemetry** as attributes: `input_tokens` / `output_tokens` (0 when the provider reported none), `stop_reason` (the provider's native stop/finish reason, `None` when unreported), `batched` (served via a provider batch API at discount pricing), `cache_read_tokens` / `cache_write_tokens` (Anthropic prompt-cache accounting: tokens served from a cache entry, and tokens written into one — both EXCLUDED from `input_tokens`, which is the full-price remainder), and the call's **reasoning record**: `reasoning` (whatever reasoning text the provider returned — Anthropic thinking blocks including summarized ones, OpenAI-compatible `reasoning`/`reasoning_content` fields — or `None`) with `reasoning_provenance` marking how complete that record is (see the marker constants above).

```python
Completion()
```

Defined in [`interlens.participant.participants.api_client`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L42-L91)

**Inherits from:** `str`

OpenAI-compatible responses also preserve `upstream_provider`, `response_model`, and
`generation_id` when reported; these make OpenRouter routing auditable.

Subclassing `str` keeps the documented client contract — `callable(...) -> str` — fully intact for
existing callers and injected test clients, while letting `APIParticipant` read the telemetry off the
return value to record per-turn usage (`Message.metadata`) and report into a `UsageMeter`.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `batched` | `bool` |  |
| `cache_read_tokens` | `int` |  |
| `cache_write_tokens` | `int` |  |
| `generation_id` | `str \| None` |  |
| `input_tokens` | `int` |  |
| `output_tokens` | `int` |  |
| `reasoning` | `str \| None` |  |
| `reasoning_provenance` | `str` |  |
| `reasoning_tokens` | `int` |  |
| `response_model` | `str \| None` |  |
| `stop_reason` | `str \| None` |  |
| `upstream_provider` | `str \| None` |  |
