# `PromptScaffold`

One immutable prompt wording.

```python
PromptScaffold(
	game_intro: str = 'You are one of {n} parties negotiating a single multi-issue agreement. Exactly one option must be chosen for every issue; the chosen options together form the deal.',
	scratchpad_help: str = 'private notes to yourself. NEVER shown to any other party. Reason here freely — writing here is not speaking and costs you nothing.',
	message_help: str = 'a short statement spoken aloud to every party (cheap talk — it does not bind you). Do NOT put your private score numbers here.',
	action_help: str = 'exactly one formal move this turn.',
	worked_examples: bool = True,
	include_pass: bool = True,
	show_role_lines: bool = False,
)
```

Defined in [`interlens.arena.scenarios.scorable_prompts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L56-L270)

Construct a variant to ablate wording; never edit the scenario.

All game *content* (issue names, option labels, party names, sheets, thresholds, round budget, info
condition, chat flag) is passed into the render methods by the scenario — this object holds only the
fixed *wording* around that content, so a single scaffold renders any instance. Every field below is a
template fragment or a toggle; the render methods assemble them.

Fields
------
game_intro : str
        One-line framing of what the parties are doing; `{n}` is the party count. Deliberately generic /
        de-anchored — the concrete subject matter lives in the (fictional) issue labels.
scratchpad_help, message_help, action_help : str
        The per-field guidance in the action-format block.
worked_examples : bool
        Include the two worked-example JSON blocks (propose-with-message, accept). On by default — worked
        examples materially raise format compliance for smaller models; turn off to ablate.
include_pass : bool
        Advertise the talk-only `{"type": "none"}` move. On by default so talking without moving is explicit
        rather than smuggled into a malformed action.
show_role_lines : bool
        Render each party's public role description (which can leak preferences). OFF by default to keep sheets
        decorrelated from public text (the communication-free-baseline leak, Study A 2502.16242). Turn on only
        to *measure* the leak.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game_intro` | `str` | `'You are one of {n} parties negotiating a single multi-issue agreement. Exactly one option must be chosen for every issue; the chosen options together form the deal.'` |  |
| `scratchpad_help` | `str` | `'private notes to yourself. NEVER shown to any other party. Reason here freely — writing here is not speaking and costs you nothing.'` |  |
| `message_help` | `str` | `'a short statement spoken aloud to every party (cheap talk — it does not bind you). Do NOT put your private score numbers here.'` |  |
| `action_help` | `str` | `'exactly one formal move this turn.'` |  |
| `worked_examples` | `bool` | `True` |  |
| `include_pass` | `bool` | `True` |  |
| `show_role_lines` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `action_help` | `str` |  |
| `game_intro` | `str` |  |
| `include_pass` | `bool` |  |
| `message_help` | `str` |  |
| `scratchpad_help` | `str` |  |
| `show_role_lines` | `bool` |  |
| `worked_examples` | `bool` |  |

## Methods {#methods}

## `action_format_block` {#action_format_block}

```python
action_format_block(self, *, chat_enabled: bool) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L118-L170)

The single action-format contract + worked examples.

`chat_enabled` toggles the public message
channel (moves-only arm disables it — a `message` field is then ignored by the harness).

The wire form is ONE flat fenced JSON object: a string `"action"` field with its parameters as
siblings (`"deal"` / `"offer_id"`), alongside the private `"scratchpad"` and public `"message"`
channels. This matches the shared typed-action parser (`interlens.arena.actions.parse_action`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `chat_enabled` | `bool` | *required* |  |

## `final_prompt` {#final_prompt}

```python
final_prompt(self, *, seat: str, offers_block: str) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L233-L242)

The forced-final prompt when the round budget is exhausted with no deal: the current opener must either table a last binding proposal or walk.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `offers_block` | `str` | *required* |  |

## `info_condition_note` {#info_condition_note}

```python
info_condition_note(self, *, info: str) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L190-L196)

The one line describing what a seat knows about others' sheets (FULL vs PRIVATE).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `info` | `str` | *required* |  |

## `private_block` {#private_block}

```python
private_block(
	self,
	*,
	seat: str,
	role_desc: str,
	sheet_lines: list[str],
	threshold: float,
	persona: str | None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L172-L188)

