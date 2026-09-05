# `turn_delta`

Append one committed turn's payload row to `rows` and return it — what a `turn_appended` event carries.

```python
turn_delta(
	episode: dict,
	turn: dict,
	rows: list[dict],
	*,
	geometry: Any = None,
	kinds: dict | None = None,
	oracles: dict | None = None,
	seat_party: dict | None = None,
) -> dict
```

Defined in [`interlens.arena.live.payload`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/payload.py#L40-L84)

`episode` is the live episode's `to_json()` (read for the seat list), `turn` the stored turn dict to
render, and `rows` the session's ACCUMULATED payload rows, appended to in place. `geometry` is the
session's prebuilt `GameGeometry`, `kinds` the `viz.episode.seat_kinds` result, `oracles` the
episode's per-turn oracle records and `seat_party` the seat-name -> party-index map: all four are
episode-scoped and computed once at session start rather than per turn.

The accumulated list is required, not a convenience. Three fields on a row — `published`, `offer_id` and
`standing_deal_index` — are properties of a turn's POSITION IN THE SEQUENCE rather than of the turn
(`viz.episode.public_ledger` derives them), and a retried turn retroactively flips an earlier row's
`published` to False. So the ledger is re-derived over the whole accumulated list after each append: a few
dozen rows of pure Python, next to an engine turn that just spent seconds in a model call. Skipping it is the
one way a streamed row can differ from the row a reload rebuilds.

Views are never reconstructed here (replaying the episode once per turn would be absurd on a live path), so a
turn the engine did not store a view for is reported `view_source="absent"` rather than reconstructed — the
honest answer, and the same one `episode_payload(reconstruct=False)` gives.

`kinds`, `oracles` and `seat_party` are derived from `episode` when omitted, so a caller with nothing
cached still gets a correct row. Pass the episode-scoped ones (`kinds`, `seat_party`, `geometry`) for
the live path; `oracles` is the exception that is normally left to default, since a turn's oracle records
are written by the engine as the turn is committed and so do not exist before it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `turn` | `dict` | *required* |  |
| `rows` | `list[dict]` | *required* |  |
| `geometry` | `Any` | `None` |  |
| `kinds` | `dict \| None` | `None` |  |
| `oracles` | `dict \| None` | `None` |  |
| `seat_party` | `dict \| None` | `None` |  |
