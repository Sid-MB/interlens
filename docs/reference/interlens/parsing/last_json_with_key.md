# `last_json_with_key`

The LAST fenced JSON OBJECT in `text` carrying at least one of `keys` at top level, else `None`.

```python
last_json_with_key(text: str | None, *keys: str = ()) -> dict | None
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L110-L127)

:func:`last_json` takes the last parseable object whatever it holds; this takes the last one that *answers a
specific question*, skipping past trailing blocks that don't (a model's closing summary fence, a scenario's
own status block). "Last wins" for the same reason: a later block supersedes an earlier one.

Backs the negotiation stack's two structured channels — a seat's action object
(`last_json_with_key(text, "action", "proposal", "deal")`) and the scenario's authoritative state block
(`last_json_with_key(text, "negotiation_state")`) — so neither carries a fence regex of its own.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
| `keys` | `str` | `()` |  |
