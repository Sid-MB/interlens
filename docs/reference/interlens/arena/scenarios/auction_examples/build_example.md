# `build_example`

Drive one example's episode to its target stage and round, then render `(system, turn)` for its seat.

```python
build_example(cfg: dict) -> tuple[str, str]
```

Defined in [`interlens.arena.scenarios.auction_examples`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_examples.py#L114-L138)

The episode is played by a scripted straightforward bidder so the standing bids, the settled stages, and
the digest are all real ledger state rather than typed-in numbers; only the message history is scripted,
from :data:`NARRATIVES`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `cfg` | `dict` | *required* |  |
