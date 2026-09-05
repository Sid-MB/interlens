# `AuctionPromptScaffold`

One immutable prompt wording for the repeated-auction scenario.

```python
AuctionPromptScaffold(
	dm_worked_example: bool = True,
	show_own_surplus: bool = True,
	turn_marker: bool = True,
	RING_BLOCK_VERSION: str = 'ring_block_v1',
)
```

Defined in [`interlens.arena.scenarios.auction_prompts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L201-L925)

Every render method is keyword-only and takes primitives; the scenario computes the numbers and this class
decides only how they read. Construct a variant to ablate wording -- never edit
:class:`~interlens.arena.scenarios.auction.AuctionScenario`.

Parameters
----------
dm_worked_example : bool
    Whether the `dm` rung and above offer the one worked envelope example with literal ellipses for the
    message bodies. Filling those ellipses would be a demonstration of what to say, which at that rung is
    exactly what the design must not supply (`channel_blocks.md`); the knob exists so the omission is
    ablatable, not so it is optional.
show_own_surplus : bool
    Whether each seat's stage result reports its own realized surplus. On by default: the number is
    computable by the seat from its own private values and the public prices, so publishing it leaks
    nothing, and doing the arithmetic silently in a scratchpad is noise we do not want to measure.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `dm_worked_example` | `bool` | `True` |  |
| `show_own_surplus` | `bool` | `True` |  |
| `turn_marker` | `bool` | `True` |  |
| `RING_BLOCK_VERSION` | `str` | `'ring_block_v1'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `RING_BLOCK_VERSION` | `str` |  |
| `dm_worked_example` | `bool` |  |
| `show_own_surplus` | `bool` |  |
| `turn_marker` | `bool` |  |

## Methods {#methods}

## `catalogue` {#catalogue}

```python
catalogue(
	self,
	*,
	stage_index: int,
	horizon: int,
	rows,
	tie_break,
	attr_names,
	single_line: str | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L706-L733)

The per-stage header: the deadline restated, the catalogue, and the tie-break order.

`rows` is a list of `(lot_id, description, base_value, loading)` tuples at more than one lot;
`single_line` carries the pre-rendered one-lot form instead.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage_index` | `int` | *required* |  |
| `horizon` | `int` | *required* |  |
| `rows` |  | *required* |  |
| `tie_break` |  | *required* |  |
| `attr_names` |  | *required* |  |
| `single_line` | `str \| None` | `None` |  |

## `conduct` {#conduct}

```python
conduct(self, *, family: str, channel: str) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L577-L601)

The rules of the road: whole numbers, privacy, the budget rule, and the one-retry rule.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str` | *required* |  |
| `channel` | `str` | *required* |  |

## `envelope` {#envelope}

```python
envelope(self, *, family: str, channel: str, dm_cap: int, other_seat_ids) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L502-L561)

The four-channel JSON contract, with the fields present per channel rung.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str` | *required* |  |
| `channel` | `str` | *required* |  |
| `dm_cap` | `int` | *required* |  |
| `other_seat_ids` |  | *required* |  |

## `fallback` {#fallback}

```python
fallback(self, key: str, **kw={}) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L918-L925)

The second-failure notice: what was recorded for the turn, and that nothing written was delivered.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `key` | `str` | *required* |  |
| `kw` |  | `{}` |  |

## `format_rules` {#format_rules}

```python
format_rules(
	self,
	*,
	family: str,
	pricing: str,
	n_items: int,
	increment: int,
	start_price: int,
	reserve: int,
	round_cap: int,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L368-L381)

The mechanism block for this cell's family: rules, action grammar, JSON examples, tie-break, what is revealed between rounds, and the payment rule.

Exactly one section is ever rendered.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str` | *required* |  |
| `pricing` | `str` | *required* |  |
| `n_items` | `int` | *required* |  |
| `increment` | `int` | *required* |  |
| `start_price` | `int` | *required* |  |
| `reserve` | `int` | *required* |  |
| `round_cap` | `int` | *required* |  |

## `history_digest` {#history_digest}

```python
history_digest(self, *, digest_rows, message_log) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L741-L755)

