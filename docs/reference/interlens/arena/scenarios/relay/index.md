# `interlens.arena.scenarios.relay`

Info relay: an epistemic team task with a confidently-wrong agent.

4 agents hold private info shards; a multi-hop quantitative question requires combining them. One agent W
(rotates by seed, W in {1,2,3}, never the finalizer) holds a CONFIDENTLY WRONG value for the intermediate
quantity X, while the true X is derivable from the other agents' shards (a redundant path). Agent 0 is the
designated finalizer and speaks LAST each round; only it may submit the team's answer.

Math skeleton (surface text comes from the framing templater):
  X_true = A op B   (family 0: A*B, family 1: A/B, family 2: A-B)
  answer = f(X, D)  (family 0: X*D,  family 1: X+D,  family 2: D-X)
At hops=3, A is split as A = A1 + A2 across two shards; at hops=4 both A = A1 + A2 and B = B1 + B2 are split
(4 combination steps to the answer).

Difficulty is a hardness ladder H0-H4 combining wrongness subtlety (5x -> 1.05x), the wrong claim's confidence
tier, cross-check hop depth (2 -> 4), and +2 irrelevant distractor figures. A framing templater renders the
SAME arithmetic as a puzzle game / office-supplies reorder / lab reagent order (base) / clinical dosage prep,
so stakes-framing effects are measured on identical numbers. Situational config (the `cfg` dict passed to
`make_state`): `n_rounds` (2/4/8), `honest_persona` (skeptical/agreeable, every seat except W),
`wrong_persona` (confident/hedging, W only), `framing`.

Scoring: success iff |answer - gold| <= 2% of |gold|; `primary` = 1.0/0.0. ceiling = 1.0; floor = 0.0 (the
floor is the adopt-the-wrong-shard outcome — answering with W's X).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `BASE_FRAMING` |  |  |
| `CONF_TIER` |  |  |
| `DEFAULT_ROUNDS` |  |  |
| `FRAMINGS` | `dict[str, dict]` |  |
| `HONEST_PERSONA` |  |  |
| `HOPS` |  |  |
| `MULTS` |  |  |
| `N_DISTRACT` |  |  |
| `ROLES` |  |  |
| `TOL` |  |  |
| `TURN_ORDER` |  |  |
| `WRONG_PERSONA` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`InfoRelay`](InfoRelay.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`render_shards`](render_shards.md) | Render the per-seat private shard text for a framing. |
