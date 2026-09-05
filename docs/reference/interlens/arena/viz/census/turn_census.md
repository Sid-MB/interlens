# `turn_census`

Count the ways this episode's turns carried nothing, from the payload's own turn rows.

```python
turn_census(rows: list[dict]) -> dict
```

Defined in [`interlens.arena.viz.census`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/census.py#L57-L109)

`rows` are the payload turns (see :func:`~interlens.arena.viz.episode.episode_payload`), which already
carry the three facts this needs — `silent` and `gen_failed` from the placeholder screen, `action.atype`
from the parse, and `cap` / `n_tokens_out` from generation accounting. Deriving the census from the same
rows the page renders is deliberate: a header that disagreed with the transcript below it would be worse
than no header.

Returns `{n_turns, placeholder, placeholder_budget_burned, placeholder_engine_failure, non_action,
non_action_rate, at_cap, at_cap_rate, placeholder_rate, by_round: [...], clean}`. `by_round` is one row
per round in play order with the same counts, which is what turns "a quarter of this episode is silent" into
"and all of it is in the last two rounds". `clean` is true only when every count is zero.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `list[dict]` | *required* |  |
