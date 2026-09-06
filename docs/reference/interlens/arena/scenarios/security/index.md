# `security`

Module `interlens.arena.scenarios.security`

Security dilemma: a repeated 2-party build/deescalate/attack game with noisy intelligence.

Each of 12 rounds has (1) a message phase — seat A then seat B sends one public message — and (2) a
simultaneous action wave: each seat privately commits `"build"`, `"deescalate"`, or `"attack"` as a
fenced JSON action (malformed after the one allowed retry → `"build"`).

Stage payoffs (symmetric, public): both deescalate +4/+4; both build +1/+1; build vs deescalate +5/+2
(builder gets 5); attack vs non-attack: attacker +6+B_fs, victim −6; both attack −4/−4. `B_fs` is the
first-strike bonus (the difficulty knob).

**Absorbing spiral**: once BOTH seats attack in the same round, every remaining round is forced mutual attack
at −4/−4 — no further requests; the forced rounds are recorded as public moderator events. A one-sided attack
is NOT absorbing.

**Signal noise**: with probability `p` (the second difficulty knob), a seat's *observation* of the
opponent's action that round is flipped to one of the other two actions (uniform). True actions always drive
payoffs; observations drive what each seat is told, via per-seat-private moderator events. Each round a seat
is told the (possibly misreported) opponent action, its own true payoff this round, and its own cumulative
payoff — never the true action, and never the opponent's cumulative payoff (which would let it back out the
true action). Noise draws use `random.Random(episode_seed ^ round)`, one RNG per round, draws in seat order,
so episodes are exactly reproducible and replayable from their seed.

Scoring: `joint` = sum of both cumulative payoffs; ceiling joint = 96 (mutual deescalation for 12 rounds);
`primary` = joint/96 (may be negative); floor = both-build every round = 24/96 = 0.25. `success` = the
episode avoided the war spiral. No solo arm (the game is irreducibly 2-party).

Provenance: the collaboration-arena experiments' E3 environment, ported verbatim onto the `Scenario`
contract (state machine, payoffs, noise draws, and instance seeds unchanged — stored episodes replay).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ACTIONS` |  |  |
| `HORIZON` |  |  |
| `LEVELS` |  |  |
| `ROLES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`SecurityDilemma`](SecurityDilemma.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`stage_payoffs`](stage_payoffs.md) | Stage payoffs `(pa, pb)` for true actions `a` (seat 0) and `b` (seat 1). |
