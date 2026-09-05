# `RunReport`

Aggregate outcome of a run.

```python
RunReport(results: dict = dict(), skipped: list = list())
```

Defined in [`interlens.runner.pool`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L55-L74)

Failures are isolated, not fatal: `results` holds every attempted job,
`failed` lists the ones that errored, `skipped` lists resume-skipped (already-checkpointed) ids.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `results` | `dict` | `dict()` |  |
| `skipped` | `list` | `list()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `failed` | `list` |  |
| `results` | `dict` |  |
| `skipped` | `list` |  |

## Methods {#methods}

## `analyses` {#analyses}

```python
analyses(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L70-L71)

## `conversations` {#conversations}

```python
conversations(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L73-L74)

## `transcripts` {#transcripts}

```python
transcripts(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L67-L68)
