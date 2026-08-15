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
# [rational_agents: viz-hovers] 2026-08-03

"""What each solution concept IS, in one place, for every part of the visualizer that explains one to a reader.

A leaf module on purpose: the browser layer (``assets/js_hover``, which serializes :data:`CONCEPT_MATH` straight
into the page's script) and anything rendering an explanation server-side both read THIS, so the axioms cannot
drift into two versions that disagree. ``geometry`` re-exports :data:`CONCEPT_LABELS`, which is also the legend
order the chart marks them in.

The formulae are HTML — ``<sub>`` plus Unicode operators (``Σ Π τ − >``) and named entities — rather than LaTeX,
because every page is opened off ``file://`` with no network: a maths library would either be a CDN request that
leaves the explanation blank or a large vendored blob to typeset five one-line objectives. Notation throughout:
``u_i`` is party ``i``'s utility for a deal, ``tau_i`` its walk-away threshold, ``b_i`` its ideal, and
``z_i = max(u_i - tau_i, 0) / (b_i - tau_i)`` the normalized surplus both chart axes are built from.
"""
from __future__ import annotations

#: The concepts marked on the frontier chart, in legend order, with the short label each mark carries. Direct-
#: labelled rather than colour-coded: they are singletons on a scatter, where the colour formula caps categorical
#: identity at three slots (see ``assets``).
CONCEPT_LABELS = {
    "nash": "NBS",
    "kalai_smorodinsky": "KS",
    "utilitarian": "UTIL",
    "egalitarian": "EGAL",
    "normalized_egalitarian": "nEGAL",
    "max_nash_welfare": "MNW",
}

#: ``{concept: {name, math, note}}`` — the full name, the objective it maximizes as HTML, and the one property
#: that separates it from its neighbours. A reader who cannot tell KS from EGAL on sight cannot read the chart,
#: so ``note`` always states the distinguishing property, not just a restatement of the formula.
CONCEPT_MATH = {
    "nash": {
        "name": "Nash bargaining solution",
        "math": "argmax<sub>d</sub> &Sigma;<sub>i</sub> log(u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>)",
        "note": "maximizes the <b>product</b> of every party's gain over its walk-away point &mdash; the unique split satisfying Nash's four axioms (efficiency, symmetry, invariance to affine rescaling, independence of irrelevant alternatives). Scale-invariant, so it does not care whose score sheet is written in bigger numbers.",
    },
    "kalai_smorodinsky": {
        "name": "Kalai&ndash;Smorodinsky solution",
        "math": "argmax<sub>d</sub> min<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>) / (b<sub>i</sub> &minus; &tau;<sub>i</sub>)",
        "note": "equalizes each party's <b>fraction of its own ideal gain</b>, and so lifts the worst-treated fraction as high as it will go. Trades Nash's independence axiom for <b>monotonicity</b>: enlarging what is on the table can never leave a party worse off. Also scale-invariant.",
    },
    "utilitarian": {
        "name": "utilitarian point",
        "math": "argmax<sub>d</sub> &Sigma;<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>)",
        "note": "maximizes <b>total</b> surplus, with no regard for how it is divided. <b class='neg'>NOT scale-invariant</b>: it adds up privately-scaled score sheets, so a party that happens to write larger numbers is handed the deal. Read it as a reference point, never as a fairness target.",
    },
    "egalitarian": {
        "name": "egalitarian point",
        "math": "argmax<sub>d</sub> min<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>)",
        "note": "maximizes the <b>worst-off</b> party's surplus &mdash; Rawlsian maximin. It is blind to everything above that minimum, so two deals with the same worst-off party tie however differently they treat everyone else.",
    },
    "normalized_egalitarian": {
        "name": "normalized egalitarian point",
        "math": "argmax<sub>d</sub> min<sub>i</sub> z<sub>i</sub>(d),&nbsp; z<sub>i</sub> = max(u<sub>i</sub> &minus; &tau;<sub>i</sub>, 0) / (b<sub>i</sub> &minus; &tau;<sub>i</sub>)",
        "note": "maximizes the <b>worst party's fraction of its own ideal gain</b>. It is the scale-invariant version of raw EGAL and is shown only when it chooses a different deal.",
    },
    "max_nash_welfare": {
        "name": "maximum Nash welfare",
        "math": "argmax<sub>d</sub> &Pi;<sub>i</sub> (u<sub>i</sub>(d) &minus; &tau;<sub>i</sub>),&nbsp; u<sub>i</sub>(d) &gt; &tau;<sub>i</sub> &forall;i",
        "note": "the Nash product over the <b>strictly</b> individually-rational deals. When no deal clears every threshold it falls back to the <b>Caragiannis</b> rule &mdash; first maximize how many parties are above threshold, then the Nash product among exactly those &mdash; so the point exists even where the strict problem is empty.",
    },
}

