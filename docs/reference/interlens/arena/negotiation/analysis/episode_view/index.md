# `episode_view`

Module `interlens.arena.negotiation.analysis.episode_view`

`EpisodeView`: a stored arena `Episode` JSON parsed into a normalized negotiation action series that the
metrics read instead of raw `parsed_action` — an ordered `TurnView` list (typed action, deal canonicalized
to an index tuple, offer id, any acceptable-offer/belief note, private thinking), the offer registry, the
per-round standing offer, and the final deal / reached flag.

The field-name maps below are the single adapter for the arena action layer's serialization: tolerant to the
scorable scenario's `{atype, deal_named, offer}` shape (offer ids `P{n}` in proposal order), the canonical
typed `{"action": "propose", "deal": [idx...]}` shape, and the older v1 `{proposal, support}` shape.

## Classes

| Name | Summary |
|---|---|
| [`EpisodeView`](EpisodeView.md) | A parsed episode: seats, the turn series, the offer registry, per-round standing offer, and outcome. |
| [`TurnView`](TurnView.md) | One turn, normalized. |
