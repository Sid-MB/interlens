# `VirtualTokenInjector`

Reserve `n_soft` positions in a *text* prompt and substitute their input embeddings at forward time.

```python
VirtualTokenInjector(
	tokenizer: 'PreTrainedTokenizerBase',
	n_soft: int,
	placeholder: str | None = None,
)
```

Defined in [`interlens.interp.softtokens`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/softtokens.py#L71-L223)

Construction picks (and validates) a `placeholder` token from `tokenizer`'s existing vocabulary — no
`add_special_tokens`, no `resize_token_embeddings`, so the model is untouched and any checkpoint stays
loadable. Validation is empirical, not assumed: the candidate must (a) tokenize, repeated `n_soft` times with
no separator, to exactly `n_soft` copies of its own id, and (b) survive `apply_chat_template` — rendered
inside a user message the run must still appear exactly once, contiguous, at length `n_soft`. Templates that
escape or normalize the candidate are rejected and the next candidate is tried.

Use :attr:`text` as the snippet to splice into your prompt string, then wrap the forward/generate call in
:meth:`inject` (or register/remove hooks yourself with :meth:`register`, the `SteeringSpec.register`
convention).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tokenizer` | `'PreTrainedTokenizerBase'` | *required* |  |
| `n_soft` | `int` | *required* |  |
| `placeholder` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `n_soft` |  |  |
| `placeholder` |  |  |
| `text` | `str` | The snippet to render into a prompt: the placeholder token repeated `n_soft` times, no separators. |
| `token_id` |  |  |
| `tokenizer` |  |  |

## Methods {#methods}

## `inject` {#inject}

```python
inject(
	self,
	model: 'PreTrainedModel',
	vectors: torch.Tensor,
) -> Iterator['VirtualTokenInjector']
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/softtokens.py#L215-L223)

Context manager around :meth:`register`: hooks are removed on exit, including on exception.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
| `vectors` | `torch.Tensor` | *required* |  |

## `register` {#register}

```python
register(self, model: 'PreTrainedModel', vectors: torch.Tensor) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/softtokens.py#L175-L213)

Register the substitution hooks on `model` and return the handles (caller removes them; or use :meth:`inject`, which does that for you).

`vectors` is `[batch, n_soft, d_model]`, aligned row-for-row with the `input_ids` the model will see;
a `batch` of 1 is broadcast to every row. It is *not* detached and *not* copied into the graph in place,
so `loss.backward()` reaches it (and anything upstream, e.g. a `LinearBridge`). Rows whose ids contain
no placeholder keep their ordinary token embeddings.

Mechanics: a forward-**pre**-hook on `model.get_input_embeddings()` records the `input_ids` that call is
about to embed (the post-hook only sees the output), and the forward hook returns a modified clone with the
placeholder slice overwritten. Decode steps under a KV cache pass one non-placeholder token and are no-ops.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
| `vectors` | `torch.Tensor` | *required* |  |

## `run_starts` {#run_starts}

```python
run_starts(self, input_ids: torch.Tensor) -> list[int | None]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/softtokens.py#L153-L173)

Per batch row, the index where the placeholder run starts, or `None` if that row has no placeholders.

Raises if a row holds a partial or non-contiguous run — that means the prompt was built wrong (e.g. the
snippet got split by a template) and silently steering the wrong positions would be worse than failing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `input_ids` | `torch.Tensor` | *required* |  |
