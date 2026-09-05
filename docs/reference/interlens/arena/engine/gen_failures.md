# `gen_failures`

Every turn of an episode whose text the ENGINE fabricated because generation failed.

```python
gen_failures(episode) -> list[dict]
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L170-L212)

`episode` is an :class:`~interlens.arena.schema.Episode` or its `to_json()` dict. Returns a list of
`{"idx", "round", "seat", "phase", "reason", "detected_by"}`, one per fabricated turn.

Use this rather than hand-rolling a screen, because the honest test depends on when the episode was recorded:

- **v1.2 and later** carry an explicit `gen_failed` stamp (`detected_by="stamp"`), which also records the
  exception that caused it.
- **Older episodes** have no stamp, so they fall back to the legacy value signature
  (`detected_by="legacy_signature"`): content is exactly :data:`EMPTY_TURN_PLACEHOLDER`, zero output
  tokens, AND `raw is None`.

The legacy fallback is a conjunction, and it is worth being precise about which clause does what, because
getting this wrong in either direction has already happened:

- `content == EMPTY_TURN_PLACEHOLDER` does the discriminating work. `raw is None` **alone is useless** on
  local runs — a local non-thinking model's raw completion equals its content, so `record_turn` stores
  `raw=None` for essentially every healthy turn too (measured: all 2,683 turns of a clean 32B cell).
- `raw is None` is a GUARD, not the detector. Its job is to exclude the other producer of the same
  placeholder: a model that genuinely returned empty or reasoning-only text, which `record_turn` also
  replaces with the placeholder but for which `raw` holds the non-placeholder text it actually got. That is
  real model behaviour (a thinking model burning its cap) and a different problem with a different fix, so it
  must not be counted as an engine failure.

Because the stamp exists from v1.2 on, this fallback is only for pre-stamp records — do not build new tooling
on it. And do NOT screen with `parse_ok` or "is the content empty": the placeholder is a non-empty string
that parses into a well-formed no-op action, so a fully fabricated episode passes both.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` |  | *required* |  |
