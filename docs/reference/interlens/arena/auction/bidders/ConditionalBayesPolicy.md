# `ConditionalBayesPolicy`

The headline rational seat: a **stage-myopic information-conditional Bayes response**.

```python
ConditionalBayesPolicy()
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L585-L627)

**Inherits from:** [AuctionPolicy](AuctionPolicy.md)

What "conditional" means here, format by format:

- **second-price / English under IPV or APV** — values are private, so bidding one's own value stays
  weakly dominant and no belief enters. The policy returns the own value, and the fact that this
  coincides with :class:`TruthfulPolicy` is a property of the mechanism, not a shortcut.
- **second-price / English under INTERDEP** — the value depends on a common component about which
  rivals hold information, so the bid is `E[v | own signal, own signal is the highest]`
  (:func:`~.benchmarks.expected_value_given_winning`), which is strictly below the naive
  signal-as-value bid. This is the winner's-curse conditioning, and the tests assert the shading engages.
- **Dutch / first-price** — the myopic best response on the integer bid grid against the rivals'
  CONDITIONED posteriors, i.e. `argmax_b (v - b) * P(all rivals below b)`. That is a best response,
  not the fixed point :class:`RNNEPolicy` solves; the distinction is deliberate and is what makes this
  seat's behavior a decision rule rather than an equilibrium assumption.
- **SAA / multi-unit** — capacity- and synergy-aware straightforward bidding inherited from the ABC.

Within a stage it updates on the public events the format reveals — exits, standing bids, and remaining
activity — through :meth:`AuctionPolicy._conditioned`. Across stages it updates on NOTHING: its stage-`t`
move is independent of stages `1..t-1` given stage-`t` values, which is the property G3's repeated-tier
extension tests directly.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `bid_for` {#bid_for}

```python
bid_for(self, state: AuctionState, item: int) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L610-L627)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `item` | `int` | *required* |  |
