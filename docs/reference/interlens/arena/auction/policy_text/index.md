# `interlens.arena.auction.policy_text`

What the computable seats SAY -- the templated broadcast and DM behavior of design.md §3.4.

The mute-channel lesson is binding: a computable seat that cannot speak loses via the microphone, not the
decision rule. So the rational and oracle seats speak and DM from templates, with every slot filled by a
quantity the policy already computes.

Two constraints pull against each other and both are hard.

**No leakage.** A policy seat never emits a number or a claim a rival could not have computed itself from
public information plus this seat's own already-public actions. Every slot below is either public-only or a
label over the seat's own public bids. The one exception is `counter_lots`, which is derived from private
values and reveals a preference ORDERING rather than a number -- exactly as much disclosure as an LLM seat
makes when it names lots in a message, and permitted because the alternative (a policy seat that can accept or
refuse but never counter) is a strictly weaker communicator than the LLM seats it is compared against, which
reintroduces the mute-channel confound in a subtler form.

**Not trivially a bot.** A seat that emits one fixed sentence every stage is identified as non-LLM in one
stage, and every DM addressed to it after that is addressed to a known machine, which would confound Q5. So
each template has a small fixed set of surface variants chosen by a seeded index derived from the frozen
draws: `variant = hash(instance_id, seat, stage, template_id) mod n_variants` -- reproducible, arm-invariant,
and not a function of anything private.

**The oracle's templates are IDENTICAL to the rational seat's**, filled from the same public-only expressions.
An oracle that spoke from full information would leak every other seat's private draws through the channel and
invalidate every cell it appeared in; its information advantage shows up in its bids and in which proposals it
accepts, never in its text.

This module is prose that a policy EMITS, not a prompt a policy reads, which is why it lives beside the policy
classes rather than in `scenarios/auction_prompts.py`. It is frozen and SHA-pinned on the same schedule as
the prompts, since an LLM seat's behavior is a function of what the policy seats say to it.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `TRANSFER_CLAUSE` |  |  |
| `VARIANTS` | `dict[str, tuple[str, ...]]` |  |

## Functions

| Name | Summary |
|---|---|
| [`dm_initiate`](dm_initiate.md) | The proposal this seat opens with, addressed to the rival whose PUBLIC profile most contests its best lot -- a public-prior computation, so the address itself leaks nothing about which lots it privately values. |
| [`dm_reply`](dm_reply.md) | The reply to a DM'd division or price proposal, driven by the policy's own :class:`~.bidders.Decision`. |
| [`margin_word`](margin_word.md) | `"clearly"` when the gap exceeds 10% of the best-response value, `"marginally"` otherwise -- a qualitative label over two numbers that are never themselves emitted. |
| [`public_position`](public_position.md) | The broadcast: presence and public-profile fit at stage start, holdings mid-stage. |
| [`render`](render.md) | One templated line, at this episode's seeded surface variant. |
| [`variant_index`](variant_index.md) | The seeded surface-variant index, `hash(instance_id, seat, stage, template_id) mod n_variants`. |
