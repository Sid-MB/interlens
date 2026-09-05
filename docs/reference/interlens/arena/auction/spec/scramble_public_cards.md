# `scramble_public_cards`

X1: permute the five PUBLIC CARDS across the seats under a seeded derangement, keeping every draw.

```python
scramble_public_cards(spec: AuctionSpec, *, seed: int) -> AuctionSpec
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L843-L901)

What moves is the whole card as one unit -- :data:`PUBLIC_CARD_FIELDS`, i.e. the persona prose (keyed by
`persona_id`), the printed public attribute vector `a_i`, and the public per-seat figures beside it.
Seat `i` presents as, and *is*, the organization whose card it holds: the addressable seat id, the
roster entry, the "your seat" line, and every mechanic the card states (capacity limit, adjacency
premium, decay) are the card's, so nothing a bidder reads contradicts anything else it reads.

What does NOT move is every seat's PRIVATE block -- its realized valuations, its budget, its synergy
target set, its resale signals, and the tie-break permutation -- because those live on
:class:`StageDraw`, which this function does not touch. **Valuations are not redrawn.** The scramble
therefore breaks exactly one thing: the mapping from the public card to the valuation it used to
describe. Persona text is still present at every seat (which is what controls Jia et al.'s
persona-shifts-competence confound), and it is now uninformative about the draw (which is what destroys
the prior's information content, the thing G2(b) tests O1 against).

The computable free arms run under this too, and their posteriors are then systematically wrong, since a
rational bidder forms them from the public attribute matrix. That is the intended reading, not a defect:
it prices what the public prior was worth to a bidder that used it correctly.

Parameters
----------
spec : AuctionSpec
    The instance spec, already at the cell's mechanism / horizon / channel.
seed : int
    The derangement seed; use :func:`card_scramble_seed` on the instance id so it is frozen with the bank.

Returns
-------
AuctionSpec
    A new spec with permuted cards and a `meta["card_scramble"]` provenance block recording the
    derangement, the seed, and which fields moved.

Raises
------
ValueError
    Under `interdep`, where `gamma` selects which seat receives the stage's resale signals: moving the
    published resale weight away from the seat holding the signals would be a half-scramble across the
    public/private line, so the control is refused rather than approximated. X1 is an `apv` cell.

Example:

```python
spec = scramble_public_cards(spec, seed=card_scramble_seed(instance.instance_id))
spec.meta["card_scramble"]["derangement"]      # e.g. [2, 3, 4, 0, 1]
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` | [AuctionSpec](AuctionSpec.md) | *required* |  |
| `seed` | `int` | *required* |  |
