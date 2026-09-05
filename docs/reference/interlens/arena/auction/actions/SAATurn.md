# `SAATurn`

One whole SAA turn: the raises and the permanent passes a seat declared together.

```python
SAATurn(bids: tuple = (), passes: tuple = ())
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L84-L101)

**Inherits from:** [Action](../../actions/Action.md)

The reviewed action grammar lets a bidder raise on any number of lots and pass permanently on any number
of lots in a single turn, so an SAA turn is not one move but a SET of them, and the set has to be
validated as a unit (its total is what the budget binds on, and a lot may not appear in both halves).
:func:`parse_auction_action` deliberately validates exactly one binding move and therefore does not read
this shape; the scenario parses the list and folds each :class:`Bid` / :class:`PassLot` into the ledger
individually, so the ledger's purity property is untouched.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bids` | `tuple` | `()` |  |
| `passes` | `tuple` | `()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `bids` | `tuple` |  |
| `kind` | `str` |  |
| `passes` | `tuple` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L99-L101)
