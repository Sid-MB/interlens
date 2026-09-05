# `TalkingBayesianPolicy`

`BayesianRationalPolicy` with a truthful templated message channel and (optionally) inbound listening.

```python
TalkingBayesianPolicy(
	*,
	commit: bool = False,
	narrate: bool = False,
	hint: bool = False,
	listen: bool = False,
	narrate_reliability: float = 0.85,
	narrate_strength: float = 0.6,
	hint_reliability: float = 0.85,
	hint_strength: float = 0.6,
	commit_tau_scale: float = 0.12,
	commit_strength: float = 0.6,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'talking-bayes-rational',
	**kwargs={},
)
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L254-L482)

**Inherits from:** [BayesianRationalPolicy](../strategies/BayesianRationalPolicy.md)

The decision rule is untouched: `act`/`vote` are inherited verbatim. Speaking variants add messages
only; the listening variant overrides `_accept_prob_table` to condition the SAME belief grid on parsed
counterparty statements before the inherited rule reads it. Actions are therefore byte-identical to the
base policy given the same beliefs — the experiment's gate G1.

Parameters
----------
commit : bool
    Emit the concession-schedule commitment on the first turn (T1 content): the optimal-stopping
    reservation bar per round under current beliefs, in own points and normalized units, falling to the
    walk-away floor. Labeled as the current plan — the live bar each turn remains authoritative.
narrate : bool
    Emit, on every turn with a standing offer, whether that offer clears the current bar and by how much
    (T2 content).
hint : bool
    Emit the per-issue ordinal top options on the first turn (T3 increment). No scores, no threshold.
listen : bool
    Parse other seats' statements (delivered by :class:`TalkingParticipant` on
    `state.statements`) into trust-discounted belief conditioning, and request the machine-readable
    convention from LLM seats in the first-turn message (T4 increment).
narrate_reliability, narrate_strength : float
    Trust discount for inbound narrations (see :func:`condition_on_narration`). `reliability` is the
    probability a claim is truthful/myopically consistent; `strength` tempers it against self-authored
    evidence.
hint_reliability, hint_strength : float
    Trust discount for inbound ordinal hints (:func:`condition_on_hint`).
commit_tau_scale, commit_strength : float
    Softness of the inbound declared-floor conditioning (:func:`condition_on_commit`): `scale` is the
    Gaussian width on the [0, 1] threshold scale, `strength` the tempering.
discount, walk_if_hopeless, name
    As in :class:`BayesianRationalPolicy`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `commit` | `bool` | `False` |  |
| `narrate` | `bool` | `False` |  |
| `hint` | `bool` | `False` |  |
| `listen` | `bool` | `False` |  |
| `narrate_reliability` | `float` | `0.85` |  |
| `narrate_strength` | `float` | `0.6` |  |
| `hint_reliability` | `float` | `0.85` |  |
| `hint_strength` | `float` | `0.6` |  |
| `commit_tau_scale` | `float` | `0.12` |  |
| `commit_strength` | `float` | `0.6` |  |
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'talking-bayes-rational'` |  |
| `kwargs` |  | `{}` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `VARIANTS` |  |  |
| `commit` |  |  |
| `commit_strength` |  |  |
| `commit_tau_scale` |  |  |
| `hint` |  |  |
| `hint_reliability` |  |  |
| `hint_strength` |  |  |
| `listen` |  |  |
| `narrate` |  |  |
| `narrate_reliability` |  |  |
| `narrate_strength` |  |  |

## Methods {#methods}

## `commentary` {#commentary}

```python
commentary(self, state: NegotiationState) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L435-L438)

The every-turn message (narration), or `None`. :class:`TalkingParticipant` appends it to the turn's public message on every turn, first and later alike.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `commit_message` {#commit_message}

```python
commit_message(self, state: NegotiationState) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L365-L379)

The first-turn concession-schedule commitment (T1).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `conditioned_belief_states` {#conditioned_belief_states}

```python
conditioned_belief_states(self, state: NegotiationState) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L441-L470)

Per-opponent posteriors after folding in the parsed statements riding on `state.statements` (attached by :class:`TalkingParticipant`), in transcript order, each softly and trust-discounted.

Offers condition exactly as in the base policy (same `fit_belief`); statements about a seat's own
valuation condition that seat's grid.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `convention_message` {#convention_message}

```python
convention_message(self, state: NegotiationState) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L406-L417)

The first-turn request (T4 increment) that language-model seats state their own constraints in the machine-readable convention this policy can actually consume.

Claims are trust-discounted, never
taken as fact.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `current_bar` {#current_bar}

```python
current_bar(self, state: NegotiationState) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L343-L352)

This turn's acceptance bar in own sheet points: the walk-away floor on a terminal vote (no continuation exists), else the optimal-stopping reservation at the rounds actually left — the exact `r_left` clamp `act` uses.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `declaration` {#declaration}

```python
declaration(self, state: NegotiationState) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L423-L433)

The one-time first-turn message: commitment schedule, ordinal tops, and/or the LLM convention request, per this variant's flags.

`PolicyParticipant` publishes it exactly like LLM chat.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `hint_message` {#hint_message}

```python
hint_message(self, state: NegotiationState) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L398-L404)

The first-turn ordinal-tops hint (T3 increment).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `issue_tops` {#issue_tops}

```python
issue_tops(self, state: NegotiationState) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L354-L358)

`{issue_name: option_name}` — this seat's true ordinal top per issue, ties broken by first index (deterministic).

Read straight off the sheet's per-issue value rows.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `narrate_message` {#narrate_message}

```python
narrate_message(self, state: NegotiationState) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L381-L396)

This turn's standing-offer narration (T2), or `None` when there is nothing to narrate.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

## `reservation_schedule` {#reservation_schedule}

```python
reservation_schedule(self, state: NegotiationState) -> list[tuple[int, float]]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L324-L341)

`[(round, bar_points), ...]` for every round 1..deadline+1: the own-sheet score a package must reach for this seat to stop, under CURRENT beliefs — the same acceptance-oracle reservation `act` prices the standing offer against, plus the walk-away floor at the forced final (where the terminal vote accepts anything individually rational).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |
