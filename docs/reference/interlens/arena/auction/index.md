# `auction`

Package `interlens.arena.auction`

Repeated multi-bidder auctions: the frozen spec, the persona-conditioned prior, exact allocation and
payment rules, equilibrium benchmarks, computable bidders and oracles, and the collusion metrics.

The sibling of :mod:`interlens.arena.negotiation`. Each module's docstring carries the primary citations for
what it implements; :mod:`.references` maps every citation key to its full reference with the exact page
range the module relies on.

Layout:

- :mod:`.spec` — `AuctionSpec` / `BidderSpec` / `StageDraw` / `Mechanism`, and `generate_spec`.
- :mod:`.priors` — the persona table, the generative model, fact-rendering data, and `RivalPosterior`.
- :mod:`.allocation` — bundle values, the exact efficient allocation, VCG / clinching / uniform-price rules.
- :mod:`.benchmarks` — the exact per-stage equilibrium benchmarks every suppression metric divides against.
- :mod:`.actions` — the auction move vocabulary, `BidLedger`, `DMRouter`, and the action parser.
- :mod:`.bidders` — `AuctionState`, the policy zoo, and their oracle variants.
- :mod:`.metrics` — stage-level and repeated-play metrics, as pure functions over records.

## Modules

- [`actions`](actions/index.md) — The auction move vocabulary, the bid ledger, and DM routing (design.md §12 item 2).
- [`allocation`](allocation/index.md) — Bundle values, the exact efficient allocation, and the payment rules.
- [`benchmarks`](benchmarks/index.md) — The exact per-stage equilibrium benchmarks every suppression metric divides against (design.md §4.3, §5).
- [`bidders`](bidders/index.md) — The computable bidder zoo: policies (`state -> action`), their DM decision rules, and their oracles.
- [`metrics`](metrics/index.md) — Stage-level and repeated-play metrics (design.md §5), as pure functions over records.
- [`policy_text`](policy_text/index.md) — What the computable seats SAY -- the templated broadcast and DM behavior of design.md §3.4.
- [`priors`](priors/index.md) — The persona-conditioned prior: the generative model, the persona table, fact rendering data, and the posterior a rational seat actually computes.
- [`references`](references/index.md) — Citation-key registry for the auction mechanism, benchmark, and collusion-metric modules.
- [`spec`](spec/index.md) — The frozen auction specification: item slots, bidders, per-stage draws, and the mechanism config.
