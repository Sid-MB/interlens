# `interlens.arena.scenario`

The `Scenario` interface: a pure game-logic state machine, participant-agnostic.

A scenario owns everything about the *game* — instance generation (with an exact solver for
ceilings/verification), per-seat private framing, the turn protocol, structured-action parsing, early
termination, and scoring — and nothing about *models*: it emits `SeatRequest`s (who must speak now, on what
view) and consumes the resulting text. The engine (`engine.py`) owns persistence, retries, provisional
forking, budgets, and driving participants.

(The concept is a *scenario*, not an "environment": these are turn-based game protocols with exact scorers,
without RL/gym step/reward semantics.)

State is a plain dict owned by the scenario. Required keys maintained by every scenario:

- `events`: `list[{seat, content, only?}]` — the public transcript (`MODERATOR` for announcements;
  `only` restricts an event to named seats)
- `round`: 1-based current round
- `done`: bool
- `arm`: `"team"` | `"solo"` | variant tags like `"team-greedy"`

The engine sets `state["budget_exhausted"] = True` when an episode token/cost budget fires; scenarios must
then steer to a forced finalization (both bundled scenarios do).

## Classes

| Name | Summary |
|---|---|
| [`Scenario`](Scenario.md) |  |
