# `spec`

Module `interlens.arena.auction.spec`

The frozen auction specification: item slots, bidders, per-stage draws, and the mechanism config.

The sibling of `negotiation/sheets.py::GameSpec` — one object carrying everything a repeated-auction episode
needs, round-tripping through a plain JSON dict so it drops straight into an arena `Instance.payload` and
back. `DealSpace` deliberately does NOT transfer: bids are effectively continuous and multi-item allocation
is combinatorial, so the full-enumeration assumption in `utility_matrix`/`feasible_mask` breaks
(design.md §2.1).

Structure of the object, per design.md §2.1 and §2.4:

- **persistent** across all `T` stages — :class:`ItemSlot` identities and their attribute loadings `w_j`,
  the five :class:`BidderSpec` personas with their PUBLIC attribute vectors `a_i`, capacities, synergy and
  decay rates, resale weights; the mechanism; the channel;
- **redrawn** each stage into a :class:`StageDraw` — base values `B_jt`, the private shifters `z_it`, the
  per-item idiosyncrasies `eps_ijt`, realized whole-number valuations, budgets, synergy target sets, resale
  values and signals, and the seeded tie-break permutation.

The generative model itself (the `ell_ijt` equation of design.md §2.2) lives in exactly one place,
:func:`~interlens.arena.auction.priors.realize_values`; :func:`generate_spec` composes it with the persona
table and the coherence permutation. Every constant of the environment (base-value range, default variances,
default mechanism parameters) is defined here and nowhere else.

Example:

```python
spec = generate_spec(seed=7, mechanism=Mechanism.sealed(pricing="second_price"),
                     value_structure="apv", n_items=1, horizon=8, channel="dm")
spec.stage(1).values[0]              # bidder 0's whole-number valuations at stage 1
AuctionSpec.from_json(spec.to_json()) == spec      # exact round-trip
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `BANK_STAGES` | `int` |  |
| `BASE_VALUE_RANGE` | `tuple[int, int]` |  |
| `CHANNELS` | `tuple[str, ...]` |  |
| `DEFAULT_BETA` | `float` |  |
| `DEFAULT_BID_GRANULARITY` | `int` |  |
| `DEFAULT_CLOCK_ROUND_CAP` | `int` |  |
| `DEFAULT_DM_CAP` | `int` |  |
| `DEFAULT_INCREMENT` | `int` |  |
| `DEFAULT_RESERVE` | `int` |  |
| `DEFAULT_SIGMA_EPS` | `float` |  |
| `DEFAULT_SIGMA_NU` | `float` |  |
| `DEFAULT_SIGMA_Z` | `float` |  |
| `DEFAULT_TALK_ROUNDS` | `int` |  |
| `DM_CHANNELS` | `tuple[str, ...]` |  |
| `ESCROW_CHANNELS` | `tuple[str, ...]` |  |
| `FAMILIES` | `tuple[str, ...]` |  |
| `N_BIDDERS` | `int` |  |
| `PRICING_BY_FAMILY` | `dict[str, tuple[str, ...]]` |  |
| `PUBLIC_CARD_FIELDS` | `tuple[str, ...]` |  |
| `SAA_ROUND_CAP_LARGE` | `int` |  |
| `SAA_ROUND_CAP_SMALL` | `int` |  |
| `SYNERGY_TARGET_LARGE_THRESHOLD` | `int` |  |
| `SYNERGY_TARGET_SIZE_LARGE` | `int` |  |
| `SYNERGY_TARGET_SIZE_SMALL` | `int` |  |
| `TRANSFER_CHANNELS` | `tuple[str, ...]` |  |
| `VALUE_STRUCTURES` | `tuple[str, ...]` |  |

## Classes

| Name | Summary |
|---|---|
| [`AuctionSpec`](AuctionSpec.md) | A complete repeated-auction episode specification (design.md §2.1). |
| [`BidderSpec`](BidderSpec.md) | One seat's persistent structure. |
| [`ItemSlot`](ItemSlot.md) | One lot in the catalogue. |
| [`Mechanism`](Mechanism.md) | The auction format as a CONFIG, never a separate runner (design.md §3). |
| [`RingSpec`](RingSpec.md) | An instructed bidding ring: which seats are in it, and whether the instruction is given in the prompt. |
| [`StageDraw`](StageDraw.md) | One stage's realized draws — everything that redraws from the same persona priors (design.md §2.4). |

## Functions

| Name | Summary |
|---|---|
| [`card_scramble_seed`](card_scramble_seed.md) | The frozen scramble seed for one bank instance, derived from its `instance_id`. |
| [`derangement`](derangement.md) | A seeded permutation of `0..n-1` with NO fixed point: `perm[i] != i` for every `i`. |
| [`generate_spec`](generate_spec.md) | Generate a complete :class:`AuctionSpec` deterministically from `seed`. |
| [`scramble_public_cards`](scramble_public_cards.md) | X1: permute the five PUBLIC CARDS across the seats under a seeded derangement, keeping every draw. |
| [`synergy_target_size`](synergy_target_size.md) | Size of the private synergy target SET at `n_items` lots: a pair below :data:`SYNERGY_TARGET_LARGE_THRESHOLD` lots, a triple at or above (design.md §2.2). |
