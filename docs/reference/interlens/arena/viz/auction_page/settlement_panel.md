# `settlement_panel`

Winner, payment and surplus per stage, with the episode total — what replaces `chrome.summary_strip`'s negotiation field list.

```python
settlement_panel(auction: dict, payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L319-L374)

Its `stat()` cell builder is reused verbatim; none of the fields are, because an auction has no deal, no
threshold and no Nash product. What it does have is a benchmark, so every revenue figure is printed beside
the benchmark revenue it is measured against, and a stage whose benchmark is undefined (an on-path SAA
demand has no counterfactual outcome) prints an em dash there rather than a ratio nobody can compute.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `auction` | `dict` | *required* |  |
| `payload` | `dict` | *required* |  |
