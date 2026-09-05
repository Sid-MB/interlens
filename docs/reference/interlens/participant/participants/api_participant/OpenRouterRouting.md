# `OpenRouterRouting`

Reproducible OpenRouter routing for research.

```python
OpenRouterRouting(
	upstream_provider: str | None,
	quantizations: tuple[OpenRouterQuantization, ...] = (),
	data_collection: Literal['allow', 'deny'] | None = None,
	allow_unpinned: bool = False,
)
```

Defined in [`interlens.participant.participants.api_participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L36-L83)

`upstream_provider` is the OpenRouter provider slug (for example `"together"` or `"deepinfra"`).
A pinned request sends both `only=[slug]` and `order=[slug]`, disables fallbacks, and requires support
for every supplied generation parameter. `quantizations` should also be set for open-weight models when
the endpoint offers multiple precisions. `data_collection="deny"` excludes providers that may retain or
train on prompts.

Use :meth:`unpinned` only for exploratory traffic where provider variance is intentionally acceptable.
Requiring that explicit opt-out prevents an uncontrolled request from looking like a reproducible run.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `upstream_provider` | `str \| None` | *required* |  |
| `quantizations` | `tuple[OpenRouterQuantization, ...]` | `()` |  |
| `data_collection` | `Literal['allow', 'deny'] \| None` | `None` |  |
| `allow_unpinned` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `allow_unpinned` | `bool` |  |
| `data_collection` | `Literal['allow', 'deny'] \| None` |  |
| `quantizations` | `tuple[OpenRouterQuantization, ...]` |  |
| `upstream_provider` | `str \| None` |  |

## Methods {#methods}

## `request_dict` {#request_dict}

```python
request_dict(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L74-L83)

Return the exact OpenRouter `provider` request object.

## `unpinned` {#unpinned}

```python
unpinned(
	cls,
	*,
	data_collection: Literal['allow', 'deny'] | None = None,
) -> 'OpenRouterRouting'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L69-L72)

Explicitly opt into OpenRouter's variable default provider routing for exploratory, non-reproducible use.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `data_collection` | `Literal['allow', 'deny'] \| None` | `None` |  |
