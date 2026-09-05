# `generate_spec`

Generate a complete :class:`AuctionSpec` deterministically from `seed`.

```python
generate_spec(
	seed: int,
	*,
	mechanism: Mechanism,
	value_structure: str = 'apv',
	horizon: int = BANK_STAGES,
	channel: str = 'silent',
	talk_rounds: int = DEFAULT_TALK_ROUNDS,
	dm_cap: int = DEFAULT_DM_CAP,
	beta: float = DEFAULT_BETA,
	sigma_z: float = DEFAULT_SIGMA_Z,
	sigma_eps: float = DEFAULT_SIGMA_EPS,
	sigma_nu: float = DEFAULT_SIGMA_NU,
	persona_order: tuple[int, ...] | None = None,
	coherent: bool = True,
	disclose_public_facts: bool = False,
	framing: str = 'datacenter',
	ring: RingSpec | None = None,
	meta: dict | None = None,
) -> AuctionSpec
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L664-L801)

The generator implements design.md §2.2 exactly, with the value equation itself living in
:func:`~interlens.arena.auction.priors.realize_values` so there is one copy of it.

Parameters
----------
seed : int
    The instance seed. Two calls with the same seed and the same arguments produce byte-identical JSON.
mechanism : Mechanism
    The format config; its `n_items` fixes the catalogue size.
value_structure : str
    `"ipv"` / `"apv"` / `"interdep"`. The switch is applied AFTER the latent draws, so the `eps`
    stream is identical across structures at a fixed seed — which is what makes O1 <-> O2 a within-bank
    paired contrast rather than two populations (design.md §7.1).
horizon : int
    Number of stage draws to generate. Bank instances use :data:`BANK_STAGES`; a cell consumes a prefix
    via :meth:`AuctionSpec.prefix`.
channel, talk_rounds, dm_cap : str, int, int
    Communication affordances, passed through to the spec.
beta, sigma_z, sigma_eps, sigma_nu : float
    Public structural constants; `beta` and `sigma_z` are forced to 0 under IPV.
persona_order : tuple[int, ...] | None
    Permutation of :data:`~interlens.arena.auction.priors.PERSONAS` indices onto seats 0..4. `None`
    draws one from `seed`, which is how persona/seat identity varies across the bank while the five
    archetypes stay fixed. The persona-scrambled control X1 does NOT use this: it keeps the draws and
    permutes the CARDS, via :func:`scramble_public_cards`, which is applied to a bank instance at cell
    time rather than at generation time so X1 and O1 read the SAME frozen draws.
coherent : bool
    Apply the once-per-instance coherence permutation (design.md §2.2, the `_make_role_coherent`
    analogue): a persona's expected-argmax slot is never one its public attributes point away from. The
    permutation moves `eps` labels only, so the realized value multiset is unchanged and the draw stays
    RNG-neutral.
disclose_public_facts, framing, ring, meta
    Passed through to the spec unchanged.

Returns
-------
AuctionSpec
    A validated spec with `horizon` stage draws.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seed` | `int` | *required* |  |
| `mechanism` | [Mechanism](Mechanism.md) | *required* |  |
| `value_structure` | `str` | `'apv'` |  |
| `horizon` | `int` | `BANK_STAGES` |  |
| `channel` | `str` | `'silent'` |  |
| `talk_rounds` | `int` | `DEFAULT_TALK_ROUNDS` |  |
| `dm_cap` | `int` | `DEFAULT_DM_CAP` |  |
| `beta` | `float` | `DEFAULT_BETA` |  |
| `sigma_z` | `float` | `DEFAULT_SIGMA_Z` |  |
| `sigma_eps` | `float` | `DEFAULT_SIGMA_EPS` |  |
| `sigma_nu` | `float` | `DEFAULT_SIGMA_NU` |  |
| `persona_order` | `tuple[int, ...] \| None` | `None` |  |
| `coherent` | `bool` | `True` |  |
| `disclose_public_facts` | `bool` | `False` |  |
| `framing` | `str` | `'datacenter'` |  |
| `ring` | [RingSpec](RingSpec.md) \| None | `None` |  |
| `meta` | `dict \| None` | `None` |  |
