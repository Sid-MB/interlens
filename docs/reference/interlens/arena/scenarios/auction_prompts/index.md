# `interlens.arena.scenarios.auction_prompts`

The frozen prompt scaffold for :class:`~interlens.arena.scenarios.auction.AuctionScenario`.

This module **transcribes** `experiments/rational_agents/auction/docs/templates/` and originates no wording
of its own. Those files were written and reviewed as prose before any implementation existed, because
design.md §6's prompt-freeze rule makes wording a preregistered object: prompt optimization can *manufacture*
stable collusion [tian2026], a sharper hazard in a repeated design than a one-shot one. Any wording change
here is a protocol change that forces a re-run of every affected cell.

The scaffold holds only WORDING. Every number, name, and table row is passed in by the scenario, so one
scaffold renders any instance and a wording ablation is a variant scaffold rather than an edited scenario --
the same rule :mod:`~interlens.arena.scenarios.scorable_prompts` states for the negotiation side.

Composition, per `templates/README.md`:

- `SYSTEM` = :meth:`AuctionPromptScaffold.system_prompt` over setting, seat identity, objective, the public
  roster, the prior statement, the format rules, the four-channel envelope, and conduct.
- `TURN` = :meth:`AuctionPromptScaffold.turn_prompt` over the stage catalogue, the bounded carried-history
  digest, this seat's private block, one phase block, and the closing ask.

Three composition invariants, enforced here and checked by `tests/test_auction_prompts.py` rather than
trusted to the wording: no private field of any seat appears outside its owner's private block; every number
appears in exactly one block; stages-remaining is restated in every turn view.

One block here is **not** part of the freeze and is marked as such at its definition:
:meth:`AuctionPromptScaffold.ring_block`, transcribed from the non-frozen `templates/ring_block.md`. It is
the instructed-ring capability probe, it is rendered only for a seat in an `instructed` `RingSpec`, and it
appends as a strict SUFFIX so that every frozen block stays byte-identical whether it is present or not.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ARROW` |  |  |
| `BLURB_PHRASES` | `dict[str, dict[int, str]]` |  |
| `CAPITAL_POSITION_PHRASES` | `dict[str, str]` |  |
| `DEFAULT_AUCTION_SCAFFOLD` |  |  |
| `EMDASH` |  |  |
| `FALLBACK_WORDS` | `dict[str, str]` |  |
| `LOT_NAMES` | `tuple[str, ...]` |  |
| `MINUS` |  |  |
| `PERSONA_CARDS` | `dict[str, str]` |  |
| `REVIEWED_CONSTANTS` | `dict[str, float]` |  |

## Classes

| Name | Summary |
|---|---|
| [`AuctionPromptScaffold`](AuctionPromptScaffold.md) | One immutable prompt wording for the repeated-auction scenario. |

## Functions

| Name | Summary |
|---|---|
| [`lot_blurb`](lot_blurb.md) | The prose description of a lot, generated from its loading vector through :data:`BLURB_PHRASES`. |
| [`lot_id`](lot_id.md) | The addressable lot token, `L01`..`L24` -- what the action grammar's `"lot"` field carries and what every table keys on. |
| [`lot_name`](lot_name.md) | The persistent display name of slot `slot_id` (:data:`LOT_NAMES`). |
| [`signed`](signed.md) | A loading or attribute entry as the reviewed prose prints it: `+1`, `0`, or `{MINUS}1` with a Unicode minus. |
| [`signed_amount`](signed_amount.md) | A surplus as the digest prints it: `+41`, `0`, `{MINUS}12`. |
