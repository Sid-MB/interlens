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
# [rational_agents: viz-upgrades] 2026-08-12

"""The decision references a scored turn can carry, placed on two axes — and what each one's number MEANS.

A turn's counterfactuals answer "what would a computable agent have done here instead". The current campaign
schema (``five-seat-triple-counterfactuals-v1``) records FOUR of them, which is one point in a 2x2:

============== ============================== =================================
                self-interest                  table fairness
============== ============================== =================================
**private**     ``rational_private``           ``fairness_private``
**omniscient**  ``oracle_omniscient``          ``fairness_oracle``
============== ============================== =================================

The *information* axis says what the reference could see when it decided: only the acting seat's own sheet plus
the public moves, or every party's hidden sheet. The *objective* axis says what it was maximizing: its own
surplus, or a welfare score over the whole table.

**The two axes are not interchangeable, and the objective axis carries a unit hazard this module exists to
close.** A self-interest reference's ``value`` is priced in the acting seat's own points, so it is directly
comparable with that seat's realized surplus. A fairness reference's ``value`` is the *table* objective — a
smoothed log-Nash score over normalized surplus (see
:func:`~interlens.arena.negotiation.fairness.objective_from_normalized`) — which belongs to the whole table and
to no seat, is on a completely different scale, and has its own optimum recorded alongside it as
``table_optimum``. Two readers have already mistaken one for the other while reading these records by hand, so
every renderer takes its unit string from :data:`REFERENCES` rather than writing its own, and no page is allowed
to put the two kinds of value in one column.
"""
from __future__ import annotations

#: The objective a reference maximizes, and how its numbers must be labelled. ``value_label`` names the stored
#: ``value``; ``unit`` is the phrase every renderer prints beside it; ``gap_label`` names the shortfall a reader
#: can form from the record, which is a different quantity on each axis (a scored oracle's own ``divergence`` on
#: the self-interest side, ``table_optimum - value`` on the fairness side).
#: ``comparable_across_information`` is the second unit hazard, and it cuts the opposite way on the two axes. A
#: fairness row's ``value`` is the deal's TRUE full-information objective however little the policy that chose
#: the deal could see, so the private and omniscient fairness numbers are two scores on one scale and their
#: difference is the cost of deciding blind. A self-interest row's ``value`` is whatever that reference's own
#: evaluator produced: the private one is an expected value under the seat's posterior over the other sheets,
#: the omniscient one is exact on the true tables. Those two are the same UNIT and not the same QUANTITY, so
#: subtracting them measures nothing.
OBJECTIVES = {
    "own_surplus": {
        "name": "self-interest",
        "value_label": "oracle's value of its best move",
        "unit": "points of the acting seat's OWN surplus",
        "gap_label": "value improvement available",
        "comparable_across_information": False,
        "note": "Priced in the acting seat's own score-sheet points, so it is comparable with that seat's "
                "realized surplus — and with nothing on the fairness rows. Not comparable with the OTHER "
                "self-interest reference either: the private one values a move by its expected payoff under "
                "the seat's posterior over the hidden sheets, the omniscient one by its exact payoff on the "
                "true tables, so the two numbers answer different questions in the same unit.",
    },
    "table_fairness": {
        "name": "table fairness",
        "value_label": "table objective of the reference's move",
        "unit": "TABLE objective (smoothed log-Nash over normalized surplus) — not points, and not any one "
                "seat's",
        "gap_label": "fairness shortfall vs the best deal on the board",
        "comparable_across_information": True,
        "note": "A welfare score for the WHOLE table on its own scale, bounded by the best score any deal "
                "could reach (table optimum). It is not a surplus: a move that deliberately gives away the "
                "acting seat's own points can score higher here, which is the entire point of the reference "
                "and exactly why this number must never be read as a gain for the seat. Both fairness rows "
                "are priced on the same true objective, so the private row's shortfall against the omniscient "
                "one is a real measurement of what deciding blind costs the table.",
    },
}

#: What a reference could see when it decided, and — separately — how that turns into the number it reports.
#: Kept as data because the page states both on every counterfactual: an omniscient reference is a hindsight
#: ceiling rather than a policy the acting seat could have run, and its value is exact where the private one's
#: is an expectation.
INFORMATION = {
    "private": {
        "name": "private",
        "detail": "own sheet and the public moves only — implementable by the acting seat",
        "value_basis": "expected value under this seat's own posterior over the hidden sheets",
    },
    "omniscient": {
        "name": "omniscient",
        "detail": "every party's hidden sheet — a hindsight ceiling, not an implementable policy",
        "value_basis": "exact value on the true score tables",
    },
}

