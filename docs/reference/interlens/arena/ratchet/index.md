# `interlens.arena.ratchet`

Adaptive difficulty ratchet: find the level where a model stops clearing the bar, then measure there.

A ceiling-saturated cell measures nothing — if every episode scores ~1.0 the comparison has no room to move.
The ratchet drives any `Scenario` with a difficulty ladder to the *found level*: the first level whose probe
mean fails the bar (default: mean primary < 0.75 of ceiling over `probe_n` probe episodes). Three phases,
run through an `EpisodePool`:

1. **probe** — `probe_n` episodes per level, climbing while the mean clears `step_up`. With
   `speculative=True` the first `wave` levels are probed CONCURRENTLY (then the rest, if every probed
   level cleared the bar) — the wall-clock optimization from the arena experiments' re-ratchet runs; the found
   decision is the same pure function either way (`found_level`).
2. **measure** — `meas_n` episodes at the found level and its neighbor below (or above when found == 0), on
   the deterministic shared instance pool, offset past the probe block so probe and measurement instances
   never overlap.
3. **solo baselines** — paired solo episodes on the SAME instances, each under a `TokenBudget` equal to the
   median team tokens-out at that level (the matched-compute recipe).

State is serialized after every batch, so a restarted ratchet resumes where it stopped and never duplicates a
completed episode (completed instances are skipped by id — paired-join safe). Instance pools are deterministic
per (scenario, level): instance `i` uses seed `level*10000 + i`, shared by every arm and model.

Provenance: the collaboration-arena experiments' ratchet (sequential form) and their re-ratchet runs
(speculative form), re-based onto the `EpisodePool` driver.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MEAS_N` |  |  |
| `PROBE_N` |  |  |
| `STEP_UP` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`DifficultyRatchet`](DifficultyRatchet.md) | Probe -> measure -> paired-solo driver over one scenario/participant pair (see the module docstring). |

## Functions

| Name | Summary |
|---|---|
| [`found_level`](found_level.md) | The found level implied by a set of probe means: the first (ascending) probed level whose mean fails the bar, else the highest level probed (the model never dropped below the bar). |
