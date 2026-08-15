# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""The persona-conditioned prior: the generative model, the persona table, fact rendering data, and the
posterior a rational seat actually computes.

**The persona IS the prior** (design.md §2.2). Public facts about a bidder are the sufficient statistics of
everyone else's belief about its valuation curve, and the mapping from facts to distribution is announced, so
a rival holding only public information can compute a genuinely informative posterior — and a computable
Bayesian seat can compute it exactly. One equation governs every value structure and every stage::

    ell_ijt = log(B_jt) + (beta / K) * (a_i . w_j) + z_it + eps_ijt
    v_ijt   = round(exp(ell_ijt)) + round(gamma_i * R_jt)

:func:`realize_values` is the ONLY implementation of that equation in the package; :mod:`.spec` composes it
with the persona table below. Every function here takes plain arrays and scalars — never an ``AuctionSpec`` —
so this module has no dependency on the spec and the two cannot form a cycle.

Three groups of things live here:

1. **The persona table** (:data:`PERSONAS`) and the catalogue draw (:func:`draw_loadings`).
2. **Fact rendering DATA** — the public/private fact KEYS and their computed values (:func:`public_facts`,
   :func:`private_facts`), with tercile boundaries that are themselves public. The prose lives in
   ``docs/templates/``; the scenario lane connects it through :func:`register_fact_renderer`.
3. **The posterior machinery** a rational seat needs: :class:`RivalPosterior`, a quadrature grid over one
   rival's ``(z, eps)`` given its public ``a_i``, supporting conditioning on the public events a stage
   reveals (exits, standing bids, winning).

On reuse of ``negotiation/beliefs.py``: its ``build_type_grid`` enumerates weight-profiles x shape-assignments
x reservation levels over a DISCRETE ``DealSpace`` option grid, and its ``BeliefState`` scores hypotheses by
concession-likelihood over observed OFFERS. Neither transfers — an auction type is a pair of continuous
Gaussian draws and the observable is a price, not a package — so the analogue is rebuilt here as a
Gauss-Hermite product grid. What DOES transfer is the shape of the interface (an enumerated type grid with
weights, conditioned by observation, exposing an induced value distribution), and the damping idea, which
appears here as :meth:`RivalPosterior.condition`'s ``floor`` so a single surprising observation cannot
collapse the posterior.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable

import numpy as np

# --------------------------------------------------------------------------------------------------------- #
# The public attribute space.
# --------------------------------------------------------------------------------------------------------- #

#: The ``K`` public attribute dimensions. Every bidder's ``a_i`` and every slot's ``w_j`` is a vector over
#: these, in this order, and the affinity term of the value equation is their dot product.
ATTR_NAMES: tuple[str, ...] = ("scale", "power_density", "urgency", "latency")

#: Boundary of the middle tercile of a zero-mean normal, in SD units: ``Phi^-1(2/3) = 0.4307``. Public, so a
#: rival knows exactly what a "strong capital position this cycle" fact rules in and out (design.md §2.2).
TERCILE_Z: float = 0.4307272993

#: Tercile labels, low to high. The private-fact block renders one of these for the realized ``z_it``.
TERCILE_LABELS: tuple[str, str, str] = ("weak", "typical", "strong")


def tercile_bounds(sigma: float) -> tuple[float, float]:
    """The two public tercile boundaries of ``N(0, sigma^2)``: ``(-0.4307*sigma, +0.4307*sigma)``. A
    degenerate ``sigma = 0`` (the IPV switch) returns ``(0.0, 0.0)``, so every draw renders ``"typical"``."""
    return (-TERCILE_Z * sigma, TERCILE_Z * sigma)


def tercile_label(x: float, sigma: float) -> str:
    """Which of :data:`TERCILE_LABELS` the realization ``x`` falls in, against the public boundaries of
    ``N(0, sigma^2)``. This is the whole content of the "unusually strong capital position this cycle"
    private fact: the label is private, the boundaries are public."""
    lo, hi = tercile_bounds(sigma)
    if sigma <= 0 or lo <= x <= hi:
        return TERCILE_LABELS[1]
    return TERCILE_LABELS[0] if x < lo else TERCILE_LABELS[2]


