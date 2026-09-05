# `preference_visibility`

The compact index label for a negotiation's information condition.

```python
preference_visibility(payload: dict) -> str
```

Defined in [`interlens.arena.viz.page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/page.py#L115-L121)

Private information is the protocol default, including older records that did not serialize `info`;
the exceptional public/shared spellings are normalized to the experiment-facing label `FULL`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
