# `dm_reply`

The reply to a DM'd division or price proposal, driven by the policy's own :class:`~.bidders.Decision`.

```python
dm_reply(
	decision,
	*,
	instance_id: str,
	seat: int,
	stage: int,
	proposer: str,
	proposed_lots,
	proposer_lots,
	counter_lots=None,
	lapsed: bool = False,
) -> str
```

Defined in [`interlens.arena.auction.policy_text`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/policy_text.py#L139-L158)

Every reply carries the stage qualifier "this stage", and that is not decoration: the rational seat is
stage-myopic by construction, so wording its agreement as stage-scoped makes a later defection a
consistency of the seat rather than a broken promise. The seat is never made to claim a commitment its
policy cannot honor.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `decision` |  | *required* |  |
| `instance_id` | `str` | *required* |  |
| `seat` | `int` | *required* |  |
| `stage` | `int` | *required* |  |
| `proposer` | `str` | *required* |  |
| `proposed_lots` |  | *required* |  |
| `proposer_lots` |  | *required* |  |
| `counter_lots` |  | `None` |  |
| `lapsed` | `bool` | `False` |  |
