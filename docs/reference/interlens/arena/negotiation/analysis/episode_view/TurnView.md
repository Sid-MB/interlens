# `TurnView`

One turn, normalized.

```python
TurnView(
	idx: int,
	round: int,
	seat: str,
	action_type: str,
	proposed_deal: Deal | None = None,
	accepted_offer_id: Any = None,
	rejected_offer_id: Any = None,
	walked: bool = False,
	stated_offer: Deal | None = None,
	stated_belief: Any = None,
	thinking: str | None = None,
	message: str | None = None,
	parse_ok: bool = True,
	raw_action: Any = None,
)
```

Defined in [`interlens.arena.negotiation.analysis.episode_view`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/episode_view.py#L47-L66)

`action_type` is the primary typed action; the granular fields coexist so a v1
turn that both registers a proposal and supports an id populates `proposed_deal` and
`accepted_offer_id` together.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `idx` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `seat` | `str` | *required* |  |
| `action_type` | `str` | *required* |  |
| `proposed_deal` | `Deal \| None` | `None` |  |
| `accepted_offer_id` | `Any` | `None` |  |
| `rejected_offer_id` | `Any` | `None` |  |
| `walked` | `bool` | `False` |  |
| `stated_offer` | `Deal \| None` | `None` |  |
| `stated_belief` | `Any` | `None` |  |
| `thinking` | `str \| None` | `None` |  |
| `message` | `str \| None` | `None` |  |
| `parse_ok` | `bool` | `True` |  |
| `raw_action` | `Any` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accepted_offer_id` | `Any` |  |
| `action_type` | `str` |  |
| `idx` | `int` |  |
| `message` | `str \| None` |  |
| `parse_ok` | `bool` |  |
| `proposed_deal` | `Deal \| None` |  |
| `raw_action` | `Any` |  |
| `rejected_offer_id` | `Any` |  |
| `round` | `int` |  |
| `seat` | `str` |  |
| `stated_belief` | `Any` |  |
| `stated_offer` | `Deal \| None` |  |
| `thinking` | `str \| None` |  |
| `walked` | `bool` |  |
