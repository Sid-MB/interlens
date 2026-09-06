# `llm_calibrated`

Module `interlens.arena.negotiation.llm_calibrated`

Private-information rational negotiation against an **empirically fitted LLM opponent model**:
:class:`LLMCalibratedRationalPolicy`.

Why this exists. :class:`~interlens.arena.negotiation.strategies.BayesianRationalPolicy` is optimal against
opponents whose signal lives in their offer sequence and who accept iff a deal clears their reservation. Notes
0057/0045/0053 established that at a real LLM table both assumptions fail: the belief posterior is
signal-starved (LLM offers barely move, so the concession likelihood extracts ~nothing), and measured LLM
acceptance is nothing like a step at surplus 0. The result is the 0.20-0.23 closure collapse. This module
keeps the composed agent's *decision machinery* — optimal stopping, expectimax proposals, the IR floor, the
walk rule — and swaps the two RATIONALISTIC priors for quantities **measured from ~1,500 frozen LLM episodes**:

1. **Acceptance**: `P(opponent accepts deal d)` becomes the posterior mixture of a fitted acceptance curve
   evaluated on each hypothesis type's normalized surplus, instead of the posterior mass of types whose
   step-model would accept. The same Hindriks–Tykhonov posterior; only the within-type response model changes.
   (The full-information version of this swap is :class:`~interlens.arena.negotiation.calibrated.CalibratedRationalPolicy`;
   this class is its private-information counterpart and reuses its
   :class:`~interlens.arena.negotiation.calibrated.AcceptanceCurveSet` containers unchanged.)
2. **Future offers**: the optimal-stopping reservation `v_j = delta * E[max(X, v_{j-1})]` is computed over
   the EMPIRICAL distribution of what LLM opponents actually table at each round position
   (:class:`OfferCurveSet`), instead of the belief-induced "deals that could close, weighted by posterior
   passage" distribution. This is the change note 0045 points at: the Bayesian reservation never decays into a
   known-good standing offer because its imagined offer distribution stays optimistic; the measured incoming-z
   distribution is far thinner, so waiting is worth less and the reservation admits real offers.

Everything is in the program's affine-invariant `z` space (`surplus_norm`: own surplus over own best
attainable surplus), so one fitted model pools across games and sheets. The policy is deterministic given
`(state, fitted model)`.

Worked example:

```python
from interlens.arena.negotiation.llm_calibrated import LLMOpponentModel, LLMCalibratedRationalPolicy

model = LLMOpponentModel.from_json("opponent_model.json")   # written by the fitting lane
policy = LLMCalibratedRationalPolicy(model=model, opponent_model="claude-opus-5")
# seat it exactly as BayesianRationalPolicy is seated (PolicyParticipant / mixed_table)
```

Degenerate-control identities (pinned by `tests/test_negotiation_llm_calibrated.py`):

- step acceptance curves reproduce the parent's posterior acceptance table bit-for-bit (a step in per-type
  `z` is exactly "this type's utility clears its tau", which is what the parent's mixture thresholds);
- with `offers=None` the whole `act`/`vote` path is the parent's own (only the acceptance table is
  swapped), so step curves + no offer model = byte-identical actions to `BayesianRationalPolicy`.

## Classes

| Name | Summary |
|---|---|
| [`LLMCalibratedRationalPolicy`](LLMCalibratedRationalPolicy.md) | :class:`BayesianRationalPolicy` for PRIVATE-information tables with both rationalistic priors replaced by the fitted :class:`LLMOpponentModel` (module docstring). |
| [`LLMOpponentModel`](LLMOpponentModel.md) | Everything the calibrated policy consumes, loaded from ONE fitted artifact. |
| [`OfferCurve`](OfferCurve.md) | One opponent model's fitted distribution of the `z` an offer delivers to its RECIPIENT, as a function of round position. |
| [`OfferCurveSet`](OfferCurveSet.md) | A fitted :class:`OfferCurve` per opponent model. |
