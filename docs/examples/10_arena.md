# 10 · Arena: scoreable multi-agent evaluations

`interlens.arena` turns the conversation harness into an **evaluation harness**: a `Scenario` defines a game — solver-verified instance generation, per-seat private framing, a turn protocol with structured JSON actions, early termination, exact scoring — and the engine plays it through any `Participant`, persisting every episode to one JSON schema. Five scenario families ship: a multi-issue **negotiation** with secret score sheets, a wrong-shard **info relay** (an epistemic team task with a confidently-wrong agent), a repeated **security dilemma** (build/deescalate/attack with an absorbing war spiral and noisy intelligence), a **coding collaboration** with private mechanically-checkable constraints (sandboxed pytest scoring), and a **distributed long-context** family (one long-context benchmark task partitioned across 4 seats). All come from the collaboration-arena research program, and stored episodes from those experiments re-score exactly under this package.

## Run an episode

```python
import asyncio
from interlens import APIParticipant, UsageMeter
from interlens.arena import EpisodePool, EpisodeStore
from interlens.arena.scenarios import Negotiation

scenario = Negotiation()
instance = scenario.generate_instance(level=0, seed=1)   # exact ceiling, floor + hidden optimum
meter = UsageMeter(budget=25.0)                          # run-level $ ledger with a hard cap
player = APIParticipant(name="player", model_id="claude-sonnet-5",
                        meter=meter, turn_token_floor=2048)

pool = EpisodePool(EpisodeStore("episodes/"), meter=meter)
episode = asyncio.run(pool.run_episode(scenario, instance, arm="team", participant=player))
print(episode.outcome)        # {"primary": ..., "success": ..., "finalized_by": ..., ...}
print(episode.usage())        # tokens in/out (total + per seat), dollar cost
print(meter.summary())        # run-level spend, per model
```

Every seat is played by `player` (one model per episode — the design the arena experiments measured). The `EpisodeStore` writes the full record atomically after every turn wave; `store.summary()` aggregates episodes into a printable usage/success table.

## Arms, budgets, and matched compute

- `arm="team"` plays the full multi-seat protocol; `arm="solo"` gives ONE seat all private information (the "one mind with all the facts" baseline). Scenario variants like `team-greedy` / `team-adversarial` change one seat's private stance.
- Budgets are **stop conditions**, not ad-hoc counters: pass `budget=TokenBudget(per_conversation=6000)` (or a `CostBudget`, or a list) to `run_episode`. The engine counts each committed turn's recorded usage, shrinks per-turn caps (`turn_cap`) so the budget lands exactly, and — when the budget fires — sets `state["budget_exhausted"]`, which both scenarios answer with a forced finalization. That is the **matched-compute** recipe: give a solo baseline the team arm's median token spend, then force it to answer.
- Run-level spend is **reservation-gated**: jobs carrying `estimated_cost=` claim it against the meter *before* launching, so N concurrent episodes can never collectively overrun the cap (`run_pool` also stops launching once the meter is exhausted; in-flight episodes finish).

```python
jobs = [dict(scenario=scenario, instance=inst, arm="team", participant=player, estimated_cost=4.0)
        for inst in instances]
episodes = asyncio.run(pool.run_pool(jobs))
```

For **local models**, `BatchedEpisodePool` co-steps many episodes as one batched `generate_batch` per tick (with adaptive batch splitting on GPU OOM) — the multi-GPU rollout path.

## Situational sweeps

Both scenarios take a `cfg` dict (`make_state(..., cfg=...)`, or `cfg=` on `run_episode`) that varies the *situation* around the fixed game — rounds, stakes framing, personas, party count (negotiation, via `generate_instance_n`), hardness/framing (relay). The episode record carries the resolved cell config, so sweeps join cleanly.

## Two hard-won gotchas, now guarded

