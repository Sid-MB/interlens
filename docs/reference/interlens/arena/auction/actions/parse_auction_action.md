# `parse_auction_action`

Read and validate ONE binding auction move — the single consolidated entry point, the sibling of `arena.actions.parse_action`.

```python
parse_auction_action(
	text: str | None,
	*,
	family: str,
	item_names: tuple[str, ...],
	standing: list[int] | None = None,
	increment: int = 1,
	granularity: int = 1,
	reserve: int = 0,
	budget: int | None = None,
	n_units: int = 1,
	eligible=None,
	clock_price: int | None = None,
) -> ParseResult
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L618-L722)

Distinguishes :data:`~interlens.arena.actions.SYNTAX` (no well-formed move could be read: absent JSON,
unknown kind, unknown lot name, non-whole amount) from :data:`~interlens.arena.actions.LEGALITY` (a
well-formed move that the mechanism forbids: below the standing bid plus increment, off the bid
granularity, above the seat's budget, on a lot it has already passed, a non-monotone schedule), so a
scenario can retry once with the parser's own message and log the two classes separately as data
[chen2023_aucarena].

**Bidding above your own valuation is neither** — it parses cleanly and is counted downstream as an
economic error (design.md §3.2), which is why this function never sees the seat's values.

Parameters
----------
text : str | None
    The model's raw turn.
family : str
    The mechanism family, which fixes the legal move kinds.
item_names : tuple[str, ...]
    Display names of the lots, in slot order; a move may name a lot by name or by index.
standing : list[int] | None
    Current standing high price per lot (`None` = no bids yet, treated as `reserve`).
increment, granularity, reserve : int
    Mechanism parameters; a bid must be at least `standing + increment` (or `reserve`) and a multiple
    of `granularity`.
budget : int | None
    The seat's remaining stage budget; a bid above it is a LEGALITY error (payments must be collectible).
n_units : int
    Units on offer, for the multi-unit families.
eligible : Callable[[int], bool] | None
    Predicate on lot index under the activity rule; a bid on an ineligible lot is a LEGALITY error.
clock_price : int | None
    The current clock price, for the clock families.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
| `family` | `str` | *required* |  |
| `item_names` | `tuple[str, ...]` | *required* |  |
| `standing` | `list[int] \| None` | `None` |  |
| `increment` | `int` | `1` |  |
| `granularity` | `int` | `1` |  |
| `reserve` | `int` | `0` |  |
| `budget` | `int \| None` | `None` |  |
| `n_units` | `int` | `1` |  |
| `eligible` |  | `None` |  |
| `clock_price` | `int \| None` | `None` |  |
