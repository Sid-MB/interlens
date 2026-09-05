# `interlens.arena.rollouts`

Directory-backed **rollout sets**: run more episodes into the same place, safely, and resume.

The arena already has every piece of a rollout: a `Scenario` (the game), a `Participant` (who plays), an
`EpisodePool`/`BatchedEpisodePool` (drives them), and an `EpisodeStore` (persists them). What it did not
have is the bookkeeping *around* a set of episodes — the part every experiment re-derives: which
(instance, seed, arm) triples are already on disk, whether it is safe to add more to this directory, and what
the set looks like so far. This module is that layer and nothing else. It composes; it re-implements nothing.

Library vs experiment — the boundary this module commits to
-----------------------------------------------------------
**In the library** (here): the identity and safety of a *set of episodes on disk*. Open-or-create a directory,
a manifest describing what produced it (model, scenario, config fingerprint, seeds completed, invocations,
artifact links), a dedupe/resume key, an append that REFUSES to mix protocols, and two contamination gates
(fabricated turns, and the placeholder budget below). Also a deliberately minimal
:meth:`RolloutSet.summary` — counts, statuses, success rate, mean primary, spend.
All of it is scenario-agnostic: it reads only fields the arena's own :mod:`~interlens.arena.schema` defines.

**In the experiment**: everything protocol-specific. Which scaffold, framing, oracle stack, instance bank, seat
lineup and arms constitute a cell; how a model id resolves to a participant; and every rich metric (per-party
normalized surplus, among-deals baskets, instance-clustered intervals, paired tables). Those live with the
analyzers that own their definitions — `summary()` here is a health check, not a results table, and it stays
that way so the library never grows a dependency on one experiment's notion of a good deal.

Two gates, because each is blind to the other
---------------------------------------------
A rollout set can be 100% `status="done"`, 100% `parse_ok`, 0% empty content, `fabrication 0.000` — and
still be a quarter silent. Those are two different failures wearing the same
:data:`~interlens.arena.engine.EMPTY_TURN_PLACEHOLDER` string:

- the ENGINE fabricated the turn (generation failed outright) — the fabrication budget owns this one;
- the MODEL burned its entire per-turn budget inside an unterminated `<think>` block and emitted no visible
  action. The engine did its job, so `fabrication` correctly reads 0.000; the placeholder it substitutes is
  non-empty and parses into a well-formed no-op, so `parse_ok` reads 1.000 too. Measured at **24.4% of turns**
  on a thinking-on Qwen3-32B cell at a 2,048-token cap, against 0.0% with thinking off — and on that cell
  `parse_ok` was *anti*-correlated with quality (1.000 silent vs 0.958 healthy).

So :meth:`RolloutSet.summary` reports a **placeholder budget** beside the fabrication audit, split by cause,
and broken down BY ROUND — the failure is late-episode by construction (context grows with the transcript:
5.8% at round 1, ~35% by rounds 2-4), so a short smoke run or a peek at an episode's opening turns reads ~0%
and under-detects it. Exceeding the budget flags the set loudly and stamps `manifest["turn_health"]`; it
never raises, because the episodes are real evidence and the right response is to record the rate. Raising the
per-turn cap changes the protocol string, so the remediated cells do not pair with the old ones.

Why the append refusal is loud
------------------------------
A rollout set is evidence. Appending episodes played under a *different* protocol into a directory whose
manifest claims one protocol produces a silently mixed corpus that every downstream analysis will average over
without ever knowing. So :meth:`RolloutSet.append` compares a fingerprint of the caller's config against the
manifest's and raises :class:`RolloutConfigMismatch` on any difference. `allow_mismatch=True` is the explicit
escape hatch, and it is not a silencer: the mismatched episodes are STAMPED in their own `cell_cfg` and the
divergence is recorded in the manifest, so the contamination stays legible forever.

Worked example:

```python
from interlens.arena.rollouts import rollout
from interlens.arena.negotiation import games
from interlens.arena.negotiation.sheets import GameSpec
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.table import rational_table

instances = [games.build_preset_instance("scorable", level=0, seed=s,
                                         instance_name=ScorableNegotiation.name)[0]
             for s in range(3)]

def seat_lineup(instance, arm, seed):                      # fresh policy seats per episode
    game = GameSpec.from_json(instance.payload)
    return rational_table(game, ["boulware", "conceder", "bayes-rational"], deadline=game.rounds)

cfg = {"model": "policy:bayes-rational", "scaffold": "canonical", "info": "full"}
rs = rollout(scenario=ScorableNegotiation(), instances=instances, participant=seat_lineup,
             seeds=[0, 1], arms=["moves_chat"], out="runs/pilot", config=cfg)
print(rs.summary_text())
# RolloutSet runs/pilot
#   model=policy:bayes-rational scenario=scorable_negotiation cfg=8f2c1a09b4de
#   episodes: 6 (6 distinct keys) statuses={'done': 6}
#   arms: {'moves_chat': 6}
#   success: 4/6 = 0.667
#   mean primary: 0.7143 over 6 scored episodes
#   usage: 0 in / 0 out tokens, $0.00
#   fabricated turns: 0 (in 0 episodes)
#   placeholder turns: 0/94 = 0.0% (engine 0.0%, burned cap 0.0%) | at cap 0.0% | no-op 19.5%

# later — two more seeds into the SAME set; the first two are skipped, not replayed
rollout(scenario=ScorableNegotiation(), instances=instances, participant=seat_lineup,
        seeds=[0, 1, 2, 3], arms=["moves_chat"], out="runs/pilot", config=cfg)
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MANIFEST_NAME` |  |  |
| `MANIFEST_SCHEMA` |  |  |
| `PLACEHOLDER_BUDGET` |  |  |
| `ParticipantFactory` |  |  |
| `RolloutKey` |  |  |
| `ScenarioFactory` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`RolloutConfigMismatch`](RolloutConfigMismatch.md) | An append's config fingerprint disagrees with the set's manifest — refused rather than silently mixed. |
| [`RolloutSet`](RolloutSet.md) | A directory of episodes plus the manifest that says what produced them. |

## Functions

| Name | Summary |
|---|---|
| [`config_fingerprint`](config_fingerprint.md) | Stable SHA256 over `config`, canonicalized (sorted keys, compact separators, non-JSON values repr'd). |
| [`rollout`](rollout.md) | Run `instances x seeds x arms` into the rollout set at `out` (creating or resuming it) and return it. |