The seat's private framing: who it is, its secret score sheet, its threshold, optional persona.

`sheet_lines` are `"- Issue: OptA=12, OptB=0, ..."` rendered by the scenario.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `role_desc` | `str` | *required* |  |
| `sheet_lines` | `list[str]` | *required* |  |
| `threshold` | `float` | *required* |  |
| `persona` | `str \| None` | *required* |  |

## `rules_block` {#rules_block}

```python
rules_block(
	self,
	*,
	n: int,
	party_lines: list[str],
	issue_lines: list[str],
	proposer_order: list[str],
	rounds: int,
	veto_line: str,
	pass_rule: str,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L97-L116)

The public, common-knowledge rules every seat sees: parties, issues+options, turn/deadline protocol, and the exact deal-closing rule.

`party_lines` already includes role text iff
`show_role_lines`; `issue_lines` are `"- Name: OptA, OptB, ..."` rendered by the scenario.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int` | *required* |  |
| `party_lines` | `list[str]` | *required* |  |
| `issue_lines` | `list[str]` | *required* |  |
| `proposer_order` | `list[str]` | *required* |  |
| `rounds` | `int` | *required* |  |
| `veto_line` | `str` | *required* |  |
| `pass_rule` | `str` | *required* |  |

## `solo_system_prompt` {#solo_system_prompt}

```python
solo_system_prompt(
	self,
	*,
	n: int,
	rules: str,
	all_sheets: str,
	threshold_note: str,
	pass_rule: str,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L245-L264)

The communication-free control (Study A 2502.16242): ONE agent with every sheet, proposing alone.

This baseline must NOT be competitive with the full multi-agent game — if it is, the benchmark is
measuring feasible-set search, not negotiation.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int` | *required* |  |
| `rules` | `str` | *required* |  |
| `all_sheets` | `str` | *required* |  |
| `threshold_note` | `str` | *required* |  |
| `pass_rule` | `str` | *required* |  |

## `solo_turn_prompt` {#solo_turn_prompt}

```python
solo_turn_prompt(self, *, forced: bool) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L266-L270)

The solo agent's per-step nudge; `forced` is the budget-exhausted last call.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `forced` | `bool` | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(
	self,
	*,
	rules: str,
	private: str,
	action_format: str,
	info_note: str,
	full_info_sheets: str | None,
	seat_index: int | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L199-L214)

Assemble a seat's complete system prompt.

`full_info_sheets` is the block of all parties' sheets,
present only in the FULL-information condition.

`seat_index` is the acting seat's index, passed by the scenario and **ignored here** — the seat is
already rendered into `private`, so the base assembly does not need it. It exists so a subclass can
vary the prompt PER SEAT (e.g. appending a reasoning workflow to one focal seat only, for a
treatment-vs-control arm) without the scenario having to know which subclass it holds. Overriding
subclasses that do not care may omit it; the base accepts and drops it, so existing scaffolds and
stored-episode replay are byte-identical.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rules` | `str` | *required* |  |
| `private` | `str` | *required* |  |
| `action_format` | `str` | *required* |  |
| `info_note` | `str` | *required* |  |
| `full_info_sheets` | `str \| None` | *required* |  |
| `seat_index` | `int \| None` | `None` |  |

## `turn_prompt` {#turn_prompt}

```python
turn_prompt(
	self,
	*,
	seat: str,
	round_no: int,
	rounds: int,
	is_opener: bool,
	offers_block: str,
	chat_enabled: bool,
	seat_index: int | None = None,
) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable_prompts.py#L216-L231)

The per-turn user prompt: restates the deadline (Lesson 13), lists live offers with ids, and names whose turn it is.

`offers_block` is the scenario-rendered live-offers summary (with, privately, this
seat's own score for each live offer when the scenario surfaces it). `seat_index` mirrors
:meth:`system_prompt` — the acting seat's index, ignored by the base assembly and available to per-seat
subclasses (`seat` already names the seat; the index is what a seat-targeting arm is configured with).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `round_no` | `int` | *required* |  |
| `rounds` | `int` | *required* |  |
| `is_opener` | `bool` | *required* |  |
| `offers_block` | `str` | *required* |  |
| `chat_enabled` | `bool` | *required* |  |
| `seat_index` | `int \| None` | `None` |  |
