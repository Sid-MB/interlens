# `default_model_id`

Which model a seat that has just become an `llm` seat is pre-selected to.

```python
default_model_id(models: Any) -> str
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L83-L102)

The provider decides, by flagging one :class:`ModelInfo` with `default=True` — the lobby must not know the
name of anybody's favourite model, and an id hardcoded in the page would be a second place to edit every time
the frontier moves. Preference order, ties broken by list order: the flagged model if it can be used, then
any model that can be used, then the flagged one anyway, then the first entry. Pre-selecting a model whose
key is missing over one that would actually run is the one case where honouring the flag helps nobody, and
the flag still wins when NOTHING is usable, so a lobby with no credential still opens on the right name (and
on the "no Anthropic credential" reason next to it). `""` when there is nothing to offer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `models` | `Any` | *required* |  |
