# `Proposal`

A division or price proposal arriving over the DM channel, in the machine-readable form a policy seat can actually evaluate.

```python
Proposal(
	proposer: int,
	assignment: dict | None = None,
	item: int | None = None,
	price: int | None = None,
	text: str = '',
)
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L190-L202)

`assignment` maps seat index -> the lots that seat is asked to take (a market division); `price` is
the level the proposal asks bidders to hold to on `item`. A proposal may carry either or both.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `proposer` | `int` | *required* |  |
| `assignment` | `dict \| None` | `None` |  |
| `item` | `int \| None` | `None` |  |
| `price` | `int \| None` | `None` |  |
| `text` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `assignment` | `dict \| None` |  |
| `item` | `int \| None` |  |
| `price` | `int \| None` |  |
| `proposer` | `int` |  |
| `text` | `str` |  |
