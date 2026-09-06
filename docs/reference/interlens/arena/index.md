# `arena`

Package `interlens.arena`

Scoreable multi-agent evaluations on interlens: scenarios, episode drivers, and exact scoring.

The arena turns interlens from a conversation harness into an evaluation harness: a `Scenario` defines a
game (solver-verified instance generation, per-seat private framing, a turn protocol with structured JSON
actions, early termination, exact scoring), and the engine plays it through any `Participant` — hosted-API
or local — as concurrently as the backend allows, persisting every episode to one JSON schema.

Quickstart:

```python
from interlens import APIParticipant, UsageMeter
from interlens.arena import EpisodePool, EpisodeStore
from interlens.arena.scenarios import Negotiation
import asyncio

scenario = Negotiation()
instance = scenario.generate_instance(level=0, seed=1)      # solver-verified: exact ceiling + optimum
meter = UsageMeter(budget=20.0)
player = APIParticipant(name="player", model_id="claude-sonnet-5", meter=meter, turn_token_floor=2048)
pool = EpisodePool(EpisodeStore("episodes/"), meter=meter)
episode = asyncio.run(pool.run_episode(scenario, instance, "team", player))
print(episode.outcome, episode.usage(), meter.summary())
```

Optional Inspect integration (`pip install interlens[inspect]`): `interlens.arena.inspect` exposes the
bundled scenarios as `inspect eval`-runnable tasks.

## Modules

