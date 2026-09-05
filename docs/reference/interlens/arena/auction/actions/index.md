# `interlens.arena.auction.actions`

The auction move vocabulary, the bid ledger, and DM routing (design.md §12 item 2).

This module EXTENDS `arena/actions.py` rather than editing it: the negotiation move vocabulary
(`Propose`/`Accept`/`Reject`/`Walk`) is untouched, and the shared machinery it already owns —
:class:`~interlens.arena.actions.Action`, :class:`~interlens.arena.actions.ParseResult`, and the
:data:`~interlens.arena.actions.SYNTAX` / :data:`~interlens.arena.actions.LEGALITY` error classes that drive
retry-once-with-specific-feedback — is imported and reused.

Three pieces, mirroring the negotiation layer one for one:

- **The action dataclasses** — one per row of design.md §3.3's action grammar, plus the three side-channel
  moves (:class:`Speak`, :class:`DirectMessage`, :class:`Transfer`) that ride alongside the binding move in
  the four-channel envelope of §3.2.
- **:class:`BidLedger`** — the sibling of `OfferRegistry`: monotonic ids, standing-high tracking per lot,
  irrevocable exits, and the eligibility ratchet, all as a PURE FUNCTION of the action sequence, so replay
  reconstructs the ledger exactly and an analysis never has to trust a stored summary.
- **:class:`DMRouter`** — delivers addressed messages to their recipients only, enforces `dm_cap`, and
  records the full directed graph (sender, recipient, stage, round, text) that the DM-graph panel and the
  per-dyad mutual-information estimator both read.

Economic errors are MEASURED, never blocked (design.md §3.2): bidding above your own valuation parses
cleanly and is counted downstream. Bidding above BUDGET is different — payments must be collectible — so it
is a :data:`~interlens.arena.actions.LEGALITY` error here, retried once and then truncated by the scenario.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `LEGAL_KINDS` | `dict[str, tuple[str, ...]]` |  |
| `TRANSFER_CONDITIONS` | `tuple[str, ...]` |  |
| `resolve_item` |  |  |
| `whole_number` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Bid`](Bid.md) | A priced bid of `amount` on lot `item` (a slot index). |
| [`BidLedger`](BidLedger.md) | Monotonic bid ids, standing-high tracking, exits, and the eligibility ratchet. |
| [`Claim`](Claim.md) | Take the lot at the current descending-clock price (Dutch). |
| [`DMRouter`](DMRouter.md) | Delivers addressed private messages to their recipients only, and records the directed graph. |
| [`Demand`](Demand.md) | A demand for `units` at the current clock price in a clinching stage; must be weakly decreasing across rounds [ausubel2004]. |
| [`DirectMessage`](DirectMessage.md) | A private message to named recipients. |
| [`DirectMessageRecord`](DirectMessageRecord.md) | One delivered private message. |
| [`Exit`](Exit.md) | Leave the ascending clock. |
| [`PassLot`](PassLot.md) | Decline to bid on lot `item` this round. |
| [`SAATurn`](SAATurn.md) | One whole SAA turn: the raises and the permanent passes a seat declared together. |
| [`Schedule`](Schedule.md) | A weakly-decreasing per-unit bid vector for a uniform-price stage. |
| [`Speak`](Speak.md) | Public broadcast cheap talk. |
| [`StandingBid`](StandingBid.md) | One registered bid and its live state — the sibling of `arena.actions.Offer`. |
| [`Stay`](Stay.md) | Remain active at the current ascending-clock price (English). |
| [`Transfer`](Transfer.md) | A side payment the harness EXECUTES at settlement. |
| [`TransferBook`](TransferBook.md) | Declared side payments, and their execution at settlement (`dm_transfers` only). |
| [`TurnEnvelope`](TurnEnvelope.md) | One turn's four channels (design.md §3.2), separated: the private `scratchpad` (never published), public `message`, addressed `dms`, an optional `transfer`, and the one binding `action`. |
| [`Wait`](Wait.md) | Let the descending clock fall one increment (Dutch). |

## Functions

| Name | Summary |
|---|---|
| [`auction_action_from_json`](auction_action_from_json.md) | Reconstruct a typed auction :class:`Action` from its stored dict — the inverse of `to_json`. |
| [`parse_auction_action`](parse_auction_action.md) | Read and validate ONE binding auction move — the single consolidated entry point, the sibling of `arena.actions.parse_action`. |
| [`parse_envelope`](parse_envelope.md) | Split a turn's fenced JSON object into its four channels WITHOUT validating the binding move. |
