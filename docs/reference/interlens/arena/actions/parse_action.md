# `parse_action`

Read ONE formal action from `text` (its last fenced/balanced JSON object), validated into a typed `Action` or a classified failure.

```python
parse_action(
	text: str,
	*,
	deal_decoder: Callable[[Any], Deal | None] | None = None,
	standing: Container[OfferId] | None = None,
	allowed: Container[str] | None = None,
) -> ParseResult
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L386-L413)

- `deal_decoder` maps a `Propose`'s `"deal"` object to a :data:`Deal` tuple, returning `None` for a
  malformed/infeasible deal (an economic-legality failure). When omitted, a deal given as a list of option
  indices is accepted as-is; any other shape is a legality failure.
- `standing` (the live offer ids, e.g. `registry.standing_ids()`) gates `Accept` / `Reject`: a
  reference to an id not in it is an economic-legality failure. When omitted, id existence is not checked
  here (the scenario/registry can check on apply).
- `allowed` optionally restricts which action kinds are legal at this point (e.g. only `accept` on a
  finalization turn); a disallowed-but-well-formed kind is a legality failure.

Accepts both the flat wire form `{"action": "propose"|"accept"|"reject"|"walk", ...}` and the nested form
`{"action": {"type": "propose", ...}}` (see :func:`_holder_and_kind`); `"offer_id"` also accepts the
aliases `"id"` / `"offer"`. A turn that mixes cheap talk with a move carries both in one object; the
scenario reads the `message` field itself and calls this for the action.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
| `deal_decoder` | `Callable[[Any], Deal \| None] \| None` | `None` |  |
| `standing` | `Container[OfferId] \| None` | `None` |  |
| `allowed` | `Container[str] \| None` | `None` |  |