# --------------------------------------------------------------------------------------------------------- #
# The persona table.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Persona:
    """One of the five archetypes of design.md §2.2, fixed across the bank and across all stages.

    Every field is PUBLIC and appears on the seat card. ``attrs`` is the attribute signature over
    :data:`ATTR_NAMES` with entries in {-1, 0, +1} — each entry is one public fact. ``budget_mult`` is the
    multiple of the seat's own top-capacity valuation total at which its per-stage budget is set: the multiple
    is public (rendered as a tercile label), the realized whole-number budget is private. ``role`` records
    what the persona is FOR in the design, so the table documents its own experimental purpose."""

    persona_id: str
    display_name: str
    attrs: tuple[int, ...]
    capacity: int
    gamma: float
    synergy_rate: float
    decay: float
    budget_mult: float
    role: str
    public_fact_keys: tuple[str, ...]
    private_fact_keys: tuple[str, ...]


#: Fact keys every seat's private block carries each stage (design.md §2.2: the private block is re-rendered
#: per stage because ``z`` redraws, while the public card is fixed).
COMMON_PRIVATE_FACT_KEYS: tuple[str, ...] = ("capital_position", "budget", "top_slot")

#: The five archetypes. Attribute signatures are exactly design.md §2.2's table; the unnamed dimensions are 0.
PERSONAS: tuple[Persona, ...] = (
    Persona(
        persona_id="hyperscaler", display_name="Meridian Compute",
        attrs=(1, 1, 0, 0), capacity=3, gamma=0.0, synergy_rate=0.15, decay=0.90, budget_mult=1.15,
        role="the large bidder in the demand-reduction prediction [ausubel_cramton2014]",
        public_fact_keys=("sites_operated", "workload", "capex_guidance"),
        private_fact_keys=COMMON_PRIVATE_FACT_KEYS + ("synergy_target",),
    ),
    Persona(
        persona_id="regional_operator", display_name="Northwind Facilities",
        attrs=(-1, 0, 0, 1), capacity=2, gamma=0.0, synergy_rate=0.10, decay=0.95, budget_mult=0.85,
        role="the small bidder; the contrast in the shading gradient",
        public_fact_keys=("sites_operated", "tenant_mix", "footprint"),
        private_fact_keys=COMMON_PRIVATE_FACT_KEYS + ("synergy_target",),
    ),
    Persona(
        persona_id="ai_lab", display_name="Cadence Research",
        attrs=(0, 1, 1, 0), capacity=2, gamma=0.0, synergy_rate=0.20, decay=1.00, budget_mult=0.70,
        role="binding-budget, high-urgency; the Che-Gale subject [che_gale1998]",
        public_fact_keys=("flagship_run", "delivery_deadline", "no_estate"),
        private_fact_keys=COMMON_PRIVATE_FACT_KEYS + ("synergy_target",),
    ),
    Persona(
        persona_id="colocation_reseller", display_name="Tessellate Capacity",
        attrs=(0, 0, 0, 0), capacity=3, gamma=0.45, synergy_rate=0.0, decay=0.85, budget_mult=1.00,
        role="the common-value channel in INTERDEP [athey_levin_seira2011, pp. 214-219]",
        public_fact_keys=("business_model", "resale_weight"),
        private_fact_keys=COMMON_PRIVATE_FACT_KEYS + ("resale_signal",),
    ),
    Persona(
        persona_id="sovereign_fund", display_name="Aster Infrastructure",
        attrs=(1, 0, -1, 0), capacity=3, gamma=0.0, synergy_rate=0.10, decay=0.95, budget_mult=1.40,
        role="the deep-pocketed natural outsider seat; outsider surplus is reported separately [asker2010]",
        public_fact_keys=("mandate", "cost_of_capital", "jurisdiction"),
        private_fact_keys=COMMON_PRIVATE_FACT_KEYS + ("synergy_target",),
    ),
)

