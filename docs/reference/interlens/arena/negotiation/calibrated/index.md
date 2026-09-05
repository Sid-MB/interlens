# `interlens.arena.negotiation.calibrated`

Behaviourally-calibrated rational negotiation: :class:`CalibratedRationalPolicy`.

The composed Bayesian agent (:class:`~interlens.arena.negotiation.strategies.BayesianRationalPolicy`) is
optimal against the opponent model it is given, and the opponent model it is given is **wrong for LLMs**. Under
full information it assumes an opponent accepts a deal iff that deal clears the opponent's reservation — a step
function at surplus 0. Measured LLM seats do not behave that way: they accept below their threshold 20-94% of
the time, and they refuse plenty of offers that clear it.

This module keeps *every* other part of the agent — the optimal-stopping reservation, the expectimax
best-response, the individual-rationality floor on its own acceptances, the walk-if-hopeless rule — and swaps
that one step function for an **empirically fitted** `P(accept | z, rounds_left)` curve per opponent model.
The whole intervention is the override of
:meth:`~interlens.arena.negotiation.strategies.BayesianRationalPolicy._accept_prob_table`; nothing else is
touched, which is what makes the Bayes-vs-calibrated contrast a clean single-factor comparison rather than two
different agents.

Why that is the interesting knob: the Bayesian agent's proposals are *generous* precisely because it models
opponents as refusers. Tell it the truth — that these opponents cave — and it should best-respond by demanding
more. The preregistered question (H2-strong) is whether it then extracts more than the Bayesian agent does, and
whether the table gets **less fair** as the extraction gets more cynical.

FULL INFORMATION ONLY (deliberate). Computing `z` needs the opponent's own utility for a deal, which only
exists under `--info full`. Under private info this class falls straight through to the inherited belief-oracle
path and is therefore *identical* to :class:`BayesianRationalPolicy` — it does not silently substitute a
half-calibrated model. Calling code that wants the calibrated behaviour must run full-info tables; the policy
records which path it took on `last_path` so a run can be audited rather than assumed.

Worked example
--------------

```python
from interlens.arena.negotiation.calibrated import AcceptanceCurveSet, CalibratedRationalPolicy

curves = AcceptanceCurveSet.from_fit_artifact("self_benefit/acceptance_curves.json")
policy = CalibratedRationalPolicy(curves=curves, opponent_model="Qwen/Qwen3-8B")
# ... seat it exactly as BayesianRationalPolicy is seated (table.policy_seat / mixed_table)
```

A step-function curve reproduces the Bayesian agent **exactly** — that equivalence is the regression test in
`tests/test_negotiation_calibrated.py` and it is the reason the curve object can express a step at all:

```python
step = AcceptanceCurveSet.step()          # P(accept) = 1 iff surplus >= 0
CalibratedRationalPolicy(curves=step, opponent_model="anything")   # == BayesianRationalPolicy
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Z_SPACES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`AcceptanceCurve`](AcceptanceCurve.md) | One opponent model's fitted `P(accept \| z, rounds_left)`. |
| [`AcceptanceCurveSet`](AcceptanceCurveSet.md) | A fitted curve per opponent model, plus the `z` convention they were all fit in. |
| [`CalibratedRationalPolicy`](CalibratedRationalPolicy.md) | :class:`BayesianRationalPolicy` with its opponent acceptance model replaced by fitted behavioural curves. |
