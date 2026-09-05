# `run_tests`

Run test_src against code_str (as `solution`) in an isolated sandbox.

```python
run_tests(code_str: str, test_src: str) -> tuple[int, int]
```

Defined in [`interlens.arena.scenarios.coding`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L531-L551)

Fresh tmpdir, [sys.executable, -I, -m, pytest, testfile, -q], cwd=tmpdir,
subprocess timeout 30s. Total is estimated by counting 'def test_' in
test_src; crash/timeout/unparseable output -> (0, total).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `code_str` | `str` | *required* |  |
| `test_src` | `str` | *required* |  |
