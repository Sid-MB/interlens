# `message_token_spans`

Token span `(start, end)` of each message of `view` in the fully-rendered chat-template sequence.

```python
message_token_spans(
	tokenizer: 'PreTrainedTokenizerBase',
	view: list[dict],
) -> list[tuple[int, int]]
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L254-L283)

Method: render the *string* prefixes `apply_chat_template(view[:i], tokenize=False)` for each `i` and
require each to be a string-prefix of the next (raised on non-prefix-stable templates). The full string is
then tokenized **once** with `return_offsets_mapping=True` and each char boundary is mapped to the first
token whose offset starts at/after it — prefix *strings* are never tokenized independently, because a
tokenization of a prefix string is not in general a prefix of the full tokenization.

Note this describes the final replayed view (the whole conversation templated once). Live generation builds
the sequence incrementally, but for standard chat templates the rendered text is identical, so spans match.
The returned spans cover each message's rendered chunk *including* its role header/footer markup.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tokenizer` | `'PreTrainedTokenizerBase'` | *required* |  |
| `view` | `list[dict]` | *required* |  |
