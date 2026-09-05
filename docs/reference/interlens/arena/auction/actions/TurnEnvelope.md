# `TurnEnvelope`

One turn's four channels (design.md §3.2), separated: the private `scratchpad` (never published), public `message`, addressed `dms`, an optional `transfer`, and the one binding `action`.

```python
TurnEnvelope(
	scratchpad: str = '',
	message: str = '',
	dms: list[DirectMessage] = list(),
	transfer: Transfer | None = None,
	action: Action | None = None,
	raw: Any = None,
)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L554-L564)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scratchpad` | `str` | `''` |  |
| `message` | `str` | `''` |  |
| `dms` | list[[DirectMessage](DirectMessage.md)] | `list()` |  |
| `transfer` | [Transfer](Transfer.md) \| None | `None` |  |
| `action` | [Action](../../actions/Action.md) \| None | `None` |  |
| `raw` | `Any` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `action` | [Action](../../actions/Action.md) \| None |  |
| `dms` | list[[DirectMessage](DirectMessage.md)] |  |
| `message` | `str` |  |
| `raw` | `Any` |  |
| `scratchpad` | `str` |  |
| `transfer` | [Transfer](Transfer.md) \| None |  |
