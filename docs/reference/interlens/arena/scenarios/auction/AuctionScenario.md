# `AuctionScenario`

Five bidders, `T` stages, one mechanism config, one communication rung.

```python
AuctionScenario(
	scaffold: AuctionPromptScaffold | None = None,
	turn_max_tokens: int = DEFAULT_TURN_MAX_TOKENS,
)
```

Defined in [`interlens.arena.scenarios.auction`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L121-L1170)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

Parameters
----------
scaffold : AuctionPromptScaffold | None
    The frozen wording. `None` uses :data:`~.auction_prompts.DEFAULT_AUCTION_SCAFFOLD`; a variant
    scaffold is how a wording ablation is run, never an edit to this class.
turn_max_tokens : int
    Per-turn output cap requested on every :class:`~interlens.arena.schema.SeatRequest`. The engine's
    budget can shrink it and never raise it, so a hosted floor is applied at the participant.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scaffold` | [AuctionPromptScaffold](../auction_prompts/AuctionPromptScaffold.md) \| None | `None` |  |
| `turn_max_tokens` | `int` | `DEFAULT_TURN_MAX_TOKENS` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `default_communication` |  |  |
| `has_solo` |  |  |
| `name` |  |  |
| `scaffold` |  |  |
| `turn_max_tokens` |  |  |

## Methods {#methods}

## `apply` {#apply}

```python
apply(self, state: dict, request: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L307-L348)

Read one turn, deliver its channels, record its binding move, and advance the wave when the last seat has answered.

A syntax or legality error gets exactly one retry carrying the parser's specific message; a second
failure records the format's fallback move and delivers nothing the seat wrote, so a channel payload
attached to an unparseable turn cannot get through by breaking the envelope.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `request` | [SeatRequest](../../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `classify_outcome` {#classify_outcome}

```python
classify_outcome(self, state: dict, turns: list, outcome: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L1166-L1170)

Episode-level tags the run index sorts on, computed purely from the stored outcome.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `turns` | `list` | *required* |  |
| `outcome` | `dict` | *required* |  |

## `generate_instance` {#generate_instance}

```python
generate_instance(self, level: int, seed: int, **overrides={}) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L145-L161)

Generate one auction instance from `seed`.

The payload carries the frozen spec under both value structures — `apv` (the default and the home of
the repeated questions) and `ipv` (the belief-free benchmark) — because switching structure zeroes
`beta` and `sigma_z` rather than redrawing, so the two are a within-bank paired contrast rather
than two populations. Freezing both means a cell selects rather than re-derives.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `overrides` |  | `{}` |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L164-L201)

Fresh episode state: the cell's spec (value structure, mechanism, horizon, channel selected from `cfg`), the ledger, the DM router, and the empty history the stage loop appends to.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | [Instance](../../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `seed` | `int` | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `next_requests` {#next_requests}

```python
next_requests(self, state: dict) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L270-L295)

The wave due now: every seat that must move, each with a view built BEFORE any of them replies, so the round is genuinely simultaneous and nobody sees what anyone else wrote before writing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, state: dict) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L302-L304)

Waves completed — the episode's own turn budget, distinct from stages.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `score` {#score}

```python
score(self, state: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L1113-L1164)

The episode outcome: per-stage rows, the episode aggregates every gate reads, and the protocol hygiene counters (design.md §5.3).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `seat_framings` {#seat_framings}

```python
seat_framings(self, state: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L1089-L1095)

`{seat_name: system prompt}` for the episode record.

A computable seat has no prose framing, so
it records the name of its decision rule instead of a prompt it never reads.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, state: dict) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L246-L253)

One record per seat for the episode file: the addressable seat id, its persona, and its public card parameters (never a draw).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `spec_for` {#spec_for}

```python
spec_for(self, instance: Instance, cfg: dict)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L203-L244)

The cell's spec: the frozen bank draws under the cell's value structure, with the cell's mechanism, horizon, and channel applied.

A cell never redraws. `mechanism` may be replaced (a single-lot bank serves the sealed, Dutch, and
English cells from identical draws, which is what makes R3 <-> R4 a within-bank paired contrast), but
its lot count may not change, since the draws are per-lot.

`cfg["scramble_cards"]` is the X1 control: the five public cards are permuted across the seats under
a derangement seeded from the INSTANCE ID, so X1 and its matched real-persona cell O1 read the same
frozen draws and the same scramble in every rerun (:func:`~interlens.arena.auction.spec
.scramble_public_cards`). It is applied last, after the mechanism, horizon and channel, so a scrambled
cell differs from its reference cell in the cards and in nothing else.

`cfg["ring"]` is a :class:`~interlens.arena.auction.spec.RingSpec` (or its JSON) for the NON-FROZEN
instructed-ring probe. It sets membership on the spec only; whether the members are TOLD is
`RingSpec.instructed`, read in :meth:`_ring_block`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | [Instance](../../schema/Instance.md) | *required* |  |
| `cfg` | `dict` | *required* |  |

## `state_block` {#state_block}

```python
state_block(self, state: dict, seat: int) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L1058-L1087)

The machine-readable turn state a computable seat reads in place of the prose turn prompt.

Carries this seat's OWN draws and the public round state. A rival's realized values appear only under
`oracle_values`, and only for an oracle seat — an explicitly named field, so reading it is a
deliberate act the policy's own information gate controls rather than an accident of serialization.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `seat` | `int` | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(self, state: dict, seat: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L872-L897)

The episode-level system prompt for `seat`: identical across seats except the one line that names the reading seat, so the public part is byte-identical and privacy cannot leak through it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `seat` | `int` | *required* |  |

## `turn_prompt` {#turn_prompt}

```python
turn_prompt(self, state: dict, seat: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L914-L921)

One turn view: the stage catalogue, the carried-history digest, this seat's private block, and the phase block.

Nothing private to any other seat can reach it — the catalogue and the digest are built
once and shared, and only :meth:`_private_block` reads a draw, for its owner only.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `seat` | `int` | *required* |  |
