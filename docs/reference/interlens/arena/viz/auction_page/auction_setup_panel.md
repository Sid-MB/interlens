# `auction_setup_panel`

The side panel: the mechanism, the five public cards, the lot catalogue, and every stage's frozen draw.

```python
auction_setup_panel(payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L572-L662)

The draws are the whole private half of the episode, so the panel leads with the fact that reading it is a
post-hoc act and states the card scramble where one was applied — an X-cell page whose panel did not say
the cards were deranged would show a reader a persona/value pairing that no seat ever faced.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
