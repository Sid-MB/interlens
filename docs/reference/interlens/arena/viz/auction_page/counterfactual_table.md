# `counterfactual_table`

Every committed turn beside what the two computable rules would have played there.

```python
counterfactual_table(auction: dict, payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L471-L519)

This is the "what I want to see" requirement made concrete for auctions: for each turn, the seat's actual
move, the information-conditional Bayesian bidder's move at that same state, and the omniscient bidder's.
Both are arithmetic given the spec, so both are present on every turn of **every** arm, `all_llm`
included — that is what makes the LLM's move comparable to the rules rather than only to other LLMs.

The agreement column is the headline read: in a dominant-strategy mechanism the rational move is
budget-capped truthful bidding, and a table of agreements says the seats found it. Message turns carry no
binding move and are omitted rather than shown as agreements on nothing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `auction` | `dict` | *required* |  |
| `payload` | `dict` | *required* |  |
