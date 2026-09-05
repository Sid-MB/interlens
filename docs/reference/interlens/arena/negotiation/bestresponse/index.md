# `interlens.arena.negotiation.bestresponse`

Exact expectimax best-response oracle over (remaining rounds x deal space x type posterior).

Yields the headline **per-turn surplus-loss** metric `V(oracle action) - V(agent action)` in surplus units
(the centipawn-loss analog: Regan & Haworth, "Intrinsic Chess Ratings," AAAI 2011; McIlroy-Young et al.,
KDD 2020) and **revealed-strategy exploitability** against fixed counterparts (Johanson, Waugh, Bowling &
Zinkevich, "Accelerating Best Response Calculation in Large Extensive Games," IJCAI 2011, pp. 258-265).

WHY exact posterior-averaging rather than MCTS/determinization: at our scale (|D| ~ 720, T ~ 24, |types| ~
10^3) the backward induction is ~10^5-10^6 elementary ops, so no sampling is needed; and averaging the value
over the *type posterior* (rather than solving determinized full-information games and averaging outcomes)
avoids strategy-fusion / non-locality bias — Frank & Basin, "Search in games with incomplete information,"
AIJ 100(1-2):87-123, 1998; ISMCTS: Cowling, Powley & Whitehouse, IEEE TCIAIG 4(2):120-143, 2012.

Protocol modeled: each round a (rotating) proposer offers a deal; all other seats accept/reject;
the deal closes iff the game's fixed acceptance quorum (and every veto seat) accepts; otherwise play
continues to the next round with the discount
`delta`; after the deadline, no-deal pays surplus 0. Two regimes share one backward induction:

- **Full information** (`value_to_go_full_info`): all sheets known; opponents accept iff the offer beats
  their own discounted continuation, and each proposer offers its value-maximizing all-accepted deal. Exact;
  this is the path the unit tests pin.
- **Belief-averaged** (`value_to_go_beliefs`): opponents' acceptance is the posterior mass of accepting
  types (`accept_prob_fn`) and opponent proposals are modeled from the posterior; the agent's own
  acceptance uses its (known) surplus vs its continuation. A documented approximation for LLM-divergence use.

Complexity: building the per-deal all-accept masks is `O(T * n * |D|)` (vectorized); the belief path adds
the `O(n * |types| * |D|)` acceptance-probability tensor once. Sub-second at the target scale.

## Classes

| Name | Summary |
|---|---|
| [`BestResponseOracle`](BestResponseOracle.md) | Per-turn expectimax best response for one seat. |

## Functions

| Name | Summary |
|---|---|
| [`conditional_vote_values`](conditional_vote_values.md) | Value this seat's yes/no vote after conditioning on votes already cast. |
| [`conditional_vote_values_batch`](conditional_vote_values_batch.md) | :func:`conditional_vote_values` for `K` offers at once; returns four `(K,)` arrays. |
| [`exploitability`](exploitability.md) | `BR_value - revealed_value`: how much surplus the agent leaves on the table vs its exact best response, holding the (full-information) counterpart continuation fixed. |
| [`passage_probability`](passage_probability.md) | Probability each deal passes under independent responder votes. |
| [`value_to_go_beliefs`](value_to_go_beliefs.md) | Agent-`agent` continuation `Vi[t]` (shape `(T+2,)`) under the posterior. |
| [`value_to_go_full_info`](value_to_go_full_info.md) | Joint continuation values `V[t]` (shape `(T+2, n)`) for *every* seat under subgame-perfect alternating-offers play with the fixed `min_accept` quorum, required `veto_seats`, and no-deal surplus 0. |
| [`value_to_go_full_info_cached`](value_to_go_full_info_cached.md) | :func:`value_to_go_full_info` memoized on the game tables — the whole `V` curve, computed ONCE. |
