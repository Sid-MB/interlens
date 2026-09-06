# `auction_policy`

Module `interlens.arena.scenarios.auction_policy`

Computable seats inside the ordinary engine loop.

A policy seat is a :class:`~interlens.arena.participant.Participant` like any other: it receives a view,
returns a :class:`~interlens.arena.message.Message`, and produces a real `TurnRecord` that the transcript
export and the analysis read on exactly the same footing as an LLM seat's. That matters more here than
convenience — the whole point of the five-arm design is that the arms differ in the DECISION RULE and nothing
else, so a computable seat that bypassed the turn loop would differ in its instrumentation too.

**Policy seats read a structured state block, not prose.** The scenario renders a fenced `auction_state`
JSON object into a policy seat's view in place of the natural-language turn prompt (the same precedent as
`ScorableNegotiation`'s `negotiation_state` block). The block carries this seat's own private draws and
the public round state, and NOTHING about any other seat's draws — an oracle seat's extra information rides
in a separate, explicitly-named field so that reading it is a deliberate act the policy's own
`_rival_values` gate controls.

**And they speak.** The mute-channel lesson is binding, so the participant fills the envelope's `message`
and `dm` fields from :mod:`~interlens.arena.auction.policy_text`, driven by the policy's own decision
functions. The oracle's templates are identical to the rational seat's.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `FREE_ARM_INFORMATION` | `dict[str, str]` |  |
| `STATE_FENCE` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`AuctionPolicyParticipant`](AuctionPolicyParticipant.md) | One computable auction seat: an information-conditional best response, plus its templated channel behavior. |

## Functions

| Name | Summary |
|---|---|
| [`read_state_block`](read_state_block.md) | The latest `auction_state` block in a view. |
| [`replay_integrity`](replay_integrity.md) | Re-derive every computable turn of `episode` from its own recorded state block and check it matches what the seat actually played. |
| [`state_block`](state_block.md) | The fenced, machine-readable turn state handed to a policy seat. |
