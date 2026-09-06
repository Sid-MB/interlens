# `strategies`

Module `interlens.arena.negotiation.strategies`

The executable rational / scripted negotiator zoo as **policies** (`state -> action`), the computable
opponent pool the LLMs are measured against.

Concession curves — Faratin, Sierra & Jennings, "Negotiation decision functions for autonomous agents,"
Robotics and Autonomous Systems 24(3-4):159-182, 1998, §3.1: time-dependent tactic
`alpha(t) = k + (1 - k) * (t / T)^{1/beta}` with **Boulware `beta < 1`** (concede near the deadline) and
**Conceder `beta > 1`** (concede early); utility-space restatement Baarslag thesis, TU Delft 2014, §2.3.3.

MiCRO — de Jonge, IJCAI 2022, pp. 223-229 (multilateral extension arXiv:2510.17401): sort own outcomes
descending; with `m` distinct offers made and `n_min` the minimum distinct-offer count across opponents,
concede one new outcome iff `m <= n_min` else repeat; accept iff incoming >= the next offer you'd make.
Parameter-free, ordinal-only.

Tit-for-tat — Faratin §3.3 behavior-dependent tactic (reproduce the opponent's concession). Tough/Hardliner
— always demand the own optimum. Acceptance conditions AC_next / AC_const / AC_time / AC_combi — Baarslag,
Hindriks & Jonker, "Acceptance Conditions in Automated Negotiation," SCI 435, 2013, eqs. (4.4)-(4.8).

`BayesianRationalPolicy` composes the belief + acceptance + best-response oracles — the headline rational
agent: update beliefs from observed offers, best-respond on proposals, accept by optimal stopping.

All policies return typed actions (`Propose`/`Accept`/`Reject`/`Walk`) and read a `NegotiationState`,
so a `PolicyParticipant` wrapping any of them is an interchangeable seat with an LLM participant.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ZOO` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`ACCombi`](ACCombi.md) | AC_combi(T, alpha): `AC_next OR (AC_time(T) AND incoming >= alpha)` (eq. 4.8; combi variants empirically dominate). |
| [`ACConst`](ACConst.md) | AC_const(alpha): accept iff `incoming >= alpha` (eq. 4.6). |
| [`ACNext`](ACNext.md) | AC_next(alpha, beta): accept iff `alpha * incoming + beta >= planned_next` — the incoming bid is at least as good as what you were about to send (Baarslag eq. 4.4; alpha=1, beta=0 standard). |
| [`ACTime`](ACTime.md) | AC_time(T): accept anything once the time fraction reaches `t_frac` (eq. 4.7). |
| [`AcceptanceCondition`](AcceptanceCondition.md) | Decide whether to accept the standing offer given the agent's own utility of it (`incoming`) and of the deal it is about to propose (`planned_next`), both on the normalized `[0, 1]` scale. |
| [`BayesianRationalPolicy`](BayesianRationalPolicy.md) | The composed rational negotiator = belief oracle + acceptance oracle + best-response oracle. |
| [`DeclaredGreedyHoldoutPolicy`](DeclaredGreedyHoldoutPolicy.md) | :class:`GreedyHoldoutPolicy` that ANNOUNCES its ultimatum on its first turn and then never speaks again. |
| [`DemandFractionPolicy`](DemandFractionPolicy.md) | Declare a demand LEVEL and hold to it: accept any package worth at least `accept_frac` of this seat's own MAXIMUM achievable score, propose its own best deal, and announce the numeric rule up front. |
| [`FairnessOraclePolicy`](FairnessOraclePolicy.md) | Omniscient **fairness oracle**: proposes and votes to maximize the table's normalized Nash welfare. |
| [`FairnessRationalPolicy`](FairnessRationalPolicy.md) | Private-information **fairness algorithmic** agent: the same welfare objective, estimated under its Bayesian posterior over the other seats' hidden sheets and thresholds. |
| [`GreedyAnchorPolicy`](GreedyAnchorPolicy.md) | Maximally selfish proposals plus the same reservation gate: always tables its OWN best deal `argmax_d u_self(d)` (canonical tie-break, tabled once and held), and accepts any standing offer with surplus >= 0, declining below. |
| [`GreedyHoldoutPolicy`](GreedyHoldoutPolicy.md) | Take it or leave it: proposes its own-max deal exactly as :class:`GreedyAnchorPolicy` does, but accepts ONLY that deal — every other offer is declined, including offers that are individually rational for it. |
| [`MiCROPolicy`](MiCROPolicy.md) | MiCRO (de Jonge 2022; multilateral variant arXiv:2510.17401): minimal-concession, parameter-free. |
| [`NaiveTitForTatPolicy`](NaiveTitForTatPolicy.md) | Behavior-dependent tit-for-tat (Faratin §3.3): mirror the opponent's most recent concession (measured in this agent's own normalized utility) as an equal concession from the agent's last demand; start near the own optimum. |
| [`NegotiationState`](NegotiationState.md) | The structured state a `Policy` reads to compute its next action — the machine-readable counterpart of the text `view` an LLM seat reads, so a `PolicyParticipant` and an LLM participant are interchangeable seats. |
| [`PassiveGatePolicy`](PassiveGatePolicy.md) | Pure veto discipline, zero strategy: NEVER proposes; accepts any standing offer that clears its own reservation (surplus >= 0) and declines everything below it, on ordinary turns and on the terminal vote alike. |
| [`Policy`](Policy.md) | A deterministic (or seeded) negotiation policy: `policy(state) -> action`. |
| [`TimeDependentPolicy`](TimeDependentPolicy.md) | Faratin time-dependent tactic: concede own utility along `alpha(t) = k + (1 - k) (t/T)^{1/beta}` toward the reservation, propose the least-concession IR deal at/above the current target, and accept per `acceptance`. |
| [`ToughPolicy`](ToughPolicy.md) | Hardliner: always demand the own optimum; accept only offers within `accept_frac` of the own max (and above reservation). |

## Functions

| Name | Summary |
|---|---|
| [`fit_belief`](fit_belief.md) | A :class:`~interlens.arena.negotiation.beliefs.BeliefOracle` fitted to everything `state` publicly reveals about the other seats — one posterior per opponent, updated from their observed offers. |
| [`parse_negotiation_state`](parse_negotiation_state.md) | The scenario-emitted `negotiation_state` block in `text` (the inner dict of the last fenced JSON object carrying that key), or `None`. |