Stages 1..t-1: the published per-stage outcome and this seat's own result, plus every message this seat sent or received, verbatim.

The bound is a design commitment, not an implementation detail: text is carried in full because
coordination lives in it, while prior stages' round-by-round bid ledgers are dropped once the stage
settles. Every lot's winner and price survives the compression -- the compression is of ROUNDS, not of
lots, since the per-lot outcome is what a market-division convention would be built on.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `digest_rows` |  | *required* |  |
| `message_log` |  | *required* |  |

## `objective` {#objective}

```python
objective(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L249-L258)

Own-surplus maximization, stated as self-contained.

The second paragraph is the neutrality anchor:
it rules out both "beat the others" and "help the others" readings without naming coordination.

## `own_result` {#own_result}

```python
own_result(self, *, stage_index: int, own_lots, own_paid: int, own_surplus: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L899-L903)

The private one-liner appended to a seat's own view of the stage result.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage_index` | `int` | *required* |  |
| `own_lots` |  | *required* |  |
| `own_paid` | `int` | *required* |  |
| `own_surplus` | `int` | *required* |  |

## `prior_statement` {#prior_statement}

```python
prior_statement(
	self,
	*,
	beta: float,
	sigma_z: float,
	sigma_eps: float,
	sigma_nu: float,
	value_structure: str,
	multi_item: bool,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L297-L365)

The load-bearing block: the generative model in plain language, and the statement that every bidder can reason about every other bidder's likely willingness to pay -- and that the reverse is equally true.

Under IPV the block is replaced wholesale rather than trimmed, because a bidder must not be told to
read signal into cards that carry none.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `beta` | `float` | *required* |  |
| `sigma_z` | `float` | *required* |  |
| `sigma_eps` | `float` | *required* |  |
| `sigma_nu` | `float` | *required* |  |
| `value_structure` | `str` | *required* |  |
| `multi_item` | `bool` | *required* |  |

## `private_block` {#private_block}

```python
private_block(
	self,
	*,
	stage_index: int,
	horizon: int,
	capital_position: str | None,
	value_rows,
	budget: int,
	synergy_target=None,
	synergy_bonus: int | None = None,
	capacity: int | None = None,
	decay: float | None = None,
	signal_rows=None,
	single_value: int | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L757-L793)

This seat's stage-`t` private block -- and the only block in the whole composition that contains anything private.

Lines are omitted rather than rendered empty when they do not apply.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage_index` | `int` | *required* |  |
| `horizon` | `int` | *required* |  |
| `capital_position` | `str \| None` | *required* |  |
| `value_rows` |  | *required* |  |
| `budget` | `int` | *required* |  |
| `synergy_target` |  | `None` |  |
| `synergy_bonus` | `int \| None` | `None` |  |
| `capacity` | `int \| None` | `None` |  |
| `decay` | `float \| None` | `None` |  |
| `signal_rows` |  | `None` |  |
| `single_value` | `int \| None` | `None` |  |

## `public_roster` {#public_roster}

```python
public_roster(self, *, cards, multi_item: bool, interdep: bool) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L260-L295)

The five PUBLIC cards, byte-identical in every seat's system prompt.

Parameters
----------
cards : list[dict]
    One dict per seat in seat order, with keys `persona_id`, `display_name`, `attrs` (the K
    signed entries, aligned with the attribute names), `capacity`, `synergy_rate`, `decay`,
    `gamma`.
multi_item : bool
    Whether the capacity / adjacency / decay figures are printed. At one lot per stage there is no
    adjacency and no capacity constraint to state, so the profile line stops after the attributes.
interdep : bool
    Whether the reseller's live resale weight is printed instead of the fixed-rate sentence.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `cards` |  | *required* |  |
| `multi_item` | `bool` | *required* |  |
| `interdep` | `bool` | *required* |  |

## `retry` {#retry}