PERSONAS_BY_ID: dict[str, Persona] = {p.persona_id: p for p in PERSONAS}


# --------------------------------------------------------------------------------------------------------- #
# The catalogue.
# --------------------------------------------------------------------------------------------------------- #
def draw_loadings(rng: np.random.Generator, n_items: int, K: int) -> np.ndarray:
    """Draw the persistent public loading matrix ``w`` of shape ``(n_items, K)``.

    Loadings are drawn WITHOUT REPLACEMENT from the ``3^K - 1`` non-zero vectors in ``{-1, 0, +1}^K``, so no
    two lots have an identical public profile (two indistinguishable lots would give a market-division
    convention nothing to attach to, and would make the S1 unique-efficient-allocation screen a coin flip) and
    no lot is profile-less. Whole-number loadings keep the catalogue printable and the arithmetic checkable in
    a transcript."""
    pool = [v for v in itertools.product((-1, 0, 1), repeat=K) if any(v)]
    if n_items > len(pool):
        raise ValueError(f"cannot draw {n_items} distinct non-zero loading vectors from {len(pool)} at K={K}")
    idx = rng.choice(len(pool), size=n_items, replace=False)
    return np.array([pool[int(i)] for i in idx], dtype=float)


def slot_name(j: int, n_items: int) -> str:
    """Display name of slot ``j`` — ``"Lot 1"``..``"Lot n"``, the token the action grammar's ``item`` field
    carries (design.md §3.2). Uniform across single- and multi-item stages so one parser serves both."""
    return f"Lot {j + 1}"


def slot_blurb_slug(loading: np.ndarray) -> str:
    """A deterministic prose-template KEY for a slot, derived from its loading vector: the dominant positive
    attribute, or ``"balanced"`` when none dominates, suffixed ``"_light"`` when the vector's mass is
    negative. The prose itself lives in ``docs/templates/`` — a slug keeps the wording out of the payload, so
    a prompt-wording change never edits a stored instance."""
    load = np.asarray(loading, dtype=float)
    if load.max() <= 0:
        base = ATTR_NAMES[int(np.argmax(load))]
        return f"{base}_light"
    top = int(np.argmax(load))
    if float(load[top]) == float(np.sort(load)[-2]) and load.sum() == 0:
        return "balanced"
    return ATTR_NAMES[top]


# --------------------------------------------------------------------------------------------------------- #
# The generative model — design.md §2.2, implemented exactly once.
# --------------------------------------------------------------------------------------------------------- #
def attribute_score(attrs: np.ndarray, loadings: np.ndarray) -> np.ndarray:
    """The public affinity matrix ``(n_bidders, n_items)`` of dot products ``a_i . w_j``.

    This is the entire public signal about the SHAPE of a bidder's valuation curve: everything else in the
    value equation is either a public scalar (``B_jt``, ``beta``) or a private draw."""
    return np.asarray(attrs, dtype=float) @ np.asarray(loadings, dtype=float).T


