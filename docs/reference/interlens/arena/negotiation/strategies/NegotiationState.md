# `NegotiationState`

The structured state a `Policy` reads to compute its next action — the machine-readable counterpart of the text `view` an LLM seat reads, so a `PolicyParticipant` and an LLM participant are interchangeable seats.

```python
NegotiationState(
	seat: int,
	sheet: ScoreSheet,
	space: DealSpace,
	round: int = 1,
	deadline: int = 1,
	offers: dict = dict(),
	standing: str | None = None,
	received: list = list(),
	received_by_opponent: dict = dict(),
	my_offers: list = list(),
	discount: float = 1.0,
	tables: GameTables | None = None,
	opponents: tuple = (),
	must_vote: bool = False,
	min_accept: int | None = None,
	veto_seats: tuple = (),
	offer_proposers: dict = dict(),
	offer_accepts: dict = dict(),
	offer_rejects: dict = dict(),
	walked_seats: tuple = (),
)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L66-L187)

Attributes
----------
seat : int
    This policy's seat index.
sheet : ScoreSheet
    This seat's private score sheet.
space : DealSpace
    The shared deal space.
round : int
    Current round (1-indexed).
deadline : int
    Total number of rounds `T` (turn-count deadline, restated every turn).
offers : dict[str, Deal]
    Live offer registry: `offer_id -> deal`.
standing : str | None
    The offer id this seat is being asked to respond to (most recent live offer), if any.
received : list[Deal]
    Opponent-proposed deals in order (feeds MiCRO / tit-for-tat / belief updates).
received_by_opponent : dict[int, list[Deal]]
    The same public opponent offers, preserving proposer seat identity. Bayesian opponent modelling uses
    this mapping; `received` remains the pooled compatibility view for policies that do not.
my_offers : list[Deal]
    This seat's own past proposals in order.
discount : float
    Per-round discount / breakdown-risk `delta` (1.0 = none).
tables : GameTables | None
    Optional cached tables for the full game (only available under full information).
opponents : tuple[int, ...]
    Seat indices of the other parties.
must_vote : bool
    True on a vote-only turn (the scenario's forced-final phase): the seat may ONLY accept/reject/walk the
    standing offer, not propose. Policies read this and cast a terminal individually-rational vote
    (accept any offer that clears their threshold, since the only alternative is no-deal = 0). Proposing
    here is an economic-legality violation, so a proposing policy would otherwise blow the deal.
min_accept : int | None
    Fixed number of original seats whose yes votes pass a deal. `None` preserves unanimity.
veto_seats : tuple[int, ...]
    Seats whose yes votes are required in addition to the numeric quorum.
offer_proposers / offer_accepts / offer_rejects : dict
    Public offer-ledger metadata keyed by offer id, with seat indices as values. This lets quorum-aware
    policies distinguish pivotal from non-pivotal votes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
| `sheet` | [ScoreSheet](../sheets/ScoreSheet.md) | *required* |  |
| `space` | [DealSpace](../space/DealSpace.md) | *required* |  |
| `round` | `int` | `1` |  |
| `deadline` | `int` | `1` |  |
| `offers` | `dict` | `dict()` |  |
| `standing` | `str \| None` | `None` |  |
| `received` | `list` | `list()` |  |
| `received_by_opponent` | `dict` | `dict()` |  |
| `my_offers` | `list` | `list()` |  |
| `discount` | `float` | `1.0` |  |
| `tables` | [GameTables](../oracle_context/GameTables.md) \| None | `None` |  |
| `opponents` | `tuple` | `()` |  |
| `must_vote` | `bool` | `False` |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` | `tuple` | `()` |  |
| `offer_proposers` | `dict` | `dict()` |  |
| `offer_accepts` | `dict` | `dict()` |  |
| `offer_rejects` | `dict` | `dict()` |  |
| `walked_seats` | `tuple` | `()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `deadline` | `int` |  |
| `discount` | `float` |  |
| `final_proposal` | `bool` | Whether this turn is the forced-final PROPOSAL turn, where only propose/accept/walk are legal. |
| `min_accept` | `int \| None` |  |
| `must_vote` | `bool` |  |
| `my_offers` | `list` |  |
| `offer_accepts` | `dict` |  |
| `offer_proposers` | `dict` |  |
| `offer_rejects` | `dict` |  |
| `offers` | `dict` |  |
| `opponents` | `tuple` |  |
| `received` | `list` |  |
| `received_by_opponent` | `dict` |  |
| `round` | `int` |  |
| `seat` | `int` |  |
| `sheet` | [ScoreSheet](../sheets/ScoreSheet.md) |  |
| `space` | [DealSpace](../space/DealSpace.md) |  |
| `standing` | `str \| None` |  |
| `standing_deal` | `Deal \| None` | The deal referenced by `standing` (or None). |
| `tables` | [GameTables](../oracle_context/GameTables.md) \| None |  |
| `time_fraction` | `float` | `(round-1)/deadline` in `[0, 1)` — the `t` used by time-dependent concession curves. |
| `veto_seats` | `tuple` |  |
| `walked_seats` | `tuple` |  |

## Methods {#methods}

## `from_block` {#from_block}

```python
from_block(
	cls,
	block: dict,
	*,
	sheet,
	space,
	tables=None,
	discount: float = 1.0,
	opponents: tuple = (),
	seat: int | None = None,
) -> 'NegotiationState'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L158-L187)

Build a state from a scenario-emitted `negotiation_state` block (see `parse_negotiation_state`) plus the seat-bound context (`sheet`/`space`/`tables`/`discount`/`opponents`).

The block
carries only the dynamic fields — `seat`, `round`, `deadline`, `offers` (`{id: [opt,...]}`),
`standing` (id or null), `received`/`my_offers` (lists of deals), and
`received_by_opponent` (`{seat_index: [deal, ...]}`) — so a `PolicyParticipant` can read the
scenario's authoritative offer registry straight from its view.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `block` | `dict` | *required* |  |
| `sheet` |  | *required* |  |
| `space` |  | *required* |  |
| `tables` |  | `None` |  |
| `discount` | `float` | `1.0` |  |
| `opponents` | `tuple` | `()` |  |
| `seat` | `int \| None` | `None` |  |
