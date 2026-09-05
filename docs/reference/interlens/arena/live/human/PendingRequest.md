# `PendingRequest`

One open ask of a human seat — what the browser renders a form from, and what the server validates a submission against.

```python
PendingRequest(
	seat: str,
	seat_idx: int,
	turn_idx: int,
	round: int,
	phase: str,
	state: Any = None,
	view: list[dict] = list(),
	legal: dict = dict(),
	block: dict = dict(),
)
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L82-L132)

Held by the participant while it blocks and mirrored into the `awaiting_human` event. Carrying the parsed
state (rather than re-parsing the prompt on submit) is what guarantees the form's legality rules and the
server's validation are computed from the same state the seat was conditioned on.

Parameters
----------
seat : str
    The seat display name being asked to move.
seat_idx : int
    Its index into the game's seat-indexed sheets/tables.
turn_idx : int
    The index the resulting turn will take.
round : int
    The negotiation round this move belongs to.
phase : str
    The scenario phase (proposal, voting, ...) — decides which actions are legal.
state : Any
    The `NegotiationState` reconstructed from the seat's view, including the live offer registry.
view : list[dict]
    The exact view the seat was conditioned on, kept so the dock can show the human the prompt they are
    answering rather than a paraphrase.
legal : dict
    `{can_accept: [offer_ids], can_reject: [offer_ids], can_offer: bool, can_walk: bool, can_pass: bool}`
    for this moment — see :func:`legal_actions`.
block : dict
    The raw `negotiation_state` JSON the state was reconstructed from. Kept alongside the typed state
    because `state` holds live `ScoreSheet`/`DealSpace` objects and the wire needs plain JSON; carrying
    the block the seat actually read (rather than re-serializing the typed state) means the browser and the
    seat are looking at the same bytes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `seat_idx` | `int` | *required* |  |
| `turn_idx` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `phase` | `str` | *required* |  |
| `state` | `Any` | `None` |  |
| `view` | `list[dict]` | `list()` |  |
| `legal` | `dict` | `dict()` |  |
| `block` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `block` | `dict` |  |
| `legal` | `dict` |  |
| `phase` | `str` |  |
| `round` | `int` |  |
| `seat` | `str` |  |
| `seat_idx` | `int` |  |
| `state` | `Any` |  |
| `turn_idx` | `int` |  |
| `view` | `list[dict]` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L128-L132)

The wire form carried in `awaiting_human` (the view is omitted — it is fetched with the snapshot).
