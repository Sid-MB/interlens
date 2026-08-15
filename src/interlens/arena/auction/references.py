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

"""Citation-key registry for the auction mechanism, benchmark, and collusion-metric modules.

The sibling of ``negotiation/references.py`` and the same shape: every algorithm and every preregistered
benchmark in this package cites its primary source by a short key (e.g. ``[vickrey1961]``) in the relevant
docstring, and this module maps each key to the full citation plus the **exact page range** the module relies
on. ``design.md`` §12 item 1 names the required entries; ``prompt.md`` requires the page numbers.

Usage — the registry is bibliography DATA (no accessor API); read it directly::

    from interlens.arena.auction.references import REFERENCES
    REFERENCES["vickrey1961"].url          # -> 'https://www.jstor.org/stable/2977633'
    str(REFERENCES["robinson1985"])        # "<citation> <url> — <note>" for a header line
"""
from __future__ import annotations

from ..negotiation.references import Reference

__all__ = ["Reference", "REFERENCES"]


#: The registry. Ordered by role: single-object theory, multi-unit/multi-item theory, collusion theory and
#: detection, experimental anchors, algorithmic/LLM collusion, and the algorithmic utilities this package
#: implements directly.
REFERENCES: dict[str, Reference] = {
    # -- single-object mechanism theory -----------------------------------------------------------------
    "vickrey1961": Reference(
        "vickrey1961",
        "Vickrey, W. (1961). Counterspeculation, Auctions, and Competitive Sealed Tenders. "
        "The Journal of Finance 16(1):8-37.",
        "https://www.jstor.org/stable/2977633",
        "pp. 20-23: bidding one's own value is weakly dominant in the second-price sealed auction, and the "
        "Dutch descending auction is strategically equivalent to the first-price sealed auction. Grounds "
        "`TruthfulPolicy`, the second-price benchmark in `benchmarks.py`, and the design's G3 check.",
    ),
    "riley_samuelson1981": Reference(
        "riley_samuelson1981",
        "Riley, J. G. & Samuelson, W. F. (1981). Optimal Auctions. "
        "The American Economic Review 71(3):381-392.",
        "https://www.jstor.org/stable/1802786",
        "pp. 383-385: the symmetric risk-neutral first-price equilibrium "
        "b(v) = v - integral_0^v F(x)^(n-1) dx / F(v)^(n-1), which reduces to (n-1)/n * v for the uniform "
        "case (0.8v at n = 5). Grounds `rnne_symmetric_bid` and the Dutch/first-price benchmark.",
    ),
    "myerson1981": Reference(
        "myerson1981",
        "Myerson, R. B. (1981). Optimal Auction Design. Mathematics of Operations Research 6(1):58-73.",
        "https://doi.org/10.1287/moor.6.1.58",
        "pp. 61-66: the revenue-equivalence theorem and the virtual-valuation characterization of the "
        "revenue-optimal reserve. Grounds the claim that the format contrasts in this design move behavior "
        "rather than theoretical revenue under risk neutrality and symmetry.",
    ),
    "milgrom_weber1982": Reference(
        "milgrom_weber1982",
        "Milgrom, P. R. & Weber, R. J. (1982). A Theory of Auctions and Competitive Bidding. "
        "Econometrica 50(5):1089-1122.",
        "https://doi.org/10.2307/1911865",
        "pp. 1094-1104: affiliation, the general symmetric model, and the linkage principle - with affiliated "
        "values the English auction reveals rivals' exits and so raises expected revenue above the "
        "second-price sealed auction. Grounds the APV value structure and the disclose_public_facts switch.",
    ),
    "che_gale1998": Reference(
        "che_gale1998",
        "Che, Y.-K. & Gale, I. (1998). Standard Auctions with Financially Constrained Bidders. "
        "The Review of Economic Studies 65(1):1-21.",
        "https://doi.org/10.1111/1467-937X.00035",
        "pp. 3-12: with binding budget constraints the first-price auction revenue-dominates the "
        "second-price auction, reversing the unconstrained ranking. Grounds the budget-violation metric and "
        "the contingent-tail budget-reversal cell.",
    ),
    # -- multi-unit and multi-item ----------------------------------------------------------------------
    "ausubel2004": Reference(
        "ausubel2004",
        "Ausubel, L. M. (2004). An Efficient Ascending-Bid Auction for Multiple Objects. "
        "The American Economic Review 94(5):1452-1475.",
        "https://doi.org/10.1257/0002828043052330",
        "pp. 1454-1460: the clinching rule - a bidder clinches a unit once residual rival demand falls below "
        "supply, and pays the clock price at which it clinched, which reproduces the Vickrey outcome and "
        "removes the demand-reduction incentive. Grounds `clinching_prices`.",
    ),
    "ausubel_cramton2014": Reference(
        "ausubel_cramton2014",
        "Ausubel, L. M., Cramton, P., Pycia, M., Rostek, M. & Weretka, M. (2014). Demand Reduction and "
        "Inefficiency in Multi-Unit Auctions. The Review of Economic Studies 81(4):1366-1400.",
        "https://doi.org/10.1093/restud/rdu023",
        "pp. 1370-1378: under uniform pricing a multi-unit bidder shades its inframarginal units because "
        "they raise the price it pays on the units it wins, so equilibrium demand schedules are strictly "
        "below true marginal values. Grounds the demand-reduction gradient metric and the "
        "demand-reduction-free uniform-price benchmark.",
    ),
    # -- collusion theory and detection -----------------------------------------------------------------
    "robinson1985": Reference(
        "robinson1985",
        "Robinson, M. S. (1985). Collusion and the Choice of Auction. "
        "The RAND Journal of Economics 16(1):141-145.",
        "https://www.jstor.org/stable/2555596",
        "pp. 142-144: a cartel agreement is self-enforcing under the second-price/English format (a defector "
        "gains nothing by shading above the agreed bid) and self-destructs under the sealed high-bid format "
        "(shading a hair above captures the whole item, undetected until settlement). Grounds the Q2 "
        "format-dependent defection hazard.",
    ),
    "graham_marshall1987": Reference(
        "graham_marshall1987",
        "Graham, D. A. & Marshall, R. C. (1987). Collusive Bidder Behavior at Single-Object Second-Price "
        "and English Auctions. Journal of Political Economy 95(6):1217-1239.",
        "https://doi.org/10.1086/261512",
        "pp. 1219-1226: the pre-auction knockout - a private ring meeting nested inside a public auction, "
        "with an ex-ante budget-balanced transfer scheme that makes truthful reporting inside the ring "
        "incentive compatible. Grounds keeping broadcast alongside DM (the nested channel ladder).",
    ),
    "mcafee_mcmillan1992": Reference(
        "mcafee_mcmillan1992",
        "McAfee, R. P. & McMillan, J. (1992). Bidding Rings. "
        "The American Economic Review 82(3):579-599.",
        "https://www.jstor.org/stable/2117323",
        "pp. 582-589: the strong-cartel / weak-cartel distinction - a cartel that can make side payments "
        "achieves the efficient within-ring allocation, while one that cannot is restricted to bid rotation. "
        "Grounds the `dm_transfers` channel rung, where the harness executes declared transfers.",
    ),
    "porter_zona1993": Reference(
        "porter_zona1993",
        "Porter, R. H. & Zona, J. D. (1993). Detection of Bid Rigging in Procurement Auctions. "
        "Journal of Political Economy 101(3):518-538.",
        "https://doi.org/10.1086/261885",
        "pp. 526-533: the losing-bid rationality test - regress non-winning bids on cost/observable "
        "covariates and test whether ring members' losing bids stop tracking their own costs while "
        "competitors' bids continue to. Grounds `porter_zona_rows`; the test is outcome-based, so a private "
        "channel does not weaken it.",
    ),
    "cramton_schwartz2000": Reference(
        "cramton_schwartz2000",
        "Cramton, P. & Schwartz, J. A. (2000). Collusive Bidding: Lessons from the FCC Spectrum Auctions. "
        "Journal of Regulatory Economics 17(3):229-252.",
        "https://doi.org/10.1023/A:1008122015102",
        "pp. 236-244: code bidding (encoding a target market number in a bid's trailing digits) and "
        "retaliatory bidding in the FCC PCS auctions. Grounds the Q6 trailing-digit test and the "
        "bid-rounding closed-channel control.",
    ),
    "klemperer2002": Reference(
        "klemperer2002",
        "Klemperer, P. (2002). What Really Matters in Auction Design. "
        "Journal of Economic Perspectives 16(1):169-189.",
        "https://doi.org/10.1257/0895330027166",
        "pp. 171-177: collusion and entry deterrence, not the revenue ranking of formats, are what determine "
        "real auction performance; ascending formats are the most collusion-friendly. The design-level "
        "justification for making collusion rather than revenue the headline outcome.",
    ),
    "asker2010": Reference(
        "asker2010",
        "Asker, J. (2010). A Study of the Internal Organization of a Bidding Cartel. "
        "The American Economic Review 100(3):724-762.",
        "https://doi.org/10.1257/aer.100.3.724",
        "pp. 731-740: a ring changes the environment for non-members too, so outsider surplus must be "
        "reported separately from ring-member surplus. Grounds the per-seat surplus reporting rule.",
    ),
    # -- experimental anchors ---------------------------------------------------------------------------
    "kagel_levin1986": Reference(
        "kagel_levin1986",
        "Kagel, J. H. & Levin, D. (1986). The Winner's Curse and Public Information in Common Value "
        "Auctions. The American Economic Review 76(5):894-920.",
        "https://www.jstor.org/stable/1816459",
        "pp. 908-915: releasing public information RAISES revenue when bidders are sophisticated and LOWERS "
        "it when they are subject to the winner's curse - a sign test that separates the two using revenue "
        "alone. Grounds the INTERDEP value structure and the Kagel-Levin sign-test cell.",
    ),
    "kagel1995": Reference(
        "kagel1995",
        "Kagel, J. H. (1995). Auctions: A Survey of Experimental Research. In Kagel, J. H. & Roth, A. E. "
        "(eds.), The Handbook of Experimental Economics, pp. 501-585. Princeton University Press.",
        "https://press.princeton.edu/books/hardcover/9780691042909/the-handbook-of-experimental-economics",
        "pp. 501-585, esp. 517-538: persistent overbidding above the dominant strategy in sealed "
        "second-price auctions that does not extinguish with experience, clean convergence in the "
        "strategically equivalent English clock, and Dutch prices below first-price. The human column of the "
        "design's three-column reporting rule.",
    ),
    "athey_levin_seira2011": Reference(
        "athey_levin_seira2011",
        "Athey, S., Levin, J. & Seira, E. (2011). Comparing Open and Sealed Bid Auctions: Evidence from "
        "Timber Auctions. The Quarterly Journal of Economics 126(1):207-257.",
        "https://doi.org/10.1093/qje/qjq001",
        "pp. 214-219: the processor/reseller asymmetry that motivates a narrative common-value channel "
        "(a dealer whose value is the resale price) rather than an abstract signal-structure prompt; "
        "pp. 230-240: entry and participation effects, which this design fixes at five seats rather than "
        "studies. Grounds the persona table and the `colocation_reseller` resale channel.",
    ),
    # -- algorithmic and LLM collusion ------------------------------------------------------------------
    "calvano2020": Reference(
        "calvano2020",
        "Calvano, E., Calzolari, G., Denicolo, V. & Pastorello, S. (2020). Artificial Intelligence, "
        "Algorithmic Pricing, and Collusion. The American Economic Review 110(10):3267-3297.",
        "https://doi.org/10.1257/aer.20190623",
        "pp. 3277-3288: Q-learning pricing agents reach supracompetitive prices with no communication, and "
        "the outcome is sustained by a genuine reward-punishment structure - a finite punishment phase "
        "followed by gradual return to cooperation. Grounds the onset, hazard, and punishment "
        "impulse-response metrics, and the rule that the silent arm is not a zero baseline.",
    ),
    "banchio_skrzypacz2022": Reference(
        "banchio_skrzypacz2022",
        "Banchio, M. & Skrzypacz, A. (2022). Artificial Intelligence and Auction Design. "
        "arXiv:2202.05947.",
        "https://arxiv.org/abs/2202.05947",
        "The pre-LLM format-dependence result: Q-learning bidders tacitly collude in first-price auctions "
        "without bid feedback but not in second-price auctions. The algorithmic reference point for Q2.",
    ),
    "fish2024": Reference(
        "fish2024",
        "Fish, S., Gonczarowski, Y. A. & Shorrer, R. I. (2024). Algorithmic Collusion by Large Language "
        "Models. arXiv:2404.00806.",
        "https://arxiv.org/abs/2404.00806",
        "LLM pricing agents reach supracompetitive prices without communication, with the abstract stating "
        "the result extends to auctions. The reason the silent cells R1/R5 are full cells rather than token "
        "baselines.",
    ),
    "lin2024": Reference(
        "lin2024",
        "Lin, K. et al. (2024). Strategic Collusion of LLM Agents: Market Division in Multi-Commodity "
        "Competitions. arXiv:2410.00031.",
        "https://arxiv.org/abs/2410.00031",
        "The multi-item collusion signature: agents divide the market by commodity rather than converging on "
        "a single supracompetitive price. Grounds the market-division detector in the SAA cells.",
    ),
    "zolkowski2025": Reference(
        "zolkowski2025",
        "Zolkowski, A. et al. (2025). Early Signs of Steganographic Capabilities in Frontier LLMs. "
        "arXiv:2507.02737.",
        "https://arxiv.org/abs/2507.02737",
        "Covert-communication capability is an AFFORDANCE ladder: frontier models cannot pass encoded "
        "messages under standard conditions but succeed given an unmonitored scratchpad or a prior "
        "coordination opportunity. The DM channel is both from the rivals' point of view; grounds Q4.",
    ),
    "lo2023": Reference(
        "lo2023",
        "Lo, K.-C. et al. (2023). Emergent Communication and Mutual-Information Measurement in Multi-Agent "
        "Systems. arXiv:2303.10733.",
        "https://arxiv.org/abs/2303.10733",
        "Mutual information between a sender's private state and its emitted message features, with a "
        "permutation null, as the operational test for an emergent channel. Grounds "
        "`dyad_mutual_information` and its within-instance permutation null.",
    ),
    "hua2024": Reference(
        "hua2024",
        "Hua, W. et al. (2024). Game-theoretic LLM: Agent Workflow for Negotiation Games. "
        "arXiv:2411.05990.",
        "https://arxiv.org/abs/2411.05990",
        "LLM agents over-trust opponents' stated claims, and an explicit Bayesian workflow repairs the "
        "failure. The prior behind Q5's expectation that a computable Bayes seat resists manipulation.",
    ),
    "park2023": Reference(
        "park2023",
        "Park, P. S., Goldstein, S., O'Gara, A., Chen, M. & Hendrycks, D. (2024). AI deception: A survey of "
        "examples, risks, and potential solutions. Patterns 5(5):100988. arXiv:2308.14752.",
        "https://arxiv.org/abs/2308.14752",
        "The deception taxonomy the tertiary transcript/DM classifier draws its label set from (false "
        "valuation claims, feigned constraints, strategic misdirection).",
    ),
    "chen2023_aucarena": Reference(
        "chen2023_aucarena",
        "Chen, J. et al. (2023). Put Your Money Where Your Mouth Is: Evaluating Strategic Planning and "
        "Execution of LLM Agents in an Auction Arena. arXiv:2310.05746.",
        "https://arxiv.org/abs/2310.05746",
        "`bid_sanity_check()` enforcing budget/floor/min-increment and `rebid_for_failure()` re-prompting "
        "with the specific violation - the source of the one-retry-with-specific-feedback rule reused here.",
    ),
    "feng2025": Reference(
        "feng2025",
        "Feng, S., Choudhary, V. & Shrestha, A. (2025). Do Personas Change LLM Agent Behavior? "
        "arXiv:2508.15926.",
        "https://arxiv.org/abs/2508.15926",
        "Persona text does not reliably produce the intended behavioral heterogeneity, which is why G2(b) "
        "carries a withdrawal clause rather than being assumed.",
    ),
    # -- algorithms this package implements directly ----------------------------------------------------
    "kuhn1955": Reference(
        "kuhn1955",
        "Kuhn, H. W. (1955). The Hungarian Method for the Assignment Problem. "
        "Naval Research Logistics Quarterly 2(1-2):83-97.",
        "https://doi.org/10.1002/nav.3800020109",
        "The O(n^3) primal-dual assignment algorithm behind `_max_weight_assignment`, which is how the "
        "efficient allocation is solved exactly under capacities and diminishing returns (each bidder is "
        "expanded into one slot per unit of capacity, ranked slots carrying the decay multiplier).",
    ),
    "clarke1971_groves1973": Reference(
        "clarke1971_groves1973",
        "Clarke, E. H. (1971). Multipart Pricing of Public Goods. Public Choice 11:17-33; "
        "Groves, T. (1973). Incentives in Teams. Econometrica 41(4):617-631.",
        "https://doi.org/10.1007/BF01726210",
        "The pivot mechanism: each winner pays the externality it imposes, i.e. the welfare the others would "
        "have obtained in its absence minus the welfare they obtain in its presence. Grounds `vcg_payments`.",
    ),
    "milgrom2000": Reference(
        "milgrom2000",
        "Milgrom, P. (2000). Putting Auction Theory to Work: The Simultaneous Ascending Auction. "
        "Journal of Political Economy 108(2):245-272.",
        "https://doi.org/10.1086/262118",
        "pp. 250-258: straightforward bidding (bid on the package maximizing surplus at current standing "
        "prices) and its competitive-equilibrium outcome under substitutes. Grounds the SAA competitive "
        "benchmark simulated in `saa_competitive_benchmark`.",
    ),
}
