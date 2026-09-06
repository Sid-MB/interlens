# `functional`

Module `interlens.functional`

Copy-on-write functional-update support shared by `Participant` and `Conversation`.

Both are dataclasses that the user builds up incrementally (`conv.turns(6).data(ds).analyzer(grade)`) and
replicates cheaply (one recipe → N per-row copies in a rollout). The `Functional` mixin gives them a single
uniform update primitive — `obj.set(**changes) -> new obj` — plus optional per-field *dot-modifier sugar*
(`conv.turns(6)`) that reads with no argument and returns a modified copy with one.

Why `copy.copy` + an explicit `_after_set` hook rather than `dataclasses.replace`: a live participant
carries heavy shared state (the loaded `_model`/`_tokenizer`) and volatile per-conversation state (KV cache,
a pending capture). We want the copy to **share** the heavy objects by reference (zero GPU cost — the whole point
of copy-on-write here) but start with **fresh** volatile state. `copy.copy` shallow-copies the instance dict
(so heavy refs are shared automatically) and, crucially, does NOT re-run `__init__`/`__post_init__` (which for
a participant would try to re-derive device from the model, and for a conversation would re-seed/re-validate),
leaving us to reset exactly the volatile fields in `_after_set`. The result is precise control over what is
shared vs. what is reset — which `replace` cannot express when the sharing/reset split cuts across init and
non-init state.

## Classes

| Name | Summary |
|---|---|
| [`Functional`](Functional.md) | Mixin giving a dataclass copy-on-write updates via `set(**changes)`. |

## Functions

| Name | Summary |
|---|---|
| [`sugar_fields`](sugar_fields.md) | Class decorator declaring copy-on-write dot-modifier sugar for `names`. |
