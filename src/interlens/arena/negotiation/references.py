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
# [rational_agents scaffold: game-theory] 2026-07-23

"""Citation-key registry for the negotiation solution-concept and generator modules.

Every algorithm in this package cites its primary source by a short key (e.g. ``[nash1950]``) in the relevant
docstring; this module maps each key to the full citation (authors, year, title, venue, volume/pages, DOI) and
a stable URL, so the citations live in exactly one place and the docstrings stay terse. Keys and page/section
references were pulled from ``experiments/rational_agents/docs/lit/rational-oracles.md`` §3 (solution concepts)
and the benchmark deep-dive; each was verified there against the fetched primary PDF.

Usage::

    from interlens.arena.negotiation.references import ref, cite
    ref("nash1950").url                # -> 'https://www.jstor.org/stable/1907266'
    print(cite("nash1950", "ks1975"))  # a two-line block for a module/function header
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reference:
    """One bibliographic entry.

    ``key`` is the short citation key used in docstrings; ``citation`` the full human-readable reference
    (authors, year, title, venue, volume(issue):pages, DOI where available); ``url`` a stable link (publisher
    landing page, JSTOR, arXiv, or open PDF). ``note`` optionally records what specifically this reference
    grounds (e.g. the exact theorem/algorithm/page a module relies on)."""

    key: str
    citation: str
    url: str
    note: str = ""

    def __str__(self) -> str:
        tail = f" — {self.note}" if self.note else ""
        return f"{self.citation} {self.url}{tail}"


# The registry. Ordered roughly by role: solution concepts first, then the additive-utility / game-structure
# and score-sheet-critique sources the generator and descriptors rely on.
REFERENCES: dict[str, Reference] = {
    "nash1950": Reference(
        "nash1950",
        "Nash, J. (1950). The Bargaining Problem. Econometrica 18(2):155-162.",
        "https://www.jstor.org/stable/1907266",
        "Solution statement p.159 (max of the product u1*u2 in the first quadrant); assumptions 6-8 p.159 "
        "(Pareto, IIA, Symmetry); scale invariance built into the framework pp.157-158; worked discrete "
        "Bill-and-Jack barter example pp.160-161.",
    ),
    "mariotti1998": Reference(
        "mariotti1998",
        "Mariotti, M. (1998). Extending Nash's Axioms to Nonconvex Problems. Games and Economic Behavior "
        "22(2):377-383.",
        "https://www.sciencedirect.com/science/article/abs/pii/S089982569790590X",
        "Axiomatizes the Nash-product-maximizer correspondence on general (incl. finite/non-convex) domains — "
        "the cover for computing argmax prod(x_i) directly on a discrete deal space.",
    ),
    "harsanyi1963": Reference(
        "harsanyi1963",
        "Harsanyi, J. C. (1963). A Simplified Bargaining Model for the n-Person Cooperative Game. "
        "International Economic Review 4(2):194-220.",
        "https://www.jstor.org/stable/2525487",
        "The symmetric n-player Nash product max prod_i x_i.",
    ),
    "ks1975": Reference(
        "ks1975",
        "Kalai, E. & Smorodinsky, M. (1975). Other Solutions to Nash's Bargaining Problem. Econometrica "
        "43(3):513-518.",
        "https://www.jstor.org/stable/1914280",
        "Swaps IIA for individual monotonicity; solution = maximal feasible point on the segment from the "
        "disagreement point to the ideal point b; original is 2-player. Scale-invariant (a_i cancels in "
        "x_i/b_i).",
    ),
    "roth1979": Reference(
        "roth1979",
        "Roth, A. E. (1979). An Impossibility Result Concerning n-Person Bargaining Games. International "
        "Journal of Game Theory 8:129-132.",
        "https://link.springer.com/article/10.1007/BF01770063",
        "For n>2 the KS solution may fail Pareto optimality and no Pareto-optimal solution keeps its other "
        "axioms; operational fix = Pareto-restricted max-min-of-normalized-surplus with leximin ties.",
    ),
    "kalai1977": Reference(
        "kalai1977",
        "Kalai, E. (1977). Proportional Solutions to Bargaining Situations: Interpersonal Utility "
        "Comparisons. Econometrica 45(7):1623-1630.",
        "https://www.jstor.org/stable/1913954",
        "Egalitarian/proportional solution; presupposes interpersonal utility comparability (NOT scale "
        "invariant). On normalized surpluses x_i/b_i it collapses into KS.",
    ),
    "harsanyi1955": Reference(
        "harsanyi1955",
        "Harsanyi, J. C. (1955). Cardinal Welfare, Individualistic Ethics, and Interpersonal Comparisons of "
        "Utility. Journal of Political Economy 63(4):309-321.",
        "https://www.davidmccarthy.org/wp-content/uploads/2018/09/harsanyi1955.pdf",
        "Utilitarian (sum-of-utilities) welfare; NOT scale invariant — only meaningful on a shared/normalized "
        "scale.",
    ),
    "caragiannis2019": Reference(
        "caragiannis2019",
        "Caragiannis, I., Kurokawa, D., Moulin, H., Procaccia, A. D., Shah, N. & Wang, J. (2019). The "
        "Unreasonable Fairness of Maximum Nash Welfare. ACM Transactions on Economics and Computation "
        "7(3), Article 12. DOI:10.1145/3355902.",
        "https://www.cs.toronto.edu/~nisarg/papers/mnw.pdf",
        "Zero-product handling (Def. 3.1 + Algorithm 1, pp.12:7-12:8): find a largest set S of agents that can "
        "be simultaneously positive, then maximize prod_{i in S} — the two-stage fallback for an empty "
        "strict-IR set. Scale-freeness p.12:2.",
    ),
    "kung1975": Reference(
        "kung1975",
        "Kung, H. T., Luccio, F. & Preparata, F. P. (1975). On Finding the Maxima of a Set of Vectors. "
        "Journal of the ACM 22(4):469-476. DOI:10.1145/321906.321910.",
        "https://dl.acm.org/doi/10.1145/321906.321910",
        "Classical maxima-of-a-vector-set (Pareto frontier) reference; brute force O(|D|^2 * n) is milliseconds "
        "at |D|<=3125.",
    ),
    "conley_wilkie1991": Reference(
        "conley_wilkie1991",
        "Conley, J. P. & Wilkie, S. (1991). The bargaining problem without convexity: Extending the egalitarian "
        "and Kalai-Smorodinsky solutions. Economics Letters 36(4):365-369.",
        "https://www.sciencedirect.com/science/article/abs/pii/0165176591901037",
        "Non-convex axiomatic cover for KS/egalitarian on finite (non-convex) feasible sets.",
    ),
    "keeney_raiffa1976": Reference(
        "keeney_raiffa1976",
        "Keeney, R. L. & Raiffa, H. (1976). Decisions with Multiple Objectives: Preferences and Value "
        "Tradeoffs. Wiley.",
        "https://www.cambridge.org/core/books/decisions-with-multiple-objectives/A9AAA6DB8A2C4E5E9C8C7E3F9F6E9A6E",
        "Additive multi-attribute value model u_i(d) = sum_j s_ij(d_j) under mutual preferential + utility "
        "independence — the score-sheet form.",
    ),
    "abdelnabi2024": Reference(
        "abdelnabi2024",
        "Abdelnabi, S., Gomaa, A., Sivaprasad, S., Schoenherr, L. & Fritz, M. (2024). Cooperation, "
        "Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation. NeurIPS 2024 D&B. "
        "arXiv:2309.17234.",
        "https://arxiv.org/abs/2309.17234",
        "The scorable-game template: 6 parties x 5 issues, 3-5 options, private additive sheets, per-party "
        "minimum threshold (BATNA), 'wrong deals' = own proposals below own threshold.",
    ),
    "reproA2025": Reference(
        "reproA2025",
        "Garcia, R., Hajkova, T., Marchenko, D. & Patino, D. (2025). Reproducibility Study of "
        "LLM-Stakeholders Interactive Negotiation. arXiv:2502.16242.",
        "https://arxiv.org/abs/2502.16242",
        "The Pareto-slack critique: 80.5% of acceptable base-game deals were ON the Pareto front, so the game "
        "goes near-zero-sum once feasible. Motivates the dominated-acceptable-fraction generator knob and the "
        "communication-free baseline control.",
    ),
    "sandholm_vulkan1999": Reference(
        "sandholm_vulkan1999",
        "Sandholm, T. & Vulkan, N. (1999). Bargaining with Deadlines. AAAI-99, pp. 44-51.",
        "https://cdn.aaai.org/AAAI/1999/AAAI99-007.pdf",
        "With a firm common deadline and NO discounting, the unique sequential-equilibrium outcome is "
        "brinkmanship (both wait to the deadline). So a per-round discount delta < 1 (or breakdown risk) is what "
        "makes interior concession the rational path -- the reason generated instances default to delta < 1.",
    ),
    "reproB_tmlr": Reference(
        "reproB_tmlr",
        "Carrasco Pollo, C., Kapetangeorgis, S., Rosenthal, J. & Yao, R. (2026). [Re] Benchmarking LLM "
        "Capabilities in Negotiation through Scoreable Games. TMLR (MLRC 2025 Journal Track). "
        "arXiv:2602.18230.",
        "https://openreview.net/forum?id=BVH81SAAh2",
        "Score-sheet descriptors: sparsity = % zero-valued options (23.7-43.0%), pairwise IoU of score "
        "functions (18.8-29.8%); welfare metrics USW/ESW/NSW.",
    ),
}


def ref(key: str) -> Reference:
    """Look up one reference by key; raises ``KeyError`` with the available keys if the key is unknown."""
    try:
        return REFERENCES[key]
    except KeyError:
        raise KeyError(f"unknown citation key {key!r}; known keys: {sorted(REFERENCES)}") from None


def cite(*keys: str) -> str:
    """Render the given keys as an indented multi-line block, one ``[key] full-citation url`` per line, for
    pasting into a module or function header."""
    return "\n".join(f"  [{k}] {ref(k)}" for k in keys)
