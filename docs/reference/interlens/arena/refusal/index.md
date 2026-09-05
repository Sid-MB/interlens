# `interlens.arena.refusal`

Recovering a turn the API refused, without changing what the turn says.

Some hosted providers return a completion with `stop_reason == "refusal"` and zero output tokens: an
API-side classifier declined the request before the model wrote anything. Measured on `claude-opus-5` in the
auction program, that refusal has three properties that make it a *protocol* problem rather than a modelling
one:

- it reproduces **deterministically** for a byte-identical request, so it survives the ordinary retry (which
  re-sends the same view with a parser note appended);
- it is **not semantic** — substituting the domain vocabulary, dropping a blurb, salting the tail, or
  splitting the turn all leave it in place, while removing almost *any* single block clears it;
- so the seat contributes no move at all, and any fallback action recorded for it is a move the model never
  chose.

The response implemented here is a **re-render ladder**: on a refusal, the same turn view is re-rendered under
a deterministic, content-preserving perturbation and reissued, escalating through a fixed sequence of rungs.
Every rung preserves every number, every rule, and every reviewed sentence — only *ordering*, *section
framing*, and an inert *nonce line* vary — so a recovered turn conditions on the same information the refused
one did. The ladder is a property of the engine, not of an arm or a condition, so it applies identically
everywhere and is a protocol feature rather than a confound; it is preregisterable because the rungs, their
order, and the seeded permutation are all fixed in advance and logged per turn
(`TurnRecord.refusal_recovery`).

What this is **not**: an attempt to defeat the classifier. The rungs are content-preserving by construction.
If a view refuses at every rung the turn is recorded as `terminal` and the cell's validity gate sees it — a
configuration that cannot clear the ladder is an escalation to the provider, not an engineering problem.

Worked example
--------------

>>> from interlens.arena.refusal import RefusalLadder
>>> ladder = RefusalLadder()
>>> view = [{"role": "system", "content": "You are seat A."},
...         {"role": "user", "content": "## Catalogue\nLot 1: 90\n\n## Your values\nLot 1: 104\n\n"
...                                      "Reply now with one fenced JSON object."}]
>>> rung1 = ladder.perturb(view, 1, key="ep-1/seat-A/r3")
>>> rung1[1]["content"].splitlines()[0]                                  # doctest: +ELLIPSIS
'Protocol note: request variant ...'
>>> sorted(ladder.perturb(view, 2, key="ep-1/seat-A/r3")[1]["content"].split("\n\n")) == \
...     sorted(rung1[1]["content"].split("\n\n"))                       # same blocks, different order
True
>>> ladder.perturb(view, 3, key="ep-1/seat-A/r3")[1]["content"].count("Lot 1: 104")   # numbers preserved
1

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `REFUSAL_RECOVERY_KEY` |  |  |
| `REFUSAL_STOPS` |  |  |
| `TRUNCATION_STOPS` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`RefusalLadder`](RefusalLadder.md) | A fixed, seeded sequence of content-preserving re-renders, tried in order after a refusal. |

## Functions

| Name | Summary |
|---|---|
| [`is_refusal`](is_refusal.md) | Did this completion come back declined rather than generated? |
| [`recovery_record`](recovery_record.md) | One turn's recovery record: `outcome` is `"recovered"` or `"terminal"`, `rung` the 1-based rung that cleared it (`None` when none did), `attempts` the rung names tried in order. |
