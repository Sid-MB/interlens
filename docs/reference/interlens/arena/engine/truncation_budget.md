# `truncation_budget`

The output budget one stored turn's `n_tokens_out` may honestly be compared against; `0` for "none, so read truncation from `stop_reason` alone".

```python
truncation_budget(turn: dict, *, cap_floor: int = 0) -> int
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L223-L245)

Two stored fields look like this number and only one is it. `cap` is what the PROTOCOL asked for, and a
participant may raise it before sending — `APIParticipant` sends `max(cap, turn_token_floor)` — so on a
hosted-API turn the stored `cap` can be a factor of eight below the budget the request ran under. Comparing
against it manufactures truncation out of ordinary long turns: measured over the frozen five-arm Opus corpus,
all 450 turns a `n_tokens_out >= cap` screen flagged carry `stop_reason: end_turn` and *exceed* the stored
cap, up to 8,545 tokens against 2,048 (0.208 reported truncation against 0.000 real).

So `effective_cap` (v1.3+) is used when present. On a pre-v1.3 record it is absent and the difference was
never stored, so the fallback reserves `cap` for turns carrying **no** `stop_reason` — which is exactly the
population the comparison was written for, since local `ModelParticipant`\ s never populate one and hosted
providers always do.

`cap_floor` is the escape hatch for a legacy run whose real budget is known from outside the record (a
manifest's `api_request_config.turn_token_floor`, or a `--turn-max-tokens` the stored caps understate): it
raises the returned budget, so a turn only counts as a cap hit if it reached the budget the run really had.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turn` | `dict` | *required* |  |
| `cap_floor` | `int` | `0` |  |