def realize_values(*, base_values: np.ndarray, loadings: np.ndarray, attrs: np.ndarray, beta: float,
                   z: np.ndarray, eps: np.ndarray, gammas: np.ndarray,
                   resale: np.ndarray | None = None) -> np.ndarray:
    """The value equation of design.md §2.2, evaluated for every ``(bidder, slot)`` pair of one stage.

    ``ell_ij = log(B_j) + (beta / K) * (a_i . w_j) + z_i + eps_ij`` and
    ``v_ij = round(exp(ell_ij)) + round(gamma_i * R_j)``, with the result clipped at 1 so a deep negative draw
    cannot produce a zero- or negative-valued lot (which would make ``bid / value`` undefined).

    Parameters
    ----------
    base_values : np.ndarray
        ``(n_items,)`` public whole-number catalogue base values ``B_jt``.
    loadings : np.ndarray
        ``(n_items, K)`` public loadings ``w_j``.
    attrs : np.ndarray
        ``(n_bidders, K)`` public attribute vectors ``a_i``.
    beta : float
        Public strength of the persona term; ``0`` under IPV, which is what makes public facts uninformative
        about values there.
    z : np.ndarray
        ``(n_bidders,)`` realized private bidder-level shifters (already scaled by ``sigma_z``).
    eps : np.ndarray
        ``(n_bidders, n_items)`` realized private idiosyncrasies (already scaled by ``sigma_eps``).
    gammas : np.ndarray
        ``(n_bidders,)`` public resale weights; all zero outside INTERDEP.
    resale : np.ndarray | None
        ``(n_items,)`` common resale values ``R_jt``, known to nobody. ``None`` outside INTERDEP.

    Returns
    -------
    np.ndarray
        ``(n_bidders, n_items)`` whole-number valuations, dtype ``int64``.
    """
    base_values = np.asarray(base_values, dtype=float)
    K = np.asarray(loadings).shape[1]
    ell = (np.log(base_values)[None, :]
           + (beta / K) * attribute_score(attrs, loadings)
           + np.asarray(z, dtype=float)[:, None]
           + np.asarray(eps, dtype=float))
    values = np.round(np.exp(ell))
    if resale is not None:
        values = values + np.round(np.asarray(gammas, dtype=float)[:, None]
                                   * np.asarray(resale, dtype=float)[None, :])
    return np.clip(values, 1, None).astype(np.int64)


def make_coherent(eps: np.ndarray, affinity: np.ndarray) -> np.ndarray:
    """The RNG-neutral coherence permutation: a persona's own-best slot is never one its public attributes
    point away from (design.md §2.2, the ``scenarios/priors.py::_make_role_coherent`` analogue).

    For each bidder independently: if its largest idiosyncrasy sits on a slot whose affinity ``a_i . w_j`` is
    strictly negative — a slot the persona publicly disfavors — that idiosyncrasy is SWAPPED with the one on
    the bidder's highest-affinity slot. The operation is a permutation within the bidder's own row, so the
    realized value multiset is unchanged and the draw stays RNG-neutral; and it only ever moves the argmax
    TOWARD a favored slot, so it reinforces rather than destroys the persistent affinity structure.

    Design note (a resolved ambiguity): design.md describes this as permuting slot LABELS once per instance.
    Relabelling slots is vacuous here — a slot's identity IS its loading vector, so permuting the labels
    permutes ``w_j`` and ``B_jt`` together and leaves every affinity unchanged. Applying the swap per stage to
    ``eps`` is the operation that actually delivers the stated property, and the design's stated reason for
    "once per instance" (not destroying persistent affinity) is satisfied by construction, since the swap is
    monotone toward affinity."""
    eps = np.array(eps, dtype=float, copy=True)
    affinity = np.asarray(affinity, dtype=float)
    for i in range(eps.shape[0]):
        j_eps = int(np.argmax(eps[i]))
        if affinity[i, j_eps] < 0:
            j_aff = int(np.argmax(affinity[i]))
            if j_aff != j_eps:
                eps[i, j_eps], eps[i, j_aff] = eps[i, j_aff], eps[i, j_eps]
    return eps


def stage_budgets(values: np.ndarray, capacities: np.ndarray, budget_mults: np.ndarray) -> np.ndarray:
    """Per-stage whole-number budgets: ``budget_i = round(budget_mult_i * sum of bidder i's top-k_i values)``.

    Deterministic given the realized values, so the budget carries no information the seat does not already
    have from its own value table, and a ``budget_mult`` below 1 makes the constraint genuinely bind on the
    seat's own preferred bundle (the Che-Gale subject). Budgets are replenished each stage and never carried
    (design.md §2.4)."""
    values = np.asarray(values, dtype=float)
    caps = np.asarray(capacities, dtype=int)
    out = np.empty(values.shape[0], dtype=np.int64)
    for i in range(values.shape[0]):
        top = np.sort(values[i])[::-1][: max(1, int(caps[i]))]
        out[i] = int(round(float(budget_mults[i]) * float(top.sum())))
    return out


