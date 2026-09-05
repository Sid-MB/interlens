# `register_worker_init`

Register a zero-arg callable to run once at worker startup (e.g. to populate the tool/analyzer registries).

```python
register_worker_init(fn) -> object
```

Defined in [`interlens.runner.worker_init`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/worker_init.py#L25-L28)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `fn` |  | *required* |  |
