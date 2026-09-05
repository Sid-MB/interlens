# `interlens.parsing`

One home for structured-action parsing and reasoning stripping.

Three call sites historically each carried their own copy of this logic — the arena's `extract_json` /
`strip_think` (`arena/views.py`), the messaging policy's `parse_json_actions`
(`communication/messaging.py`), and the model participant's `parse_tool_calls` / `split_reasoning`
(`model_participant.py`) — with subtly divergent regexes and edge-case handling. They now all call the one
implementation here; the original names survive as thin shims so their signatures stay stable.

Two orthogonal jobs:

- **Fenced / tagged JSON extraction** — pulling structured actions out of a model's free text, whether they
  arrive as ```` ```json {...} ```` fences (the family-agnostic action surface) or `<tag>{...}</tag>` blocks
  (Hermes/Qwen tool calls). Malformed JSON is skipped, never fatal.
- **Reasoning stripping** — separating a `<think>...</think>` stream from the visible content, in two
  flavours: a strict *leading-block* split (the participant's own completion, where reasoning is a prefix) and
  a *strip-anywhere* pass (a defensive re-strip before content reaches another seat's view, robust to a
  generation truncated mid-`<think>`).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `FENCE_RE` |  |  |
| `LEADING_THINK_RE` |  |  |
| `THINK_BLOCK_RE` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`first_think_block`](first_think_block.md) | The first complete `<think>...</think>` block's inner reasoning, or `None`. |
| [`iter_fenced_json`](iter_fenced_json.md) | Every parseable fenced JSON OBJECT in `text`, in order (malformed fences skipped, not fatal). |
| [`iter_tagged_json`](iter_tagged_json.md) | Every `<tag>{json}</tag>` block in `text` as `(parsed_object, raw_match)` pairs (malformed JSON skipped). |
| [`last_json`](last_json.md) | The LAST fenced JSON object in `text`, else the last balanced top-level `{...}` that parses, else `None`. "Last wins" because a model's final fenced block is its committed action when it revised mid-turn. |
| [`last_json_with_key`](last_json_with_key.md) | The LAST fenced JSON OBJECT in `text` carrying at least one of `keys` at top level, else `None`. |
| [`split_leading_think`](split_leading_think.md) | Split a raw completion into `(visible_content, parsed_think)` on a LEADING `<think>...</think>` block only (the participant-level convention). |
| [`strip_think`](strip_think.md) | Remove `<think>...</think>` blocks ANYWHERE in `text`; return `(visible, think)`. |