# --------------------------------------------------------------------------------------------------------- #
# Fact rendering DATA (the prose lives in docs/templates/).
# --------------------------------------------------------------------------------------------------------- #

#: Registered prose renderers, keyed by fact key. The scenario lane owns the prose and registers it here; this
#: module owns only the KEYS and their computed VALUES, so a wording change never touches a stored spec.
FACT_RENDERERS: dict[str, "Callable[[object], str]"] = {}


def register_fact_renderer(key: str, fn: "Callable[[object], str]", *, overwrite: bool = False) -> None:
    """Register the prose renderer for one fact key. Re-registering without ``overwrite=True`` is an error, so
    two prompt variants cannot silently share a key (the same fail-fast rule as
    ``negotiation/sheets.py::register_constraint``)."""
    if key in FACT_RENDERERS and not overwrite:
        raise ValueError(f"fact renderer {key!r} is already registered")
    FACT_RENDERERS[key] = fn


def render_facts(facts: dict, keys: tuple[str, ...] | None = None) -> list[str]:
    """Render fact values to prose lines through :data:`FACT_RENDERERS`, in ``keys`` order (default: the
    dict's own order). A key with no registered renderer falls back to ``"<key>: <value>"``, so a bare harness
    and the tests work before the scenario lane connects its templates."""
    order = keys if keys is not None else tuple(facts)
    out = []
    for k in order:
        if k not in facts:
            continue
        fn = FACT_RENDERERS.get(k)
        out.append(fn(facts[k]) if fn is not None else f"{k}: {facts[k]}")
    return out


def public_facts(persona: Persona, attrs: tuple[int, ...], *, capacity: int, gamma: float,
                 synergy_rate: float, decay: float, budget_mult: float) -> dict:
    """The public fact VALUES for one seat card: the persona's own keys, every attribute entry as its own
    fact (each entry of ``a_i`` is one public fact, per design.md §2.2), and the public mechanism-relevant
    parameters. Returned as data; :func:`render_facts` turns it into prose."""
    facts: dict = {k: persona.persona_id for k in persona.public_fact_keys}
    facts.update({f"attr_{name}": int(a) for name, a in zip(ATTR_NAMES, attrs)})
    facts.update({"capacity": int(capacity), "gamma": float(gamma), "synergy_rate": float(synergy_rate),
                  "decay": float(decay), "budget_mult": float(budget_mult)})
    return facts


def private_facts(*, z: float, sigma_z: float, budget: int, values: np.ndarray,
                  synergy_target: tuple[int, ...] | None, signals: np.ndarray | None = None,
                  n_items: int) -> dict:
    """The private fact VALUES for one seat at one stage — re-rendered every stage because ``z`` redraws
    while the public card is fixed (design.md §2.2).

    Keys: ``capital_position`` (the tercile LABEL of the realized ``z``, against public boundaries),
    ``budget`` (the realized whole-number budget), ``top_slot`` (the seat's own argmax slot name and value),
    ``synergy_target`` (the private target SET as slot names, or ``None``), and ``resale_signal`` (the noisy
    per-slot resale signals, INTERDEP only)."""
    values = np.asarray(values)
    top = int(np.argmax(values))
    facts = {
        "capital_position": tercile_label(float(z), float(sigma_z)),
        "budget": int(budget),
        "top_slot": (slot_name(top, n_items), int(values[top])),
    }
    if synergy_target is not None:
        facts["synergy_target"] = tuple(slot_name(j, n_items) for j in synergy_target)
    if signals is not None:
        facts["resale_signal"] = tuple(int(s) for s in np.asarray(signals))
    return facts


