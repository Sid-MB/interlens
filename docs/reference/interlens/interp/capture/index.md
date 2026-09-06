# `capture`

Module `interlens.interp.capture`

## Classes

| Name | Summary |
|---|---|
| [`CaptureRequest`](CaptureRequest.md) | A pending capture handed to `generate`: where to store records (`cache`) and what to grab (`spec`). |
| [`CapturedSite`](CapturedSite.md) | One activation captured by `capture_activations`: the `tensor` (`[seq, d_model]`) at a given `layer` and `site`. |

## Functions

| Name | Summary |
|---|---|
| [`capture_activations`](capture_activations.md) | Run one clean forward pass over `input_ids` and return `[(layer, site, tensor[seq, d_model])]`. |
