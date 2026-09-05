# `budget_badge`

The per-seat generation budget, stated whenever it is not the frozen default.

```python
budget_badge(budget: dict | None) -> str
```

Defined in [`interlens.arena.viz.hazards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/hazards.py#L246-L263)

Muted-informational rather than alarming: a raised cap is a deliberate protocol choice and often the right
one. What it is not is comparable — so the badge names the number and says which frozen pair it departs
from, and stays silent on a default run so the exception reads as exceptional.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `budget` | `dict \| None` | *required* |  |