# --------------------------------------------------------------------------------------------------------- #
# The posterior a rational seat computes.
# --------------------------------------------------------------------------------------------------------- #
def build_type_grid(sigma_z: float, sigma_eps: float, n_z: int = 9, n_eps: int = 9
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The auction analogue of ``negotiation/beliefs.py::build_type_grid``: one rival's type is the pair
    ``(z, eps)`` of continuous Gaussian draws, so the grid is a Gauss-Hermite product rule rather than an
    enumeration of discrete hypotheses.

    Returns ``(z_nodes, z_weights, eps_nodes, eps_weights)``, each 1-D, with weights summing to 1. A
    degenerate ``sigma = 0`` (the IPV switch zeroing ``sigma_z``) collapses to the single node ``0.0`` with
    weight 1, so an IPV posterior is exact rather than approximated. ``n_z``/``n_eps`` of 9 integrate the
    smooth exp-transformed integrand to well under a whole-number rounding step over the design's value
    range, which is the accuracy that matters when bids are integers."""
    def _rule(sigma: float, n: int) -> tuple[np.ndarray, np.ndarray]:
        if sigma <= 0:
            return np.zeros(1), np.ones(1)
        x, w = np.polynomial.hermite_e.hermegauss(n)
        return x * sigma, w / w.sum()
    zn, zw = _rule(float(sigma_z), int(n_z))
    en, ew = _rule(float(sigma_eps), int(n_eps))
    return zn, zw, en, ew


class RivalPosterior:
    """What one seat believes about ONE rival's realized valuations, from public information alone.

    The rival's value for slot ``j`` is ``round(exp(log B_j + (beta/K) a.w_j + z + eps_j)) + round(gamma R_j)``
    with ``z`` and ``eps_j`` the only unknowns; both are public-variance Gaussians, so the posterior is the
    Gauss-Hermite product grid of :func:`build_type_grid` pushed through the value equation. Because ``z`` is
    shared across the rival's slots, values across slots are CORRELATED within a rival while being independent
    across rivals — the affiliation the APV structure is named for [milgrom_weber1982].

    The grid is materialized as a flat list of ``(z, eps_j)`` nodes per slot with a weight vector, which is
    what makes conditioning a reweighting: :meth:`condition` multiplies the weights by an indicator on the
    node's implied value and renormalizes, so "this rival is still active at price p" and "this rival exited
    at p" are the same operation with different bounds.

    Parameters
    ----------
    base_values : np.ndarray
        ``(n_items,)`` public catalogue base values for the stage.
    loadings : np.ndarray
        ``(n_items, K)`` public loadings.
    attrs_row : np.ndarray
        ``(K,)`` the RIVAL's public attribute vector.
    beta, sigma_z, sigma_eps : float
        The public structural constants.
    gamma : float
        The rival's public resale weight; combined with ``resale_mean`` when non-zero.
    resale_mean : np.ndarray | None
        ``(n_items,)`` prior mean of the unobserved common resale value, used only when ``gamma > 0``. The
        resale component is treated as a known constant at its prior mean rather than a third integrated
        dimension: the design's INTERDEP cells sit in the contingent tail, and the winner's-curse conditioning
        that matters there happens on the SEAT'S OWN signal (see
        :func:`~interlens.arena.auction.bidders.winners_curse_value`), not on the rival grid.
    n_z, n_eps : int
        Quadrature node counts.
    """

    def __init__(self, *, base_values, loadings, attrs_row, beta: float, sigma_z: float, sigma_eps: float,
                 gamma: float = 0.0, resale_mean=None, n_z: int = 9, n_eps: int = 9):
        self.base_values = np.asarray(base_values, dtype=float)
        self.n_items = int(self.base_values.shape[0])
        loadings = np.asarray(loadings, dtype=float)
        K = loadings.shape[1]
        affinity = np.asarray(attrs_row, dtype=float) @ loadings.T          # (n_items,)
        self._mu = np.log(self.base_values) + (float(beta) / K) * affinity   # (n_items,)
        self._resale = (np.round(float(gamma) * np.asarray(resale_mean, dtype=float))
                        if (gamma and resale_mean is not None) else np.zeros(self.n_items))
        zn, zw, en, ew = build_type_grid(sigma_z, sigma_eps, n_z, n_eps)
        # Flatten the (z, eps) product into one node axis shared across slots: node k = (z_a, eps_b).
        self._z = np.repeat(zn, len(en))
        self._e = np.tile(en, len(zn))
        self.weights = np.repeat(zw, len(en)) * np.tile(ew, len(zn))
        self.weights = self.weights / self.weights.sum()
        self._values = np.clip(np.round(np.exp(self._mu[:, None] + self._z[None, :] + self._e[None, :])), 1,
                               None).astype(np.int64) + self._resale[:, None].astype(np.int64)  # (n_items, n_nodes)

    # -- readouts ------------------------------------------------------------------------------------------
    def node_values(self, slot: int) -> np.ndarray:
        """The implied whole-number value of ``slot`` at every grid node (aligned with :attr:`weights`)."""
        return self._values[slot]

    def value_pmf(self, slot: int) -> tuple[np.ndarray, np.ndarray]:
        """The marginal distribution of the rival's value for ``slot`` as ``(values, probs)`` with values
        sorted ascending and duplicate nodes merged."""
        v = self._values[slot]
        uniq, inv = np.unique(v, return_inverse=True)
        p = np.zeros(len(uniq))
        np.add.at(p, inv, self.weights)
        return uniq, p

    def expected_value(self, slot: int) -> float:
        """``E[v_j]`` under the current (possibly conditioned) posterior."""
        return float(np.dot(self._values[slot], self.weights))

    def cdf(self, slot: int, x: float) -> float:
        """``P(v_j <= x)`` under the current posterior."""
        return float(self.weights[self._values[slot] <= x].sum())

    def prob_above(self, slot: int, x: float) -> float:
        """``P(v_j > x)`` under the current posterior."""
        return 1.0 - self.cdf(slot, x)

    # -- conditioning --------------------------------------------------------------------------------------
    def condition(self, slot: int, *, lower: float | None = None, upper: float | None = None,
                  floor: float = 1e-9) -> "RivalPosterior":
        """A COPY of this posterior reweighted by ``lower <= v_slot <= upper``.

        Every public event a stage reveals is one of these two bounds under a monotone bidding function: a
        rival that EXITED an English clock at ``p`` has ``v ~ p`` (pass both bounds around ``p``); one still
        ACTIVE at ``p`` has ``v >= p``; one that LOST a sealed second-price auction at price ``p`` has
        ``v <= p``. ``floor`` is a uniform mass mixed back in after renormalizing — the damping idea from
        ``negotiation/beliefs.py::BeliefState``, so one surprising observation (a rival bidding above its own
        value, which this design MEASURES rather than blocks) cannot collapse the posterior to zero mass."""
        v = self._values[slot]
        mask = np.ones_like(v, dtype=float)
        if lower is not None:
            mask *= (v >= lower)
        if upper is not None:
            mask *= (v <= upper)
        w = self.weights * mask
        if w.sum() <= 0:
            w = np.ones_like(self.weights)
        w = w / w.sum()
        w = (1 - floor) * w + floor / len(w)
        out = object.__new__(RivalPosterior)
        out.__dict__.update(self.__dict__)
        out.weights = w / w.sum()
        return out


def rival_max_cdf(posteriors: "list[RivalPosterior]", slot: int, x: float) -> float:
    """``P(max_k v_kj <= x)`` = the product of the rivals' CDFs, valid because ``(z_k, eps_k)`` are
    independent ACROSS bidders (they are correlated only across slots within a bidder). This is the
    distribution every conditional-on-winning calculation and every first-price best response reads."""
    out = 1.0
    for p in posteriors:
        out *= p.cdf(slot, x)
    return float(out)