- [`actions`](actions/index.md) — Typed formal-action layer for structured negotiation turns.
- [`auction`](auction/index.md) — Repeated multi-bidder auctions: the frozen spec, the persona-conditioned prior, exact allocation and payment rules, equilibrium benchmarks, computable bidders and oracles, and the collusion metrics.
- [`engine`](engine/index.md) — Episode drivers: play `Scenario` instances through `Participant`s.
- [`export`](export/index.md) — Human-readable transcripts from stored episodes: an `EpisodeStore` tree -> one markdown + one self-contained HTML page per episode, plus a per-run index.
- [`gates`](gates/index.md) — Template-fidelity gates: preflight checks before spending GPU-hours on local-model rollouts.
- [`inspect`](inspect/index.md) — Optional Inspect (inspect-ai) integration: run arena scenarios under `inspect eval`.
- [`live`](live/index.md) — Live play: watch an arena episode as it happens, reconfigure its seats, and play one yourself.
- [`negotiation`](negotiation/index.md) — Multi-issue, multi-party scorable negotiation: deal spaces, private score sheets, exact solution concepts, computable rational-agent oracles, and an executable strategy zoo.
- [`oracles`](oracles/index.md) — The oracle layer: per-turn "what would a rational agent have done here?" annotations.
- [`ratchet`](ratchet/index.md) — Adaptive difficulty ratchet: find the level where a model stops clearing the bar, then measure there.
- [`refusal`](refusal/index.md) — Recovering a turn the API refused, without changing what the turn says.
- [`replay`](replay/index.md) — Deterministic replay of stored episodes through a scenario's state machine.
- [`rollouts`](rollouts/index.md) — Directory-backed **rollout sets**: run more episodes into the same place, safely, and resume.
- [`scenario`](scenario/index.md) — The `Scenario` interface: a pure game-logic state machine, participant-agnostic.
- [`scenarios`](scenarios/index.md) — Bundled scenarios, four families:
- [`schema`](schema/index.md) — The arena's record schema: one JSON shape for every episode.
- [`table`](table/index.md) — Heterogeneous **tables**: present a whole many-seat lineup to the arena engine as one participant.
- [`views`](views/index.md) — Per-seat view construction + structured-action parsing for arena scenarios.
- [`viz`](viz/index.md) — Interactive episode visualization: any arena run directory in, self-contained interactive HTML out.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`Accept`](actions/Accept.md) | `interlens.arena.actions` | Accept a specific standing offer by id (an `ACCEPT` vote on that exact deal). |
| [`Action`](actions/Action.md) | `interlens.arena.actions` | Base class for the four formal moves. |
| [`BatchedEpisodePool`](engine/BatchedEpisodePool.md) | `interlens.arena.engine` | Synchronous co-stepping for local model participants: each tick gathers every live episode's pending requests and runs them as one batched `generate_batch` per participant — the local-GPU throughput path. |
| [`Deal`](actions/index.md#attributes) | `interlens.arena.actions` |  |
| [`DifficultyRatchet`](ratchet/DifficultyRatchet.md) | `interlens.arena.ratchet` | Probe -> measure -> paired-solo driver over one scenario/participant pair (see the module docstring). |
| [`EMPTY_TURN_PLACEHOLDER`](engine/index.md#attributes) | `interlens.arena.engine` |  |
| [`Episode`](schema/Episode.md) | `interlens.arena.schema` | One complete play-through: turns, forked provisional checkpoints, outcome, and usage accounting. |
| [`EpisodePool`](engine/EpisodePool.md) | `interlens.arena.engine` | Concurrent episodes as independent asyncio tasks — one participant call at a time per episode, many episodes in flight. |
| [`EpisodeRun`](engine/EpisodeRun.md) | `interlens.arena.engine` | Per-episode bookkeeping shared by both drivers: state stepping, turn recording, budget checks, retries, and finalization. |
| [`EpisodeStore`](schema/EpisodeStore.md) | `interlens.arena.schema` | Per-episode JSON persistence, written atomically on every update so a crash loses at most one turn. |
| [`GenerationFailureBudgetExceeded`](engine/GenerationFailureBudgetExceeded.md) | `interlens.arena.engine` | Raised by :class:`BatchedEpisodePool` when it has had to fabricate more turns than its budget allows. |
| [`Instance`](schema/Instance.md) | `interlens.arena.schema` | One generated problem instance, solver-verified at generation time. |
| [`LEGALITY`](actions/index.md#attributes) | `interlens.arena.actions` |  |
| [`Offer`](actions/Offer.md) | `interlens.arena.actions` | One registered offer and its live vote state. |
| [`OfferId`](actions/index.md#attributes) | `interlens.arena.actions` |  |
| [`OfferRegistry`](actions/OfferRegistry.md) | `interlens.arena.actions` | Monotonic offer ids + standing-offer tracking for the formal protocol. |
| [`Oracle`](oracles/Oracle.md) | `interlens.arena.oracles` | A rational reference policy that scores a seat's options at a decision point. |
| [`OracleRecord`](oracles/OracleRecord.md) | `interlens.arena.oracles` | One per-turn oracle annotation on an episode (the typed replacement for the loose checkpoint dict). |
| [`OracleVerdict`](oracles/OracleVerdict.md) | `interlens.arena.oracles` | One oracle's read of a decision point. |
| [`PERSONAS`](schema/index.md#attributes) | `interlens.arena.schema` |  |
| [`ParseResult`](actions/ParseResult.md) | `interlens.arena.actions` | The outcome of reading one formal action from a model's turn. |
| [`Pass`](actions/Pass.md) | `interlens.arena.actions` | Take NO formal move this turn — the typed form of the talk-only pass a scenario already accepts as `{"action": "none"}`. |
| [`Propose`](actions/Propose.md) | `interlens.arena.actions` | Register a complete deal. |
| [`RefusalLadder`](refusal/RefusalLadder.md) | `interlens.arena.refusal` | A fixed, seeded sequence of content-preserving re-renders, tried in order after a refusal. |
| [`Reject`](actions/Reject.md) | `interlens.arena.actions` | Reject a specific standing offer by id. |
| [`ReplayError`](replay/ReplayError.md) | `interlens.arena.replay` | A stored turn could not be matched to the state machine's pending request. |
| [`RolloutConfigMismatch`](rollouts/RolloutConfigMismatch.md) | `interlens.arena.rollouts` | An append's config fingerprint disagrees with the set's manifest — refused rather than silently mixed. |
| [`RolloutSet`](rollouts/RolloutSet.md) | `interlens.arena.rollouts` | A directory of episodes plus the manifest that says what produced them. |
| [`SYNTAX`](actions/index.md#attributes) | `interlens.arena.actions` |  |
| [`Scenario`](scenario/Scenario.md) | `interlens.arena.scenario` |  |
| [`SeatRequest`](schema/SeatRequest.md) | `interlens.arena.schema` | One pending generation: a seat that must speak now, with the exact view its model is conditioned on. |
| [`TURN_SIGNATURES`](engine/index.md#attributes) | `interlens.arena.engine` |  |
| [`TurnRecord`](schema/TurnRecord.md) | `interlens.arena.schema` |  |
| [`Walk`](actions/Walk.md) | `interlens.arena.actions` | Explicit no-deal exit — a decision, not a timeout. |
| [`action_from_json`](actions/action_from_json.md) | `interlens.arena.actions` | Reconstruct a typed :class:`Action` from its stored dict — the inverse of `Action.to_json()`. |
| [`annotate`](oracles/annotate.md) | `interlens.arena.oracles` | Run every oracle over one decision point and return one inline :class:`OracleRecord` each — the ready helper a scenario calls from `annotate_turn` so its oracle wiring is a single line. |
| [`build_view`](views/build_view.md) | `interlens.arena.views` | Render `events` (`[{seat\|'MODERATOR', content, only?}]`, public unless `only` names seats) into an alternating per-speaker view for `seat`, ending with `phase_prompt` as the final user turn. |
| [`check_reasoning_leak`](gates/check_reasoning_leak.md) | `interlens.arena.gates` | Scan a played episode for reasoning leakage: any turn whose raw completion contains a `<think>` block whose content then appears verbatim in a LATER turn's visible content (meaning another seat saw it). |
| [`check_template_fidelity`](gates/check_template_fidelity.md) | `interlens.arena.gates` | Assert token-id equality between `tokenizer(apply_chat_template(tokenize=False))` and `apply_chat_template(tokenize=True)` for every view. |
| [`config_fingerprint`](rollouts/config_fingerprint.md) | `interlens.arena.rollouts` | Stable SHA256 over `config`, canonicalized (sorted keys, compact separators, non-JSON values repr'd). |
| [`extract_json`](views/extract_json.md) | `interlens.arena.views` | The last fenced JSON object in `text`, else the last balanced top-level `{...}` that parses. |
| [`found_level`](ratchet/found_level.md) | `interlens.arena.ratchet` | The found level implied by a set of probe means: the first (ascending) probed level whose mean fails the bar, else the highest level probed (the model never dropped below the bar). |
| [`gen_failures`](engine/gen_failures.md) | `interlens.arena.engine` | Every turn of an episode whose text the ENGINE fabricated because generation failed. |
| [`is_refusal`](refusal/is_refusal.md) | `interlens.arena.refusal` | Did this completion come back declined rather than generated? |
| [`load_instances`](schema/load_instances.md) | `interlens.arena.schema` | Load an instance pool saved by `save_instances` (or by the arena experiments — the pre-rename `env` key is migrated on read). |
| [`parse_action`](actions/parse_action.md) | `interlens.arena.actions` | Read ONE formal action from `text` (its last fenced/balanced JSON object), validated into a typed `Action` or a classified failure. |
| [`replay_episode`](replay/replay_episode.md) | `interlens.arena.replay` | Feed a stored episode's turns back through `scenario` and return the recomputed outcome dict. |
| [`rescore`](replay/rescore.md) | `interlens.arena.replay` | Replay `episode` and compare the recomputed outcome to the recorded one on `fields`. |
| [`rollout`](rollouts/rollout.md) | `interlens.arena.rollouts` | Run `instances x seeds x arms` into the rollout set at `out` (creating or resuming it) and return it. |
| [`save_instances`](schema/save_instances.md) | `interlens.arena.schema` | Persist an instance pool as one JSON file (`{scenario}_L{level}.json` unless `name` overrides). |
| [`scenario_smoke_views`](gates/scenario_smoke_views.md) | `interlens.arena.gates` | Real rendered views for gating: a fresh team state's first requests, plus the views after one scripted turn (so later views carry assistant/user mixes, which is where templates diverge). |
| [`strip_think`](../parsing/strip_think.md) | `interlens.parsing` | Remove `<think>...</think>` blocks ANYWHERE in `text`; return `(visible, think)`. |
| [`truncation_budget`](engine/truncation_budget.md) | `interlens.arena.engine` | The output budget one stored turn's `n_tokens_out` may honestly be compared against; `0` for "none, so read truncation from `stop_reason` alone". |
| [`turn_signatures`](engine/turn_signatures.md) | `interlens.arena.engine` | Every failure signature carried by one stored turn (a `TurnRecord.to_json()` dict); `set()` if healthy. |
