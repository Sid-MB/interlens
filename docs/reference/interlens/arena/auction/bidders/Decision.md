# `Decision`

A policy's verdict on a proposal, with the arithmetic that produced it exposed as reason slots.

```python
Decision(accept: bool, reason: str, detail: dict = dict())
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L205-L228)

`reason` is one of a small closed vocabulary (`"matches_best_response"`,
`"dominated_by_best_response"`, `"exceeds_capacity"`, `"below_reservation"`,
`"unenforceable"`), and `detail` carries the numbers behind it, so the templated DM reply states WHY
in the seat's own terms and an analysis can read the decision without parsing prose.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `accept` | `bool` | *required* |  |
| `reason` | `str` | *required* |  |
| `detail` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accept` | `bool` |  |
| `detail` | `dict` |  |
| `reason` | `str` |  |

## Methods {#methods}

## `sentence` {#sentence}

```python
sentence(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L218-L228)

The one-line natural-language form the templated DM reply publishes.

Numbers only — never a
private valuation, which would leak through the microphone the design deliberately hands policy
seats.
