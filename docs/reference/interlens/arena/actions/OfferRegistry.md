# `OfferRegistry`

Monotonic offer ids + standing-offer tracking for the formal protocol.

```python
OfferRegistry(prefix: str = 'O')
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L190-L290)

`register` mints `{prefix}{n}` ids (`O1`, `O2`, ...); the proposer is recorded as an implicit accept
of its own offer (proposing implies supporting it). `accept` / `reject` record a seat's vote on a live
offer (a vote on a dead/unknown offer is refused and returns False). Withdrawing an offer marks it not-live
without deleting it, so the ledger stays complete for the record. The registry is a pure function of the
action sequence, so replay reconstructs it identically; `to_json` / `from_json` also persist it directly.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `prefix` | `str` | `'O'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `offers` | dict[OfferId, [Offer](Offer.md)] |  |
| `prefix` |  |  |

## Methods {#methods}

## `accept` {#accept}

```python
accept(self, offer_id: OfferId, agent: str) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L240-L248)

Record `agent`'s ACCEPT of a live offer; a reject by the same agent is cleared.

Returns False (no
effect) when the offer is unknown or dead.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |
| `agent` | `str` | *required* |  |

## `apply` {#apply}

```python
apply(self, action: Action, agent: str, *, round: int = 0) -> OfferId | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L267-L277)

Fold one parsed `action` into the registry: `Propose` registers (returns the new id), `Accept` / `Reject` record the vote, `Walk` is a no-op here (the scenario handles the exit).

Returns the new
offer id for a `Propose`, else `None`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [Action](Action.md) | *required* |  |
| `agent` | `str` | *required* |  |
| `round` | `int` | `0` |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'OfferRegistry'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L283-L290)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `get` {#get}

```python
get(self, offer_id: OfferId) -> Offer | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L220-L221)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |

## `is_live` {#is_live}

```python
is_live(self, offer_id: OfferId) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L223-L225)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |

## `register` {#register}

```python
register(
	self,
	deal: Deal,
	proposer: str,
	*,
	round: int = 0,
	implicit_accept: bool = True,
) -> OfferId
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L205-L218)

Mint a new live offer for `deal` by `proposer` and return its id.

The proposer implicitly accepts.

`implicit_accept=False` registers the offer with an EMPTY accept set — the explicit no-vote path for a
proposer that is not a party to the deal (:data:`FACILITATOR`). Without it a mediator's own id would sit
in `accepts` and any closure rule that counts the accept set (or renders "accepted by: ...") would
report a vote nobody cast.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |
| `proposer` | `str` | *required* |  |
| `round` | `int` | `0` |  |
| `implicit_accept` | `bool` | `True` |  |

## `reject` {#reject}

```python
reject(self, offer_id: OfferId, agent: str) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L250-L258)

Record `agent`'s REJECT of a live offer; an accept by the same agent is cleared.

Returns False when
the offer is unknown or dead.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |
| `agent` | `str` | *required* |  |

## `standing` {#standing}

```python
standing(self) -> list[Offer]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L227-L229)

Live offers, in registration order.

## `standing_ids` {#standing_ids}

```python
standing_ids(self) -> list[OfferId]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L231-L238)

Live offer ids in REGISTRATION order (same order as :meth:`standing`).

A list, not a set, deliberately: callers build ordered things out of it — the legal-action set an oracle
scores, and hence the stored verdict — and a set's iteration order varies with `PYTHONHASHSEED`, which
used to make a saved annotation differ run to run. Membership tests (`offer_id in standing_ids()`, how
:func:`parse_action` gates accept/reject) read the same either way.

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L279-L281)

## `withdraw` {#withdraw}

```python
withdraw(self, offer_id: OfferId) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L260-L265)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |
