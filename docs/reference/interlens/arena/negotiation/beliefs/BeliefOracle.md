# `BeliefOracle`

Maintains a per-opponent `BeliefState` for one agent and exposes the posteriors as the `beliefs` payload of an `OracleVerdict` (this oracle annotates beliefs; it does not itself value moves, so `action_values` is left empty and `best` None).

```python
BeliefOracle(
	agent: int,
	*,
	sigma: float = 0.25,
	lam: float = 1.0,
	floor: float = 0.001,
	mode: str = 'auto',
	anchor_first: bool = True,
	seed: int = 0,
	types=None,
)
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L571-L617)

**Inherits from:** [Oracle](../../oracles/Oracle.md)

Consumed by the acceptance / best-response oracles
and the `BayesianRationalPolicy` for their induced `(utility, threshold)` distributions.

Parameters mirror `BeliefState` (`sigma`/`lam`/`floor`/`mode`/`anchor_first`); `agent` is
the seat whose opponents are modeled.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `int` | *required* |  |
| `sigma` | `float` | `0.25` |  |
| `lam` | `float` | `1.0` |  |
| `floor` | `float` | `0.001` |  |
| `mode` | `str` | `'auto'` |  |
| `anchor_first` | `bool` | `True` |  |
| `seed` | `int` | `0` |  |
| `types` |  | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `agent` |  |  |
| `name` |  |  |
| `states` | dict[int, [BeliefState](BeliefState.md)] |  |

## Methods {#methods}

## `evaluate` {#evaluate}

```python
evaluate(self, game, history, agent, legal)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L602-L617)

Annotate the current turn with per-opponent posteriors.

Reads opponent offers from `history`
(turns with a `Propose` action) if present; otherwise assumes `update_from_offers` was already
called. Returns a verdict whose `beliefs` is a JSON-safe per-opponent summary (MAP type + tau
posterior + entropy), with the rich `(OpponentType, prob)` induced distributions in `extra`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |
| `agent` |  | *required* |  |
| `legal` |  | *required* |  |

## `update_from_offers` {#update_from_offers}

```python
update_from_offers(self, offers_by_opponent: dict, option_counts)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L590-L600)

Feed each opponent's ordered list of proposed deals into its belief state (idempotent rebuild: resets and replays, so it is safe to call each turn with the full history).

The replay goes through :func:`replay_belief`, which reuses the longest cached offer prefix, so
"rebuild from scratch every turn" costs one folded observation per turn rather than the whole history.
The result is identical either way — that function returns a private copy of a pure fold.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offers_by_opponent` | `dict` | *required* |  |
| `option_counts` |  | *required* |  |
