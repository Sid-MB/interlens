# `scenarios`

Package `interlens.arena.scenarios`

Bundled scenarios, four families:

- `Negotiation` — multi-issue, multi-party deal-making with secret score sheets (exact enumeration).
- `InfoRelay` — wrong-shard epistemics: can a team relay a correct fact past a confident wrong holder.
- `SecurityDilemma` — repeated 2-party build/deescalate/attack with an absorbing war spiral and noisy
  intelligence (payoff-exact scoring; no solo arm).
- `CodingCollab` — 3 seats jointly write one Python module against a public pytest suite while each holds
  private, mechanically checkable style constraints (sandboxed exact scoring).
- `AuctionScenario` — five bidders over `T` auction stages under one mechanism config (sealed second-price,
  Dutch / English clock, simultaneous ascending), with the format as a config rather than a separate runner.
- `DistributedLongContext` — one long-context task partitioned across 4 seats (task adapters + offline
  instance builders in `interlens.arena.scenarios.dlc`; first-class `truncated_at_budget` /
  `capitulated` outcome classes).

Generator-backed scenarios ship solver-verified instances (every instance carries its exact ceiling, floor,
and hidden solution) and exact scorers. Further scenarios follow the same pattern: subclass
`interlens.arena.Scenario`. `SCENARIOS` maps every bundled scenario name to a zero-argument factory
(the distributed long-context entries bind their task adapter).

## Modules

- [`auction`](auction/index.md) — Repeated multi-bidder auctions as one :class:`~interlens.arena.scenario.Scenario`.
- [`auction_examples`](auction_examples/index.md) — The three worked turn views of the auction scaffold, generated from real frozen draws.
- [`auction_policy`](auction_policy/index.md) — Computable seats inside the ordinary engine loop.
- [`auction_prompts`](auction_prompts/index.md) — The frozen prompt scaffold for :class:`~interlens.arena.scenarios.auction.AuctionScenario`.
- [`coding`](coding/index.md) — Coding collaboration with private constraints: 3 seats jointly write ONE Python module.
- [`dlc`](dlc/index.md) — Task adapters for the distributed long-context scenario, ported from the RLM paper's benchmarks.
- [`longcontext`](longcontext/index.md) — Distributed long-context: one long-context task split across 4 communicating seats.
- [`negotiation`](negotiation/index.md) — Negotiation: a multi-issue, multi-party deal with secret score sheets (structured-JSON actions).
- [`priors`](priors/index.md) — Role-prior sign table for the negotiation scenario (role × issue) and sheet-vs-prior analysis helpers.
- [`relay`](relay/index.md) — Info relay: an epistemic team task with a confidently-wrong agent.
- [`scorable`](scorable/index.md) — ScorableNegotiation: the repaired multi-party, multi-issue scorable game — the *protocol* around a :class:`~interlens.arena.negotiation.sheets.GameSpec` (carried in `Instance.payload`), built on the shared typed-action (:mod:`interlens.arena.actions`) and oracle (:mod:`interlens.arena.oracles`) layers. "Repaired" names the specific benchmark flaws it fixes, each called out at the code that fixes it: votes-not-arithmetic closure, structural channel separation, a restated deadline, and measured-not-blocked economic illegality.
- [`scorable_prompts`](scorable_prompts/index.md) — The canonical prompt scaffold for the scorable-negotiation scenario.
- [`security`](security/index.md) — Security dilemma: a repeated 2-party build/deescalate/attack game with noisy intelligence.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`AuctionScenario`](auction/AuctionScenario.md) | `interlens.arena.scenarios.auction` | Five bidders, `T` stages, one mechanism config, one communication rung. |
| [`CodingCollab`](coding/CodingCollab.md) | `interlens.arena.scenarios.coding` |  |
| [`DistributedLongContext`](longcontext/DistributedLongContext.md) | `interlens.arena.scenarios.longcontext` |  |
| [`InfoRelay`](relay/InfoRelay.md) | `interlens.arena.scenarios.relay` |  |
| [`Negotiation`](negotiation/Negotiation.md) | `interlens.arena.scenarios.negotiation` |  |
| [`ScorableNegotiation`](scorable/ScorableNegotiation.md) | `interlens.arena.scenarios.scorable` | The repaired scorable-negotiation protocol over a :class:`GameSpec` (see the module docstring). |
| [`SecurityDilemma`](security/SecurityDilemma.md) | `interlens.arena.scenarios.security` |  |
| [`TaskAdapter`](longcontext/TaskAdapter.md) | `interlens.arena.scenarios.longcontext` | Per-task behavior plugged into `DistributedLongContext`. |
| [`dlc_scenario`](dlc/dlc_scenario.md) | `interlens.arena.scenarios.dlc` | A `DistributedLongContext` scenario for one task, e.g. `dlc_scenario("sniah")`. |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `SCENARIOS` |  |  |
