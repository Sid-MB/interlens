# `interlens.templating`

Per-row templating for data-driven rollouts.

A `Conversation` run over a benchmark shares ONE recipe but needs a DIFFERENT scenario per dataset row. Any
templated string field on the conversation (`shared_context`, `shared_system_prompt`) or its participants
(`system_prompt`, private context) may be a *template value* that is resolved against each row at rollout
expansion time (once, deterministically — so job *i* always maps to row *i* and resume stays correct).

A template value is any of:
  - a plain `str` — used as-is (no substitution);
  - `dataset_field("question")` — pulls `row["question"]`;
  - a `callable(row) -> str` — arbitrary per-row computation;
  - a `tuple`/`list` of the above — resolved part-by-part and concatenated (the <3.14 way to interleave
    literal text with fields: `("Solve:\n\n", dataset_field("question"))`);
  - a PEP 750 template string (`t"...{dataset_field('question')}..."`) on Python 3.14+ — interpolated
    `DatasetField`s resolve from the row, everything else formats normally.

`resolve(value, row)` performs the substitution; `has_fields(value)` reports whether a value depends on the
row at all (so a conversation with no data-dependent fields can be run directly, and one WITH them refuses to run
un-expanded — see `Conversation`).

## Classes

| Name | Summary |
|---|---|
| [`DatasetField`](DatasetField.md) | A placeholder for `row[name]` in a templated field, created by :func:`dataset_field`. |

## Functions

| Name | Summary |
|---|---|
| [`dataset_field`](dataset_field.md) | Reference a dataset column in a templated field: `shared_context=("Solve:\n\n", dataset_field("question"))` resolves `row["question"]` for each row at rollout expansion. |
| [`has_fields`](has_fields.md) | Whether `value` depends on the dataset row (contains a `DatasetField`, a callable, or a t-string). |
| [`resolve`](resolve.md) | Resolve a template `value` against one dataset `row` (a mapping) to a concrete value. |
