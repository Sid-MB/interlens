# `RefusalLadder`

A fixed, seeded sequence of content-preserving re-renders, tried in order after a refusal.

```python
RefusalLadder(
	rungs: tuple[str, ...] = ('nonce', 'permute', 'reframe'),
	seed: int = 20260815,
	target_role: str = 'user',
)
```

Defined in [`interlens.arena.refusal`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/refusal.py#L96-L194)

:param rungs: The escalation order. Rungs are **cumulative** — rung *k* applies the perturbations of
    rungs 1..*k* — so each attempt is strictly further from the refused bytes than the last while staying
    content-preserving. The default ladder is:

    1. `"nonce"` — prepend one inert line naming a seeded variant tag. Adds no number and no instruction;
       its only job is to make the request bytes differ from the refused ones.
    2. `"permute"` — reorder the view's independent top-level blocks under a seeded permutation, holding
       the first block (the turn's own header) and the last block (the single closing ask) in place, since
       those two carry position-dependent meaning and the interior sections do not.
    3. `"reframe"` — re-wrap markdown section headings in an alternate but fixed framing
       (`## Catalogue` becomes `### Section: Catalogue`). Heading *text* and every body line are
       untouched.

:param seed: Ladder-level seed mixed into every per-turn permutation, so the whole campaign's re-renders
    replay exactly from the run manifest.
:param target_role: Which message of the view is perturbed. `"user"` (the default) is the measured one:
    in the auction pilot a line prepended to the user turn cleared a refusal 2/2 while the same line on the
    system prompt did not.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rungs` | `tuple[str, ...]` | `('nonce', 'permute', 'reframe')` |  |
| `seed` | `int` | `20260815` |  |
| `target_role` | `str` | `'user'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `rungs` | `tuple[str, ...]` |  |
| `seed` | `int` |  |
| `target_role` | `str` |  |

## Methods {#methods}

## `perturb` {#perturb}

```python
perturb(self, view: list[dict], rung: int, *, key: str) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/refusal.py#L170-L194)

The view re-rendered at rung *k* (1-based, cumulative).

Returns a new list; `view` is untouched.

:param view: The refused request's view — a list of `{"role", "content"}` messages.
:param rung: Which rung to render, 1-based; `rung > len(self)` raises.
:param key: The per-turn key the seeded perturbations hang off, e.g.
    `f"{episode_id}/{seat}/{round}/{phase}"`. Identical inputs give identical bytes, which is what
    makes a recovered turn reproducible from the episode record.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` | `list[dict]` | *required* |  |
| `rung` | `int` | *required* |  |
| `key` | `str` | *required* |  |

## `rung_name` {#rung_name}

```python
rung_name(self, rung: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/refusal.py#L127-L129)

The name of rung *k* (1-based), for logging.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rung` | `int` | *required* |  |
