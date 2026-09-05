# `Functional`

Mixin giving a dataclass copy-on-write updates via `set(**changes)`.

```python
Functional()
```

Defined in [`interlens.functional`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/functional.py#L86-L131)

`set` shallow-copies the instance (heavy refs like a loaded model are shared, not reloaded), applies the
changes, then calls `_after_set` to reset volatile per-instance state on the copy. Sugared field names
(declared via `sugar_fields`) are accepted under their public spelling and routed to their `_`-prefixed
storage. Unknown fields raise `TypeError`. The original is never mutated.

## Methods {#methods}

## `set` {#set}

```python
set(self, **changes={})
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/functional.py#L96-L113)

Return a modified shallow copy: the same object with `changes` applied and volatile state reset.

The
receiver is untouched (copy-on-write); heavy state (a loaded model, an API client) is shared by reference.
Unknown field names raise `TypeError`.

The copy is a raw instance-dict clone (NOT `copy.copy`), so it deliberately bypasses `__getstate__` —
which exists to DROP the loaded model/client on *pickle* (spawn boundary). A `.set()` clone, by contrast,
is in-process and must KEEP those shared references (that is the whole point of copy-on-write here).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `changes` |  | `{}` |  |
