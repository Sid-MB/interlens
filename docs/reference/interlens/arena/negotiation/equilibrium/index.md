# `equilibrium`

Module `interlens.arena.negotiation.equilibrium`

Banks-Duggan stationary-equilibrium oracle for the multilateral unanimity bargaining game.

Model (random-proposer, closed rule, unanimity): Baron & Ferejohn, "Bargaining in Legislatures," APSR
83(4):1181-1206, 1989; generalized to arbitrary alternative spaces / utilities by Banks & Duggan, "A
Bargaining Model of Collective Choice," APSR 94(1):73-88, 2000, and QJPS 1(1):49-85, 2006. No-delay
stationary characterization with continuation values `v` and disagreement flows `tau`:

    A_i(v) = { d in D : u_i(d) >= (1 - delta) * tau_i + delta * v_i }     # i's acceptance set
    A(v)   = intersection_i A_i(v)                                        # unanimity social acceptance set
    x_j*(v) = argmax_{d in A(v)} u_j(d)                                   # proposer j best-in-set (else delay)
    v_i     = sum_j p_j * u_i(x_j*(v))   (+ delay branch)                 # fixed point

Solved by damped fixed-point iteration `v^{k+1} = (1 - lambda) v^k + lambda * T(v^k)` over the enumerated
`D` (each sweep `O(n * |D|)`); a softmax-over-ties proposer rule (`tie_temperature > 0`) is available as
the fallback when the discrete argmax correspondence makes the hard iteration cycle.

Sanity anchor (built in, `divide_the_dollar` + `okada_closed_form`): Okada, "A Noncooperative Coalitional
Bargaining Game with Random Proposers," GEB 16(1):97-108, 1996 — the unanimity closed form is proposer keeps
`1 - delta (n-1)/n`, each responder gets `delta/n`, and `v_i = 1/n`.

Caveats (docstring, not asserted): Eraslan, "Uniqueness of Stationary Equilibrium Payoffs in the Baron-
Ferejohn Model," JET 103(1):11-30, 2002, gives uniqueness for `q < n` rules; general *unanimity* games can
have delay / multiplicity / non-existence of a pure no-delay equilibrium (Britz, Herings & Predtetchinski).
Existence here is in mixed proposal strategies with pure stage-undominated voting on the finite (compact) D.

## Classes

| Name | Summary |
|---|---|
| [`EquilibriumOracle`](EquilibriumOracle.md) | Mounts the stationary equilibrium as a per-turn reference: what the standing offer *should* look like for whichever seat currently proposes, plus the proposer-power decomposition `v*`. |
| [`EquilibriumSolution`](EquilibriumSolution.md) | Result of the fixed-point solve. |

## Functions

| Name | Summary |
|---|---|
| [`divide_the_dollar`](divide_the_dollar.md) | A discrete divide-the-dollar TU game as `GameTables`: deals = integer allocations of `steps` units among `n` players (compositions), `u_i = share_i = units_i / steps`, `tau = 0`. |
| [`okada_closed_form`](okada_closed_form.md) | The Okada 1996 unanimity closed form: `{"proposer_keeps": 1 - delta(n-1)/n, "responder_gets": delta/n, "value": 1/n}`. |
| [`solve_equilibrium`](solve_equilibrium.md) | Damped fixed-point solve for the Banks-Duggan stationary continuation values. |