```python
retry(self, key: str, **kw={}) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L906-L916)

One parser-feedback message, by key, in the `[Auctioneer]` register of `retry_messages.md`.

Every message has the same three-part shape -- what was wrong in terms of the actual submitted value,
what the rule is, what is legal instead -- and never restates strategy, comments on the quality of the
move, or introduces a number the seat did not already have.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `key` | `str` | *required* |  |
| `kw` |  | `{}` |  |

## `ring_block` {#ring_block}

```python
ring_block(self, *, channel: str, member_ids, n_bidders: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L613-L691)

The instructed-ring instruction, version :attr:`RING_BLOCK_VERSION`, transcribed from `templates/ring_block.md`, which sits OUTSIDE the neutral prompt freeze and is versioned separately.

**This block is outside the prompt freeze and inverts the neutrality rule the rest of this module
obeys**: it names coordination, division, and side payments in as many words. It exists to measure
CAPABILITY ("told a ring exists, can they run one?") rather than PROPENSITY ("do they form one?"), and
an episode that renders it may never be pooled with a neutral-prompt cell.

It still scripts nothing: no division, no bid level, no price target, no punishment or trigger scheme,
and no statement that participating is expected — every one of those is a measured quantity, and
supplying it would manufacture the result. The only per-channel variation is the side-payment
semantics, which restate what the envelope already established: under `dm_transfers` a declared
transfer is executed by the auctioneer at settlement, and at every lower rung a promised payment is
words.

Rendered ONLY into the system prompt of a seat in an `instructed`
:class:`~interlens.arena.auction.spec.RingSpec`, and appended as a strict suffix after `conduct` so
every frozen block above it is byte-identical to the outsider's and to a neutral cell's.

Parameters
----------
channel : str
    The cell's channel rung. Selects the side-payment bullet, and at `silent` there is no channel to
    coordinate in, which is a configuration this block refuses rather than papers over.
member_ids : Sequence[str]
    The `persona_id` of every ring member in seat order, INCLUDING the reading seat — a ring member
    has to know the whole membership, which is what makes the outsider identifiable to it.
n_bidders : int
    Seats at the table, so the count of non-parties is stated rather than left to be inferred.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `channel` | `str` | *required* |  |
| `member_ids` |  | *required* |  |
| `n_bidders` | `int` | *required* |  |

## `round_ask` {#round_ask}

```python
round_ask(
	self,
	*,
	family: str,
	round_no: int,
	round_cap: int,
	clock_price: int | None = None,
	increment: int | None = None,
	standing_rows=None,
	active=None,
	exited=None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L826-L845)

The bidding-round ask, carrying the live round state the format reveals and nothing else.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str` | *required* |  |
| `round_no` | `int` | *required* |  |
| `round_cap` | `int` | *required* |  |
| `clock_price` | `int \| None` | `None` |  |
| `increment` | `int \| None` | `None` |  |
| `standing_rows` |  | `None` |  |
| `active` |  | `None` |  |
| `exited` |  | `None` |  |

## `setting` {#setting}

```python
setting(self, *, n_bidders: int, horizon: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L227-L242)

The opening scene: what is being sold, and over how many stages.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_bidders` | `int` | *required* |  |
| `horizon` | `int` | *required* |  |

## `single_lot_line` {#single_lot_line}

```python
single_lot_line(
	self,
	*,
	name: str,
	blurb: str,
	base_value: int,
	loading,
	attr_names,
	tail: str,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L735-L739)

The one-lot collapse of the catalogue table, keeping the same columns as prose.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `blurb` | `str` | *required* |  |
| `base_value` | `int` | *required* |  |
| `loading` |  | *required* |  |
| `attr_names` |  | *required* |  |
| `tail` | `str` | *required* |  |

## `stage_result` {#stage_result}

```python
stage_result(self, *, family: str, stage_index: int, **kw={}) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L873-L897)

