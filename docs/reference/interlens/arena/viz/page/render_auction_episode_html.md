# `render_auction_episode_html`

One self-contained interactive page for one auction episode.

```python
render_auction_episode_html(payload: dict) -> str
```

Defined in [`interlens.arena.viz.page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/page.py#L761-L813)

Sections, in order: the auction summary strip; the census strip; the staged bid ladder; the per-lot
allocation strip; the winner/payment/surplus panel; the message graph; the per-turn counterfactual table;
the system-prompt audit; and the transcript. The side panel carries the mechanism, the five public cards,
the lot catalogue, the per-stage private draws, the public chat, and the reading guide.

Reached through :func:`render_episode_html`, so a caller never has to know which kind of episode it holds.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
