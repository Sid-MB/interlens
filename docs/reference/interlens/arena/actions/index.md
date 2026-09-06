# `actions`

Module `interlens.arena.actions`

Typed formal-action layer for structured negotiation turns.

A scenario that wants *binding moves* (not just free text) gives each turn one formal action drawn from the
package-deal protocol — `Propose` a complete deal (which the registry stamps with a monotonic `offer_id`),
`Accept` / `Reject` a specific live offer by id, or `Walk` (an explicit no-deal exit). Referencing offers
by id removes the "I accept" ambiguity that breaks down with two live proposals on the table.

Three pieces:

- **The action dataclasses** (`Propose` / `Accept` / `Reject` / `Walk`), all frozen and
  JSON-round-trippable — the frozen team contract's move vocabulary. A `Deal` is a tuple of option indices
  (one per issue); deals are decoded from a model's `{"Site": "...", ...}` object by a scenario-supplied
  `deal_decoder`, so this module stays free of any specific game's issue set.
- **`OfferRegistry`** — monotonic ids and standing-offer tracking (accept/reject sets per offer, withdrawal),
  serializable for the episode record and reconstructable by replay (it is a pure function of the action
  sequence).
- **`parse_action`** — the single consolidated JSON-extraction-and-validation entry point. It returns a
  `ParseResult` distinguishing a **syntax** violation (no well-formed action could be read) from an
  **economic-legality** violation (well-formed but references a dead offer / an infeasible deal), so a scenario
  can retry once with specific feedback and log the two failure classes separately as data.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Deal` |  |  |
| `FACILITATOR` |  |  |
| `FACILITATOR_SEAT` |  |  |
| `LEGALITY` |  |  |
| `OfferId` |  |  |
| `SYNTAX` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Accept`](Accept.md) | Accept a specific standing offer by id (an `ACCEPT` vote on that exact deal). |
| [`Action`](Action.md) | Base class for the four formal moves. |
| [`Offer`](Offer.md) | One registered offer and its live vote state. |
| [`OfferRegistry`](OfferRegistry.md) | Monotonic offer ids + standing-offer tracking for the formal protocol. |
| [`ParseResult`](ParseResult.md) | The outcome of reading one formal action from a model's turn. |
| [`Pass`](Pass.md) | Take NO formal move this turn — the typed form of the talk-only pass a scenario already accepts as `{"action": "none"}`. |
| [`Propose`](Propose.md) | Register a complete deal. |
| [`Reject`](Reject.md) | Reject a specific standing offer by id. |
| [`Walk`](Walk.md) | Explicit no-deal exit — a decision, not a timeout. |

## Functions

| Name | Summary |
|---|---|
| [`action_from_json`](action_from_json.md) | Reconstruct a typed :class:`Action` from its stored dict — the inverse of `Action.to_json()`. |
| [`action_from_key`](action_from_key.md) | Rebuild the :class:`Action` a :func:`action_key` string names; `None`/unparseable → `None`. |
| [`action_key`](action_key.md) | The canonical STRING an action serializes to when it must be a JSON object key or a sort key — its `to_json()` dumped with sorted keys (`'{"action": "accept", "offer_id": "O1"}'`). |
| [`action_message`](action_message.md) | Render `action` as a message body: an optional free-text `preface`, then the fenced `json` action block — the exact envelope an LLM seat produces, so a transcript is symmetric across seat types (a `PolicyParticipant` emits through here). |
| [`parse_action`](parse_action.md) | Read ONE formal action from `text` (its last fenced/balanced JSON object), validated into a typed `Action` or a classified failure. |