The public stage-result block: exactly what the format reveals and nothing more.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str` | *required* |  |
| `stage_index` | `int` | *required* |  |
| `kw` |  | `{}` |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(
	self,
	*,
	setting: str,
	your_seat: str,
	objective: str,
	roster: str,
	prior: str,
	rules: str,
	envelope: str,
	conduct: str,
	ring: str | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L693-L703)

Assemble the episode-level system prompt from the blocks above, in the reviewed order.

`ring` is the NON-FROZEN :meth:`ring_block`, or `None` for every committed cell. It appends after
`conduct` — last of the system blocks — so that the reviewed prefix is byte-identical with and
without it and a ring member's prompt is the outsider's prompt plus one suffix.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `setting` | `str` | *required* |  |
| `your_seat` | `str` | *required* |  |
| `objective` | `str` | *required* |  |
| `roster` | `str` | *required* |  |
| `prior` | `str` | *required* |  |
| `rules` | `str` | *required* |  |
| `envelope` | `str` | *required* |  |
| `conduct` | `str` | *required* |  |
| `ring` | `str \| None` | `None` |  |

## `talk_round` {#talk_round}

```python
talk_round(
	self,
	*,
	stage_index: int,
	talk_round_no: int,
	talk_rounds: int,
	channel: str,
	dm_cap: int,
	mid_stage: bool = False,
	clock_price: int | None = None,
	round_no: int | None = None,
	round_cap: int | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L796-L824)

The message round that runs before each stage's bidding.

`mid_stage` renders the §3.4 mid-stage variant instead: one message round on a LIVE clock, once it has
crossed the middle of its schedule. It differs from the pre-bidding round in exactly two ways, and both
are required rather than stylistic -- it may not say bidding has yet to begin, because it has, and it
must restate the price the clock is standing at, because a ring tested mid-stage is tested against that
number and a seat that had to infer it from the history digest would be answering a different question.
Every other sentence, including the whole channel body, is the reviewed pre-bidding wording verbatim.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage_index` | `int` | *required* |  |
| `talk_round_no` | `int` | *required* |  |
| `talk_rounds` | `int` | *required* |  |
| `channel` | `str` | *required* |  |
| `dm_cap` | `int` | *required* |  |
| `mid_stage` | `bool` | `False` |  |
| `clock_price` | `int \| None` | `None` |  |
| `round_no` | `int \| None` | `None` |  |
| `round_cap` | `int \| None` | `None` |  |

## `turn_ask` {#turn_ask}

```python
turn_ask(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L847-L849)

The single closing line of every turn prompt.

## `turn_id` {#turn_id}

```python
turn_id(self, *, turn_no: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L851-L863)

The opening line of every turn view: which turn of the auction this is.

**Added after the pilot, and the reason is a measurement rather than a wording preference.** In the
first live pilot run, 4 of 12 Opus requests came back with `stop_reason == "refusal"` and zero output
tokens -- an API-side classifier refusal, not the model declining. It reproduced deterministically for
a byte-identical request, survived the one retry (whose view still contains the trigger), and was NOT
semantic: substituting the datacenter vocabulary did not clear it, while removing almost any single
block did, and appending this one line cleared it 2/2. The line restates the turn index and no number
the seat does not already have, and it VARIES every turn, so a refusal cannot repeat identically
through an episode. It is a protocol change and is logged as one; the alternative was a campaign whose
parse-ok rate fails G1 for reasons that have nothing to do with the auction.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turn_no` | `int` | *required* |  |

## `turn_prompt` {#turn_prompt}

```python
turn_prompt(
	self,
	*,
	catalogue: str,
	digest: str,
	private: str,
	phase: str,
	turn_no: int | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L865-L870)

Assemble one turn view from the catalogue, the digest, the seat's private block, and one phase block.

Blocks that do not apply are omitted rather than rendered empty.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `catalogue` | `str` | *required* |  |
| `digest` | `str` | *required* |  |
| `private` | `str` | *required* |  |
| `phase` | `str` | *required* |  |
| `turn_no` | `int \| None` | `None` |  |

## `your_seat` {#your_seat}

```python
your_seat(self, *, display_name: str, seat_id: str) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L244-L247)

The one block that names the reading seat.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `display_name` | `str` | *required* |  |
| `seat_id` | `str` | *required* |  |
