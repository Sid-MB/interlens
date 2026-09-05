# `interlens.arena.scenarios.priors`

Role-prior sign table for the negotiation scenario (role × issue) and sheet-vs-prior analysis helpers.

A negotiation seat has two pulls: its generated *score sheet* (the payoff gradient) and its *role stereotype*
(a Developer "should" dislike a big community fund). This table records, per (role, issue) where the stereotype
is clear, which options the role-prior FAVORS and DISFAVORS — sign/monotonicity only, deliberately coarse, with
"no prior" the default (Site has no prior for anyone). Two uses:

- **Role-coherent instance generation** (`Negotiation.generate_instance(coherent=True)`): each seat's sheet is
  permuted so its own-best options never fall in its role's disfavored set — removing the character-vs-payoff
  tension so measured behavior reflects the game, not a personality conflict.
- **Conflict analysis** (`conflicted_slots` / `classify_choice`): on incoherent instances, a "conflict"
  slot is one where the sheet's own-best option is role-disfavored — the natural experiment for whether a seat
  follows its sheet or its character.

Issue option orders (for reference):
    Site          [Northgate, Riverbend, Eastfield, Harborview]   (no prior)
    PowerSource   [Grid, SolarPPA, GasPeaker]      clean=SolarPPA, dirty=GasPeaker
    WaterPlan     [Municipal, Recycled, AirCooled, Hybrid]   sustainable vs Municipal
    CommunityFund [None, 1M, 5M, 15M]              ordinal spend, high=15M
    Timeline      [Fast18mo, Standard30mo, Phased48mo]   fast vs slow

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `PRIORS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`classify_choice`](classify_choice.md) | On a conflicted slot, was the seat's CHOSEN option sheet-following, role(prior)-following, or neither? |
| [`conflicted_slots`](conflicted_slots.md) | `(role_idx, issue_name, sheet_option, favor, disfavor)` for every slot where the sheet's own-best option is one the role prior DISFAVORS. |
| [`sheet_argmax_option`](sheet_argmax_option.md) | The option name the seat's SHEET scores highest for one issue. |