#: The point kinds that are not solution concepts. ``what`` a given mark is gets phrased per-point (it names seats
#: and turns); these are the standing explanations of what that KIND of mark means.
ROLE_NOTES = {
    "party_best": "the <b>frontier deal this party would dictate</b> if it could choose alone: argmax<sub>d</sub> u<sub>i</sub>(d) over the deals that are both efficient and able to close. The gap between it and the deal that closed is what this party gave up by having to agree with anyone.",
    "oracle": "what the <b>best-response oracle</b> would have put on the table at this turn. Standard saved annotations use the full game table; in a private-information episode this is an omniscient hindsight result, not a move the seat could have derived from what it knew. The chart's regret strip is the value of this deal minus the oracle's value of what the seat actually did.",
    "proposal": "a deal the negotiation actually put <b>on the table</b>. The numbered path traces the order of play, so the walk from the first move to the last is the concession pattern.",
    "agreed": "the deal the parties <b>closed on</b>. Everything the episode is scored against &mdash; capture, distance to the Nash solution, whether anyone was left below threshold &mdash; is read off this point.",
    "standing": "the deal <b>standing on the table</b> at the turn in view: the most recent live offer, which is what the next seat is answering.",
}

#: The caveat both axis explanations end on. The chart is an honest *projection*, and the one way to misread it is
#: to treat plotted proximity as the real distance in the full ``n``-dimensional surplus space.
PROJECTION_CAVEAT = ("Both axes are summaries: the chart is a <b>2-D projection</b> of the full "
                     "<var>n</var>-dimensional <var>z</var>-space, so two different deals can land on the same "
                     "point and on-screen closeness is a guide, not a measurement. The exact distances (including "
                     "distance to the Nash solution) are in the numeric table under the chart.")

#: ``{axis: {title, html}}`` — what each axis of the embedding measures, for the info control beside its title.
#: ``c_i = b_i - tau_i`` is party ``i``'s own surplus capacity, so ``z_i`` is a fraction of what that party could
#: possibly have got, which is what makes both axes comparable across privately-scaled score sheets.
AXIS_NOTES = {
    "x": {
        "title": "joint welfare — mean normalized surplus",
        "html": ("<span class='hmath'>z<sub>i</sub> = (u<sub>i</sub> &minus; &tau;<sub>i</sub>) / c<sub>i</sub>"
                 "&nbsp;&nbsp;&nbsp;x = mean<sub>i</sub> z<sub>i</sub></span>"
                 "Each party's gain over its <b>walk-away point</b> &tau;<sub>i</sub>, as a fraction of the most "
                 "it could possibly have gained (c<sub>i</sub> = b<sub>i</sub> &minus; &tau;<sub>i</sub>); the "
                 "axis is the mean of those over every party at the table. Read it as <b>how much total value "
                 "the deal created</b> — the utilitarian direction. Because every party's gain is divided by its "
                 "own capacity, the axis is <b>scale-invariant</b>: no party can move a deal rightwards by "
                 "inflating the numbers on its private score sheet."),
    },
    "y": {
        "title": "worst-off party — min normalized surplus",
        "html": ("<span class='hmath'>y = min<sub>i</sub> z<sub>i</sub></span>"
                 "How the party doing <b>worst</b> out of this deal fares, in the same normalized units — the "
                 "egalitarian direction, and exactly the quantity discrete Kalai&ndash;Smorodinsky maximizes. "
                 "<b>Zero means someone gained nothing over walking away</b>, and a deal that leaves a party "
                 "below its threshold is an individual-rationality violation if it is accepted. Up and to the "
                 "right is therefore better for everybody, which is why the frontier's image is the upper-right "
                 "envelope of the cloud."),
    },
}

__all__ = ["AXIS_NOTES", "CONCEPT_LABELS", "CONCEPT_MATH", "PROJECTION_CAVEAT", "ROLE_NOTES"]
