# `make_coherent`

The RNG-neutral coherence permutation: a persona's own-best slot is never one its public attributes point away from (design.md §2.2, the `scenarios/priors.py::_make_role_coherent` analogue).

```python
make_coherent(eps: np.ndarray, affinity: np.ndarray) -> np.ndarray
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L261-L285)

For each bidder independently: if its largest idiosyncrasy sits on a slot whose affinity `a_i . w_j` is
strictly negative — a slot the persona publicly disfavors — that idiosyncrasy is SWAPPED with the one on
the bidder's highest-affinity slot. The operation is a permutation within the bidder's own row, so the
realized value multiset is unchanged and the draw stays RNG-neutral; and it only ever moves the argmax
TOWARD a favored slot, so it reinforces rather than destroys the persistent affinity structure.

Design note (a resolved ambiguity): design.md describes this as permuting slot LABELS once per instance.
Relabelling slots is vacuous here — a slot's identity IS its loading vector, so permuting the labels
permutes `w_j` and `B_jt` together and leaves every affinity unchanged. Applying the swap per stage to
`eps` is the operation that actually delivers the stated property, and the design's stated reason for
"once per instance" (not destroying persistent affinity) is satisfied by construction, since the swap is
monotone toward affinity.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `eps` | `np.ndarray` | *required* |  |
| `affinity` | `np.ndarray` | *required* |  |
