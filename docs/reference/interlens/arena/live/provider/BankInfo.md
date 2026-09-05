# `BankInfo`

One instance bank the lobby may draw a game from.

```python
BankInfo(
	bank_id: str,
	label: str,
	instance_ids: tuple[str, ...] = (),
	n_parties: int | None = None,
	description: str = '',
)
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L159-L188)

Parameters
----------
bank_id : str
    Stable identifier passed back to :meth:`ScenarioProvider.prepare` (for the rational-agents launcher, the
    instances directory name, e.g. `"instances_realistic_demo"`).
label : str
    Display name.
instance_ids : tuple[str, ...]
    The instances in the bank, in a stable order. The lobby offers a pick from these plus "random".
n_parties : int | None
    Seat count, when every instance in the bank shares one (the usual case) — the lobby builds that many seat
    cards before an instance is chosen. `None` for a mixed bank, where the cards wait for :meth:`prepare`.
description : str
    One line about what the bank contains, shown under the picker.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bank_id` | `str` | *required* |  |
| `label` | `str` | *required* |  |
| `instance_ids` | `tuple[str, ...]` | `()` |  |
| `n_parties` | `int \| None` | `None` |  |
| `description` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `bank_id` | `str` |  |
| `description` | `str` |  |
| `instance_ids` | `tuple[str, ...]` |  |
| `label` | `str` |  |
| `n_parties` | `int \| None` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L185-L188)

The lobby's wire form.