1. **Thinking × turn caps.** Models with adaptive/always-on reasoning spend hidden thinking tokens *out of* `max_tokens`. A small per-turn cap (500) silently produced **58% empty turns** in a real run — thinking consumed the whole budget, and the "negotiation" proceeded among mutes. Two controls on `APIParticipant`: `thinking="disabled"` (or an explicit int budget — Anthropic models) is the reliable fix, and `turn_token_floor=2048` raises any externally-imposed cap back to a generable size for models whose thinking can't be disabled. On very long contexts adaptive thinking can outgrow ANY fixed floor — a live 3-round negotiation with claude-sonnet-5 produced empty final-proposal turns even at a 4096 cap until thinking was disabled.
2. **Seat-selective refusals.** Hosted models occasionally refuse *from one seat's framing* and not others', silently biasing team results. Refusals are classified per turn (`metadata["refusal"]`, from the provider's native stop reason) and counted per model on the `UsageMeter` — check `meter.summary()` before believing a team-vs-solo delta.

## Preflight gates for local rollouts

```python
from interlens.arena import check_template_fidelity, check_reasoning_leak, scenario_smoke_views

views = scenario_smoke_views(scenario)
assert check_template_fidelity(tokenizer, views, enable_thinking=True)["ok"]   # token-id equality
# ... play one smoke episode, then:
assert check_reasoning_leak(episode)["ok"]   # no <think> content leaked into other seats' views
```

## The second scenario wave

### Security dilemma (`SecurityDilemma`, no solo arm)

Two seats play 12 rounds of message-then-simultaneous-action (`build` / `deescalate` / `attack`). Once BOTH attack in the same round, war spirals: every remaining round is forced mutual attack. Intelligence is noisy — with a level-dependent probability, a seat's *report* of the opponent's action is flipped; true actions always drive payoffs, and each seat sees only its own report and payoffs, so misreports are seeded, private, and replayable. The difficulty ladder raises the first-strike bonus and the noise. `primary` = joint payoff / 96 (mutual deescalation for 12 rounds); `success` = no spiral.

### Coding collaboration (`CodingCollab`)

Three seats jointly write ONE Python module against a public spec + pytest suite; each seat holds private style constraints (AST-checkable: no loops, full type hints, line caps, ...) it must get honored WITHOUT revealing verbatim. The latest complete ```` ```python ```` fence anywhere is the working draft; per-turn `{"constraints_ok": true|false}` declarations drive early consensus. Scoring is exact and sandboxed: `primary` = (tests passing) × (constraints held), with the suite run in an isolated subprocess (`sys.executable -I`, fresh tmpdir, 30 s timeout). The generator verifies every dealt constraint set against a bundled reference solution, so `primary == 1.0` is always achievable.

### Distributed long-context (`DistributedLongContext` + task adapters)

One long-context task is partitioned into 4 contiguous shards (asserted: their concatenation reproduces the original context exactly); each seat privately holds one shard, and the finalizer (seat 0, last each round) submits the answer. Three arms: `team` (round-robin broadcast), `team-msg` (directed messaging — each non-finalizer turn is only a fenced `{"messages": [...]}` routing object; a seat sees only mail addressed to it — the routing is part of the state machine, so episodes replay), and `solo` (the full concatenated context in one seat).

Task adapters (`interlens.arena.scenarios.dlc`) port four benchmarks: **S-NIAH** (RULER-style needle in a haystack, exact match), **OOLONG-Pairs** (pairwise aggregation, F1 over the emitted pair set), **LongBench-v2 CodeQA** (repo-understanding multiple choice), and **BrowseComp-Plus** (multi-hop QA; two-phase — the scenario records the answer un-judged, and the official grader template ships for a post-hoc LLM-judge pass). Benchmark data does **not** ship in the repo: `interlens.arena.scenarios.dlc.build` fetches from each benchmark's own source at a pinned revision (`pip install interlens[benchmarks]`) and writes a `load_instances`-compatible bank; instances embed megabytes of context, so they are built offline, once.

**Outcome classes.** Long-context episodes fail in ways a bare score conflates, so two classes are first-class outcome fields, applied by the engine and recomputed identically in replay (`Scenario.classify_outcome`):

- `truncated_at_budget` — some committed turn stopped at its `max_tokens` cap. The episode ran out of room; exclude it from success/failure analysis rather than scoring the accident.
- `capitulated` (OOLONG-Pairs) — NOT truncated, but the answer enumerated <50% of the gold pairs: the model *declined* the enumeration. The classification carries evidence — how many relevant user IDs the team had actually surfaced in discussion vs how many pairs it emitted.
- otherwise `answered` / `no_answer`.

## Adaptive difficulty ratchet

A ceiling-saturated cell measures nothing. `DifficultyRatchet` drives any scenario with a difficulty ladder to its *found level* — the first level whose probe mean drops below 75% of ceiling — then measures there and at the neighbor level, then runs paired solo baselines on the SAME instances under a `TokenBudget` equal to the median team spend (matched compute):

```python
from interlens.arena import DifficultyRatchet, EpisodePool, EpisodeStore

ratchet = DifficultyRatchet(scenario, player, EpisodePool(EpisodeStore("episodes/"), meter=meter),
                            instances_dir="instances/", state_path="ratchet.json",
                            speculative=True)   # probe the first 3 levels concurrently
state = asyncio.run(ratchet.run())              # {"found": ..., "probe_means": ..., ...}
```

State persists after every batch: a restarted ratchet resumes where it stopped and never duplicates a completed episode (instances are deterministic per level and skipped by id, so team/solo pairings stay intact). `speculative=True` probes the first wave of levels concurrently — faster wall-clock at the cost of probing levels a sequential climb might have skipped; the found decision is the same pure function (`found_level`) either way.

## Replay and re-scoring

Scenarios are pure state machines, so a stored episode replays exactly:

```python
from interlens.arena import replay_episode, rescore
outcome = replay_episode(scenario, instance, stored_episode_json)   # recompute with the current scorer
result = rescore(scenario, instance, stored_episode_json)           # compare vs the recorded outcome
```

## Communication styles

**Async messaging is the package default** (`Scenario.default_communication = "messaging"`, used by the Inspect tasks when no mode is given): no shared transcript; autonomous agents exchange point-to-point mail via `send_message`/`read_message` (fenced-JSON actions for any participant type, or native tools via `policy.tools_for(name)`), with ping-driven scheduling (priority + a fairness tick). Sends/reads/deliveries are first-class transcript events. See `examples/arena_relay_messaging.py` for the relay task run in this mode.

Two other styles remain available as explicit configs and compose with the same scoring and persistence (see `interlens.communication`):

- **Round-robin protocol** (`communication="round_robin"`, or `EpisodePool.run_episode` directly): each scenario's published turn protocol over a shared transcript. **This is the comparability option**: the shipped v0 transcript dataset was produced under this protocol (recorded per episode in `gen_config`), so use it when comparing new runs against those cells — do not assume messaging-mode and protocol-mode scores are equivalent. The security dilemma pins this mode (`default_communication = "round_robin"`): a simultaneous-move payoff game has no sound free-messaging reduction.
- **Direct piping** (`DirectPipingPolicy`): one participant's output is the next one's input along a fixed chain — the natural two-agent dialogue framing, generalized. See `examples/arena_direct_piping.py`.

## Inspect integration (optional)

With the extra installed (`pip install interlens[inspect]`), both scenarios run under [Inspect](https://inspect.aisi.org.uk/):

```bash
inspect eval interlens.arena.inspect/info_relay --model anthropic/claude-sonnet-5 -T level=2   # messaging (default)
inspect eval interlens.arena.inspect/negotiation --model openai/gpt-5 -T n_parties=8 -T arm=solo
inspect eval interlens.arena.inspect/info_relay -T communication=round_robin --model anthropic/claude-sonnet-5   # published protocol, comparable with the v0 dataset
inspect eval interlens.arena.inspect/security_dilemma --model anthropic/claude-sonnet-5 -T level=2   # always round-robin
inspect eval interlens.arena.inspect/coding_collab --model openai/gpt-5 -T level=3
inspect eval interlens.arena.inspect/distributed_longcontext -T instances=banks/dlc_sniah_L0.json --model anthropic/claude-sonnet-5
```

Messaging-mode (default) notes for the new families: `coding_collab` scores the latest complete ```` ```python ```` fence in the agents' mail as the submission (the same working-draft rule as the protocol); `distributed_longcontext` maps messaging to the scenario's NATIVE directed-messaging arm (`team-msg`), so those episodes stay replayable; `security_dilemma` rejects messaging mode — a simultaneous-move payoff game has no sound free-messaging reduction — and pins `round_robin` via its `default_communication`.

Instance banks become samples (instance JSON + per-seat framings in sample metadata), the arena engine runs inside a fully-async solver (Inspect's `--max-samples` runs many episodes concurrently), the exact scenario scorers register as Inspect scorers (`success` accuracy + mean `primary`), and each seat turn is mirrored into the sample's message list so `inspect view` renders the multi-agent flow with seat attribution, structured actions as transcript events, and the outcome in the score view. Inspect's native `token_limit` carries episode budgets; the adapter adds per-sample dollar cost (`metadata["cost_usd"]`) computed from the same pricing as `UsageMeter`. Without the extra, `import interlens.arena.inspect` fails with a clear install hint — the base package never requires inspect-ai.

Next: back to the [index](README.md).
