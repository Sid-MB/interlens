# `interlens.arena.scenarios.scorable`

ScorableNegotiation: the repaired multi-party, multi-issue scorable game — the *protocol* around a
:class:`~interlens.arena.negotiation.sheets.GameSpec` (carried in `Instance.payload`), built on the shared
typed-action (:mod:`interlens.arena.actions`) and oracle (:mod:`interlens.arena.oracles`) layers. "Repaired"
names the specific benchmark flaws it fixes, each called out at the code that fixes it: votes-not-arithmetic
closure, structural channel separation, a restated deadline, and measured-not-blocked economic illegality.

Each turn is one fenced JSON object with three channels — private `scratchpad`, public `message`, one
binding `action` (`Propose` a complete package -> a fresh offer id, `Accept` / `Reject` a live id,
`Walk`, or a talk-only pass, parsed by :func:`~interlens.arena.actions.parse_action`); the harness publishes
only the message + the validated action, so privacy is structural, not tag-dependent. A deal closes ONLY on real
ACCEPT votes on the SAME standing offer (never threshold arithmetic). Rotating proposer, the turn deadline
restated each turn, one canonical prompt scaffold with variants behind flags
(:class:`~interlens.arena.scenarios.scorable_prompts.PromptScaffold`). A syntax/legality error gets one
retry-with-specific-feedback then a pass; an economic (below-own-threshold) move is MEASURED, never blocked.

Arms `moves_chat` / `moves_only` / `team` / `solo` cross the game's FULL/PRIVATE info; ultimatum-style
single-shot / fixed-proposer / majority variants ride on cfg knobs, as does `seeded_offer` — one standing
package tabled by a neutral non-voting facilitator before round 1, which deletes the search problem and leaves
the table nothing to do but judge a known deal (:meth:`ScorableNegotiation._seed_offer`). Each seat's surplus is normalized by its
own maximum available surplus before aggregation, so `primary` is invariant to positive affine rescaling of
any party's utility. Raw surplus welfare remains in explicitly named audit fields. Per-turn normative regret
comes from the pluggable `oracles=` (each turn ->
:class:`OracleRecord` via :meth:`annotate_turn`). A pure state machine (state is a pure function of the action
sequence), so stored episodes replay and rescore exactly (`arena/replay.py`).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ARMS` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`ScorableNegotiation`](ScorableNegotiation.md) | The repaired scorable-negotiation protocol over a :class:`GameSpec` (see the module docstring). |
