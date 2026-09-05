# `interlens.arena.auction.priors`

The persona-conditioned prior: the generative model, the persona table, fact rendering data, and the
posterior a rational seat actually computes.

**The persona IS the prior** (design.md §2.2). Public facts about a bidder are the sufficient statistics of
everyone else's belief about its valuation curve, and the mapping from facts to distribution is announced, so
a rival holding only public information can compute a genuinely informative posterior — and a computable
Bayesian seat can compute it exactly. One equation governs every value structure and every stage:

```python
ell_ijt = log(B_jt) + (beta / K) * (a_i . w_j) + z_it + eps_ijt
v_ijt   = round(exp(ell_ijt)) + round(gamma_i * R_jt)
```

:func:`realize_values` is the ONLY implementation of that equation in the package; :mod:`.spec` composes it
with the persona table below. Every function here takes plain arrays and scalars — never an `AuctionSpec` —
so this module has no dependency on the spec and the two cannot form a cycle.

Three groups of things live here:

1. **The persona table** (:data:`PERSONAS`) and the catalogue draw (:func:`draw_loadings`).
2. **Fact rendering DATA** — the public/private fact KEYS and their computed values (:func:`public_facts`,
   :func:`private_facts`), with tercile boundaries that are themselves public. The prose lives in
   `docs/templates/`; the scenario lane connects it through :func:`register_fact_renderer`.
3. **The posterior machinery** a rational seat needs: :class:`RivalPosterior`, a quadrature grid over one
   rival's `(z, eps)` given its public `a_i`, supporting conditioning on the public events a stage
   reveals (exits, standing bids, winning).

On reuse of `negotiation/beliefs.py`: its `build_type_grid` enumerates weight-profiles x shape-assignments
x reservation levels over a DISCRETE `DealSpace` option grid, and its `BeliefState` scores hypotheses by
concession-likelihood over observed OFFERS. Neither transfers — an auction type is a pair of continuous
Gaussian draws and the observable is a price, not a package — so the analogue is rebuilt here as a
Gauss-Hermite product grid. What DOES transfer is the shape of the interface (an enumerated type grid with
weights, conditioned by observation, exposing an induced value distribution), and the damping idea, which
appears here as :meth:`RivalPosterior.condition`'s `floor` so a single surprising observation cannot
collapse the posterior.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ATTR_NAMES` | `tuple[str, ...]` |  |
| `COMMON_PRIVATE_FACT_KEYS` | `tuple[str, ...]` |  |
| `FACT_RENDERERS` | `dict[str, 'Callable[[object], str]']` |  |
| `PERSONAS` | tuple[[Persona](Persona.md), ...] |  |
| `PERSONAS_BY_ID` | dict[str, [Persona](Persona.md)] |  |
| `TERCILE_LABELS` | `tuple[str, str, str]` |  |
| `TERCILE_Z` | `float` |  |

## Classes

| Name | Summary |
|---|---|
| [`Persona`](Persona.md) | One of the five archetypes of design.md §2.2, fixed across the bank and across all stages. |
| [`RivalPosterior`](RivalPosterior.md) | What one seat believes about ONE rival's realized valuations, from public information alone. |

## Functions

| Name | Summary |
|---|---|
| [`attribute_score`](attribute_score.md) | The public affinity matrix `(n_bidders, n_items)` of dot products `a_i . w_j`. |
| [`build_type_grid`](build_type_grid.md) | The auction analogue of `negotiation/beliefs.py::build_type_grid`: one rival's type is the pair `(z, eps)` of continuous Gaussian draws, so the grid is a Gauss-Hermite product rule rather than an enumeration of discrete hypotheses. |
| [`draw_loadings`](draw_loadings.md) | Draw the persistent public loading matrix `w` of shape `(n_items, K)`. |
| [`make_coherent`](make_coherent.md) | The RNG-neutral coherence permutation: a persona's own-best slot is never one its public attributes point away from (design.md §2.2, the `scenarios/priors.py::_make_role_coherent` analogue). |
| [`private_facts`](private_facts.md) | The private fact VALUES for one seat at one stage — re-rendered every stage because `z` redraws while the public card is fixed (design.md §2.2). |
| [`public_facts`](public_facts.md) | The public fact VALUES for one seat card: the persona's own keys, every attribute entry as its own fact (each entry of `a_i` is one public fact, per design.md §2.2), and the public mechanism-relevant parameters. |
| [`realize_values`](realize_values.md) | The value equation of design.md §2.2, evaluated for every `(bidder, slot)` pair of one stage. |
| [`register_fact_renderer`](register_fact_renderer.md) | Register the prose renderer for one fact key. |
| [`render_facts`](render_facts.md) | Render fact values to prose lines through :data:`FACT_RENDERERS`, in `keys` order (default: the dict's own order). |
| [`rival_max_cdf`](rival_max_cdf.md) | `P(max_k v_kj <= x)` = the product of the rivals' CDFs, valid because `(z_k, eps_k)` are independent ACROSS bidders (they are correlated only across slots within a bidder). |
| [`slot_blurb_slug`](slot_blurb_slug.md) | A deterministic prose-template KEY for a slot, derived from its loading vector: the dominant positive attribute, or `"balanced"` when none dominates, suffixed `"_light"` when the vector's mass is negative. |
| [`slot_name`](slot_name.md) | Display name of slot `j` — `"Lot 1"`..`"Lot n"`, the token the action grammar's `item` field carries (design.md §3.2). |
| [`stage_budgets`](stage_budgets.md) | Per-stage whole-number budgets: `budget_i = round(budget_mult_i * sum of bidder i's top-k_i values)`. |
| [`tercile_bounds`](tercile_bounds.md) | The two public tercile boundaries of `N(0, sigma^2)`: `(-0.4307*sigma, +0.4307*sigma)`. |
| [`tercile_label`](tercile_label.md) | Which of :data:`TERCILE_LABELS` the realization `x` falls in, against the public boundaries of `N(0, sigma^2)`. |
