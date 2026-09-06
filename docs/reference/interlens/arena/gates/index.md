# `gates`

Module `interlens.arena.gates`

Template-fidelity gates: preflight checks before spending GPU-hours on local-model rollouts.

Two silent failure modes cost real runs in the arena experiments, and both are cheap to gate on:

1. **Template drift** — the token ids a model is *actually* conditioned on
   (`apply_chat_template(tokenize=True)`) can differ from tokenizing the rendered string, e.g. when a
   template inserts special tokens the string round-trip re-splits. `check_template_fidelity` asserts exact
   token-id equality over real rendered multi-party views, for the exact id path batched generation feeds to
   `generate`.
2. **Reasoning leaks** — a `<think>` block from one seat's raw completion ending up inside another seat's
   later view (observed live when a turn truncates mid-`<think>`). `check_reasoning_leak` scans a played
   episode for any raw think fragment appearing in a later turn's visible content.

Run both on smoke instances before a full rollout; each returns a report dict with `ok: bool`.

## Functions

| Name | Summary |
|---|---|
| [`check_reasoning_leak`](check_reasoning_leak.md) | Scan a played episode for reasoning leakage: any turn whose raw completion contains a `<think>` block whose content then appears verbatim in a LATER turn's visible content (meaning another seat saw it). |
| [`check_template_fidelity`](check_template_fidelity.md) | Assert token-id equality between `tokenizer(apply_chat_template(tokenize=False))` and `apply_chat_template(tokenize=True)` for every view. |
| [`scenario_smoke_views`](scenario_smoke_views.md) | Real rendered views for gating: a fresh team state's first requests, plus the views after one scripted turn (so later views carry assistant/user mixes, which is where templates diverge). |
