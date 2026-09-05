# `Transfer`

A side payment the harness EXECUTES at settlement.

```python
Transfer(to: str, amount: int, condition: str | None = None)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L193-L217)

**Inherits from:** [Action](../../actions/Action.md)

Available only at a transfer rung; that switch is
the strong-cartel / weak-cartel contrast [mcafee_mcmillan1992, pp. 582-589], because under plain `dm` a
promise to pay is words and nothing more.

`condition` makes the payment CONTINGENT, and it exists because the unconditional form was measured and
found to be dominated. Reading the ring smoke's scratchpads, the seats priced the instrument and rejected
it correctly, 28 times in as many words — *"non-binding standdown + binding transfer = pure loss"*,
*"transfers are pure gifts"*, *"no transfer — unconditional, no value"*. An unconditional payment buys a
promise the recipient has no obligation to keep, so paying is strictly worse than not paying and the
strong-cartel case was never actually on the table. With `condition="recipient_wins_nothing"` the
auctioneer pays only if the recipient took no lot, which is what makes standing down PURCHASABLE and is
the instrument McAfee-McMillan's knockout requires.

`None` is the unconditional form, retained rather than replaced: it is now a theory-confirmed control
arm, and the channel ladder's rule is that each rung adds a capability and removes none.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `to` | `str` | *required* |  |
| `amount` | `int` | *required* |  |
| `condition` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `amount` | `int` |  |
| `condition` | `str \| None` |  |
| `kind` | `str` |  |
| `to` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L216-L217)
