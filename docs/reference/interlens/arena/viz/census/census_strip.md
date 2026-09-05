# `census_strip`

The per-episode census as a compact header strip, always rendered when there are turns to count.

```python
census_strip(census: dict | None) -> str
```

Defined in [`interlens.arena.viz.census`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/census.py#L126-L156)

Present even when everything is zero, because "this episode has no silent turns" is the claim a reader needs
and an absent strip cannot make it. Non-zero counts are styled as hazards and every cell carries its
by-round breakdown on hover.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `census` | `dict \| None` | *required* |  |
