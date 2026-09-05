# `auction_body`

The auction episode page's four panels plus the counterfactual table, in reading order.

```python
auction_body(payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L713-L728)

Returned as one string for `page.render_episode_html` to place between the shared header and the shared
transcript, so the auction branch of that function stays a handful of lines and the shell, census, vintage
badges and prompt audit are reused rather than re-implemented.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
