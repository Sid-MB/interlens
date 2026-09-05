# `interlens.arena.negotiation.acceptance`

Optimal-stopping acceptance oracle: when is accepting the standing offer better than holding out?

Core recursion — Baarslag & Hindriks, "Accepting Optimally in Automated Negotiation with Incomplete
Information," AAMAS 2013, pp. 715-722, Eqs. (1)-(3) (http://www.ifaamas.org/Proceedings/aamas2013/docs/p715.pdf):

    v_0 = 0
    v_j = E[ max(X_{j-1}, v_{j-1}) ] - C          # j = rounds remaining; X_j ~ F_j the offer distribution
    accept x  iff  x >= v_j                        # Algorithm 1

with `F_j` = the offer-distribution mixture induced by the belief posterior (`offer_surplus_pmf` below).
Closed form for a uniform opponent (their Prop. 3.1): `v_j = 1/2 + v_{j-1}^2 / 2` (reproduced by the unit
test). This module **generalizes** the recursion with a per-round discount `delta` and a disagreement
`flow` so the reservation is an *endogenous, time-varying* continuation value tau_i(t) (McCall, "Economics
of Information and Job Search," QJE 84(1):113-126, 1970 — the reservation-wage recursion); the additive cost
`C` and the discount `delta` are the two friction conventions and coincide with Baarslag at
`delta=1, flow=0`. An optional outside-option floor follows Li, Giampapa & Sycara, IEEE SMC-C 36(1):31-44,
2006 (reservation price = valuation - reservation utility; conservative order-statistic OU).

DEADLINE WARNING (Sandholm & Vulkan, "Bargaining with Deadlines," AAAI-99, pp. 44-51): with a firm common
deadline and NO discounting, the unique sequential-equilibrium play is extreme brinkmanship — both wait until
the earlier deadline, then the deadline-bound party concedes the whole surplus. So if the game's only
impatience is a hard turn-count deadline, this oracle's "hold out" recommendation is rational but degenerate;
pass a `discount < 1` (or a breakdown-risk / outside-option) to make interior concession rational.

The single most diagnostic per-turn signal in practice (accept-too-early leaves surplus on the table;
never-accept blows the deadline).

## Classes

| Name | Summary |
|---|---|
| [`AcceptanceOracle`](AcceptanceOracle.md) | Values accept / reject / propose / walk at one turn via optimal stopping. |
| [`ThresholdOracle`](ThresholdOracle.md) | The trivial hard-violation detector: accepting or proposing a deal below one's *own* threshold is a strict rationality error (agreeing below your BATNA is worse than no deal — Abdelnabi et al.'s "wrong deals" metric, which runs 7-20% even for strong models). |

## Functions

| Name | Summary |
|---|---|
| [`offer_surplus_pmf`](offer_surplus_pmf.md) | The distribution `F` of the surplus `agent` expects to *receive*, induced by the belief posterior. |
| [`reservation_values`](reservation_values.md) | Backward-induction reservation curve `[v_0, v_1, ..., v_T]` where `v_j` is the reservation with `j` rounds remaining; **accept an offer of surplus x iff x >= v_j**. |
