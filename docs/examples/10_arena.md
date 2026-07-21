# 10 · Arena: scoreable multi-agent evaluations

`interlens.arena` turns the conversation harness into an **evaluation harness**: a `Scenario` defines a game — solver-verified instance generation, per-seat private framing, a turn protocol with structured JSON actions, early termination, exact scoring — and the engine plays it through any `Participant`, persisting every episode to one JSON schema. Two scenarios ship: a multi-issue **negotiation** with secret score sheets, and a wrong-shard **info relay** (an epistemic team task with a confidently-wrong agent). Both come from the collaboration-arena research program, and stored episodes from those experiments re-score exactly under this package.

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

## Replay and re-scoring

Scenarios are pure state machines, so a stored episode replays exactly:

```python
from interlens.arena import replay_episode, rescore
outcome = replay_episode(scenario, instance, stored_episode_json)   # recompute with the current scorer
result = rescore(scenario, instance, stored_episode_json)           # compare vs the recorded outcome
```

## Communication styles

The protocol mode (round-robin over a shared transcript) is each scenario's published default. Two other styles are core interlens machinery (see `interlens.communication`) and compose with the same scoring and persistence:

- **Direct piping** (`DirectPipingPolicy`): one participant's output is the next one's input along a fixed chain — the natural two-agent dialogue framing, generalized. See `examples/arena_direct_piping.py`.
- **Async messaging** (`MessagingPolicy`): no shared transcript; autonomous agents exchange point-to-point mail via `send_message`/`read_message` (fenced-JSON actions for any participant type, or native tools via `policy.tools_for(name)`), with ping-driven scheduling (priority + a fairness tick). Sends/reads/deliveries are first-class transcript events. See `examples/arena_relay_messaging.py` for the relay task run in this mode.

## Inspect integration (optional)

With the extra installed (`pip install interlens[inspect]`), both scenarios run under [Inspect](https://inspect.aisi.org.uk/):

```bash
inspect eval interlens.arena.inspect/info_relay --model anthropic/claude-sonnet-5 -T level=2
inspect eval interlens.arena.inspect/negotiation --model openai/gpt-5 -T n_parties=8 -T arm=solo
inspect eval interlens.arena.inspect/info_relay -T communication=messaging --model anthropic/claude-sonnet-5
```

Instance banks become samples (instance JSON + per-seat framings in sample metadata), the arena engine runs inside a fully-async solver (Inspect's `--max-samples` runs many episodes concurrently), the exact scenario scorers register as Inspect scorers (`success` accuracy + mean `primary`), and each seat turn is mirrored into the sample's message list so `inspect view` renders the multi-agent flow with seat attribution, structured actions as transcript events, and the outcome in the score view. Inspect's native `token_limit` carries episode budgets; the adapter adds per-sample dollar cost (`metadata["cost_usd"]`) computed from the same pricing as `UsageMeter`. Without the extra, `import interlens.arena.inspect` fails with a clear install hint — the base package never requires inspect-ai.

Next: back to the [index](README.md).
