# `BestResponseOracle`

Per-turn expectimax best response for one seat.

```python
BestResponseOracle(
	agent: int,
	*,
	discount: float | None = None,
	accept_prob=None,
	opp_proposal=None,
	min_accept: int | None = None,
	veto_seats=(),
)
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L401-L652)

**Inherits from:** [Oracle](../../oracles/Oracle.md)

Parameters
----------
agent : int
    The deciding seat.
discount : float | None
    Per-round discount `delta` OVERRIDE; default `None` = read the game's own `discount` /
    `breakdown_risk` via `effective_discount` (single source of truth). Pass a float only to force it.
accept_prob : np.ndarray | None
    Optional `(D, n)` posterior acceptance-probability table (belief regime). None => full information.
opp_proposal : dict[int, int] | None
    Optional stationary modeled opponent proposals (belief regime). If None in the belief regime, each
    opponent is modeled as proposing its own posterior-expected-utility-maximizing deal (via
    `accept_prob` as a utility proxy is avoided; falls back to full-info proposal if sheets known).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `int` | *required* |  |
| `discount` | `float \| None` | `None` |  |
| `accept_prob` |  | `None` |  |
| `opp_proposal` |  | `None` |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accept_prob` |  |  |
| `agent` |  |  |
| `discount` |  |  |
| `min_accept` |  |  |
| `name` |  |  |
| `opp_proposal` |  |  |
| `veto_seats` |  |  |

## Methods {#methods}

## `evaluate` {#evaluate}

```python
evaluate(self, game, history, agent, legal)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L462-L595)

Value each legal action; `best` is the surplus-maximizing one.

`extra` carries the per-turn
`surplus_loss` of every action (`V(best) - V(action)`) and the best-response proposal deal.

Ties in the argmax are resolved by :meth:`_argmax_action`, which prefers any action over accepting an
offer that pays this seat strictly negative surplus, and only then falls back to the canonical
`action_key` order. A strict optimum is never overridden.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |
| `agent` |  | *required* |  |
| `legal` |  | *required* |  |

## `propose_values` {#propose_values}

```python
propose_values(
	self,
	tables: GameTables,
	cont: np.ndarray,
	agent: int | None = None,
	*,
	min_accept: int | None = None,
	veto_seats=None,
	objective=None,
) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L431-L460)

Expected value to `agent` of proposing each deal now, given the continuation vector `cont` (full-info: `cont` is the length-n discounted continuation; belief: pass agent scalar via a length-n vector with opponents' acceptance folded into `accept_prob`).

`agent` is the PROPOSING seat; `None` falls back to the constructor's `self.agent`. Pass it
explicitly whenever one oracle instance serves several seats — which is what a scenario's shared oracle
stack does (`BestResponseOracle(0)` reused for every seat), and what :meth:`evaluate` now does with the
seat it resolved. Getting this wrong is silent: the acceptance mask and the surplus column both come from
this seat, so a stale seat prices every proposal from the wrong sheet while accept/reject/walk values
(computed from the resolved seat) stay correct.

`objective` is an optional `(|D|,)` payoff column replacing `agent`'s own surplus as *what the
proposal is worth if it passes* — the substitution that makes this best-response machinery serve a
fairness-seeking proposer (`fairness.mnw_objective`). Only the payoff changes: which deals can pass
is still governed by the other seats' own-surplus acceptance, since the opponents remain
self-interested however this seat scores the outcome. `None` (default) is the exact prior behaviour.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `cont` | `np.ndarray` | *required* |  |
| `agent` | `int \| None` | `None` |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `None` |  |
| `objective` |  | `None` |  |
