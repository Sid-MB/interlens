# `PromptCache`

Where to put a request's `cache_control` breakpoints — Anthropic only.

```python
PromptCache(system: bool = True, marks: tuple[str, ...] = (), ttl: str = '5m')
```

Defined in [`interlens.participant.participants.api_participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L94-L152)

Caching is a **prefix** match: the cache key is the exact bytes up to each breakpoint, in the provider's
render order (`tools` → `system` → `messages`), so any byte that changes early invalidates everything
after it. This spec therefore describes *stability boundaries*, not "cache these strings".

:param system: Put a breakpoint at the end of the system prompt (default on). This is the one boundary every
        multi-turn scenario has for free: a seat's system prompt is fixed for its whole episode, and it renders
        before any message, so one breakpoint there caches the framing of every later turn.
:param marks: Literal substrings of the LAST user message, in the order they appear. The text *before* each
        mark's first occurrence ends a cached prefix, so a scenario that renders its turn view as stable
        sections followed by volatile ones (a catalogue and a history digest, then this turn's private state and
        ask) gets those sections cached by naming the headings that follow them. Splitting is byte-preserving —
        the concatenated blocks are the original message — so the model reads exactly what it read uncached, and
        the refusal ladder and stored `view` are untouched. A mark that does not occur is skipped rather than
        raising, because a view legitimately varies by phase.
:param ttl: `"5m"` (default) or `"1h"`. A write costs 1.25x the input rate at 5m and 2x at 1h, against
        0.1x for a read, so 5m breaks even on the second request and 1h on the third. Prefer `"1h"` only when
        a seat's turns are more than five minutes apart — which wave-parallel generation is specifically
        designed to stop being true.

Breakpoints are capped at :data:`MAX_CACHE_BREAKPOINTS`; `system` consumes one, so at most three marks
take effect and the rest are ignored. {note}

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `system` | `bool` | `True` |  |
| `marks` | `tuple[str, ...]` | `()` |  |
| `ttl` | `str` | `'5m'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `marks` | `tuple[str, ...]` |  |
| `system` | `bool` |  |
| `ttl` | `str` |  |

## Methods {#methods}

## `control` {#control}

```python
control(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L129-L131)

The `cache_control` value one breakpoint carries.

## `split` {#split}

```python
split(self, text: str) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L133-L152)

`text` as Anthropic text blocks with a breakpoint before each of :attr:`marks`.

Concatenating the blocks' `text` reproduces `text` exactly. The final block never carries a
breakpoint: it is the volatile tail, and marking it would write a fresh cache entry per turn that is
never read — the failure that reports as "caching is on and saving nothing".

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