#: Every reference this visualizer understands, in the order pages present them: the two self-interest
#: references first (they are what the campaign's headline regret is measured against), then the two fairness
#: references, then the legacy omniscient comparator. Each entry names its cell of the 2x2 plus the label the
#: page prints. ``legacy`` marks a name kept only so old annotation vintages keep rendering under their own
#: name instead of being silently relabelled; such an entry may carry a ``role`` naming the modern reference it
#: stands in for, so a page branching on role needs no special case per historical spelling while the reference
#: still labels itself honestly.
REFERENCES: dict[str, dict] = {
    "rational_private": {
        "label": "private-information rational agent",
        "short": "rational · private",
        "information": "private",
        "objective": "own_surplus",
        "legacy": False,
    },
    "oracle_omniscient": {
        "label": "omniscient oracle",
        "short": "rational · omniscient",
        "information": "omniscient",
        "objective": "own_surplus",
        "legacy": False,
    },
    "fairness_private": {
        "label": "private-information fairness agent",
        "short": "fairness · private",
        "information": "private",
        "objective": "table_fairness",
        "legacy": False,
    },
    "fairness_oracle": {
        "label": "omniscient fairness oracle",
        "short": "fairness · omniscient",
        "information": "omniscient",
        "objective": "table_fairness",
        "legacy": False,
    },
    "bestresponse": {
        "label": "best-response oracle",
        "short": "rational · omniscient (legacy)",
        "information": "omniscient",
        "objective": "own_surplus",
        "role": "oracle_omniscient",
        "legacy": True,
    },
}

#: Reference names in presentation order.
REFERENCE_ORDER = tuple(REFERENCES)

#: Spellings older records used for the two self-interest references, mapped to the canonical name. Applied when
#: merging annotation stores so one page never shows the same reference twice under two names.
ALIASES = {
    "rational": "rational_private", "private_rational": "rational_private",
    "private_information_rational": "rational_private",
    "oracle": "oracle_omniscient", "omniscient": "oracle_omniscient",
    "omniscient_oracle": "oracle_omniscient",
    "fairness": "fairness_private", "fairness_rational": "fairness_private",
    "fairness_private_rational": "fairness_private",
    "fairness_omniscient": "fairness_oracle",
}


def canonical(name: str) -> str:
    """The canonical reference name for a stored one, or the stored name unchanged when it is not a reference."""
    return ALIASES.get(str(name), str(name))


def spec(name: str) -> dict | None:
    """The :data:`REFERENCES` entry for a (possibly aliased) name, or ``None`` for a generic scored oracle."""
    return REFERENCES.get(canonical(name))


def describe(name: str) -> dict:
    """Everything a renderer needs about one reference, flattened into one dict.

    Returns ``{}`` for a name that is not a known decision reference — a generic scored oracle keeps rendering
    through the page's older, name-agnostic path rather than being described wrongly. Otherwise the keys are
    ``role`` (the canonical name), ``label``, ``short``, ``information``, ``information_detail``, ``objective``,
    ``objective_name``, ``value_label``, ``unit``, ``value_basis``, ``comparable_across_information``,
    ``gap_label``, ``objective_note``, and ``legacy``.
    """
    entry = spec(name)
    if entry is None:
        return {}
    objective = OBJECTIVES[entry["objective"]]
    information = INFORMATION[entry["information"]]
    return {
        "role": entry.get("role") or canonical(name),
        "label": entry["label"],
        "short": entry["short"],
        "information": entry["information"],
        "information_detail": information["detail"],
        "objective": entry["objective"],
        "objective_name": objective["name"],
        "value_label": objective["value_label"],
        "unit": objective["unit"],
        # How the number was produced, which the unit alone does not say — an expectation and an exact value
        # share a unit without being the same quantity. Only meaningful on the self-interest axis, where the
        # two references really do use different evaluators; a fairness row is priced on the true objective
        # either way, which is what ``comparable_across_information`` records.
        "value_basis": (None if objective["comparable_across_information"] else information["value_basis"]),
        "comparable_across_information": objective["comparable_across_information"],
        "gap_label": objective["gap_label"],
        "objective_note": objective["note"],
        "legacy": entry["legacy"],
    }


def axes_payload() -> dict:
    """The 2x2's own description, shipped once per page so the browser groups the references from data.

    Carries the axis names, each cell's meaning, and — the part that matters — the per-objective unit and note
    strings, so the grid's column headers and the "these numbers are not comparable" warning are written here
    and nowhere else."""
    return {
        "order": list(REFERENCE_ORDER),
        "information": {k: dict(v) for k, v in INFORMATION.items()},
        "objective": {k: dict(v) for k, v in OBJECTIVES.items()},
    }
