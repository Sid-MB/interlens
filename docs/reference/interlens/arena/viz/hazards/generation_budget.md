# `generation_budget`

The per-seat generation budget this episode actually ran at, and whether it is the frozen default.

```python
generation_budget(payload: dict) -> dict
```

Defined in [`interlens.arena.viz.hazards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/hazards.py#L146-L182)

Reads three sources, most authoritative first, and reports all three rather than collapsing them — a badge
that said only "raised" would leave a reader unable to tell a protocol option from an API floor:

- `caps` — the distinct `max_tokens` values stamped on this episode's own requests. This is the record.
- `turn_max_tokens` — the protocol option that raised them, from the episode's `cell_cfg`. Stamped only
  when set, which is exactly why it cannot be the detector.
- `api_floors` — `{model: turn_token_floor}` from the run manifest's `api_request_config`. An API
  participant applies its floor as `max(cap, floor)`, so an API seat's effective budget is the floor even
  though the request's own cap says otherwise. This is the term that made two arms look matched when they
  were not.

`default` is true only when the observed caps are a subset of :data:`FROZEN_TURN_CAPS` and no API floor
exceeds them. `effective` is the largest budget any seat could actually use.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
