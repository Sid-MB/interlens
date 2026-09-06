# `references`

Module `interlens.arena.viz.references`

The decision references a scored turn can carry, placed on two axes — and what each one's number MEANS.

A turn's counterfactuals answer "what would a computable agent have done here instead". The current campaign
schema (`five-seat-triple-counterfactuals-v1`) records FOUR of them, which is one point in a 2x2:

============== ============================== =================================
                self-interest                  table fairness
============== ============================== =================================
**private**     `rational_private`           `fairness_private`
**omniscient**  `oracle_omniscient`          `fairness_oracle`
============== ============================== =================================

The *information* axis says what the reference could see when it decided: only the acting seat's own sheet plus
the public moves, or every party's hidden sheet. The *objective* axis says what it was maximizing: its own
surplus, or a welfare score over the whole table.

**The two axes are not interchangeable, and the objective axis carries a unit hazard this module exists to
close.** A self-interest reference's `value` is priced in the acting seat's own points, so it is directly
comparable with that seat's realized surplus. A fairness reference's `value` is the *table* objective — a
smoothed log-Nash score over normalized surplus (see
:func:`~interlens.arena.negotiation.fairness.objective_from_normalized`) — which belongs to the whole table and
to no seat, is on a completely different scale, and has its own optimum recorded alongside it as
`table_optimum`. Two readers have already mistaken one for the other while reading these records by hand, so
every renderer takes its unit string from :data:`REFERENCES` rather than writing its own, and no page is allowed
to put the two kinds of value in one column.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ALIASES` |  |  |
| `INFORMATION` |  |  |
| `OBJECTIVES` |  |  |
| `REFERENCES` | `dict[str, dict]` |  |
| `REFERENCE_ORDER` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`axes_payload`](axes_payload.md) | The 2x2's own description, shipped once per page so the browser groups the references from data. |
| [`canonical`](canonical.md) | The canonical reference name for a stored one, or the stored name unchanged when it is not a reference. |
| [`describe`](describe.md) | Everything a renderer needs about one reference, flattened into one dict. |
| [`spec`](spec.md) | The :data:`REFERENCES` entry for a (possibly aliased) name, or `None` for a generic scored oracle. |
