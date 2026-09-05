# `statements_in`

Every well-formed talking-rational statement in `text`, plus the census the honesty audit needs.

```python
statements_in(text: str, *, space=None, personas=()) -> tuple[list[dict], int, int]
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L158-L210)

Returns `(statements, n_candidates, n_dropped)`. Each statement is a normalized dict with `kind`
(:data:`STATEMENT_KINDS`), `seat` (int), and kind-specific fields — `narrate`: `above` (bool) plus
optionally `deal` (index tuple) and `offer_id`; `hint`: `tops` `{issue_index: option_index}`;
`commit`: `floor_norm` (float in [0, 1]) if the block carried one. The parser is TOTAL: an unparseable
or schema-violating candidate is dropped and counted in `n_dropped`, never raised, because a listening
seat must survive arbitrary LLM text.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
| `space` |  | `None` |  |
| `personas` |  | `()` |  |
