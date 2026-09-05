# `clear_replay_cache`

Drop every cached offer-prefix posterior.

```python
clear_replay_cache() -> None
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L562-L565)

Only needed to reclaim memory or to measure cold timings —
correctness never depends on the cache, since a hit and a miss produce the same state.
