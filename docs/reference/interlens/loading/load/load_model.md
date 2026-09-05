# `load_model`

Load a causal LM + tokenizer, sharing through the process-local caches.

```python
load_model(
	id_or_path: str | Path,
	device: str | torch.device = 'cuda',
	dtype: torch.dtype = torch.bfloat16,
	attn: str = 'flash_attention_2',
	quant: str | None = None,
	revision: str | None = None,
	max_memory: dict | None = None,
)
```

Defined in [`interlens.loading.load`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/load.py#L117-L171)

`id_or_path` is the HF id or a local path to load directly (a `Path` is normalized to `str` so it shares
the same cache slot as its string form). Identical (hf_id, device, dtype, attn, quant, revision, max_memory)
pairings share the one model object, and the tokenizer is cached by hf_id. Flash-attention is the default with
automatic fallback to sdpa/eager; quantization is opt-in.

**Returns**

| Name | Type | Description |
|---|---|---|
|  |  | `(model, tokenizer)`. On a sharded load, place inputs with |
|  |  | func:`~interlens.loading.devices.input_device` rather than `model.device`. |

**Example**

>>> model, tok = load_model("Qwen/Qwen3-8B")                       # single GPU, bf16, flash-attn
>>> model, tok = load_model("Qwen/Qwen3-32B", device="balanced",   # two cards, KV headroom reserved
...                         max_memory={0: "70GiB", 1: "70GiB", "cpu": "0GiB"})

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `id_or_path` | `str \| Path` | *required* | HF hub id or a local directory of weights. |
| `device` | `str \| torch.device` | `'cuda'` | either a single placement (`"cuda"`, `"cuda:1"`, `"cpu"`, a `torch.device` — the default, loaded then moved) or a **sharding strategy** handed to `device_map=`: `"auto"` (fill each visible GPU in turn, then cpu/disk), `"balanced"` (even split over GPUs), `"balanced_low_0"` (leave headroom on GPU 0 for generation buffers), `"sequential"`, or an explicit `{module_name: device}` map. Use a strategy when the weights do not fit one card — e.g. a 32B policy on two 80 GB GPUs; use the single-device default whenever they do, since sharding adds cross-device transfers to every forward. |
| `dtype` | `torch.dtype` | `torch.bfloat16` | parameter dtype; `bfloat16` is the default and what every evaluation in this library assumes. |
| `attn` | `str` | `'flash_attention_2'` | preferred attention backend, tried first and then degraded through `sdpa` and `eager`, so `flash_attention_2` is safe to leave on hardware/builds that lack it. |
| `quant` | `str \| None` | `None` | `None` (full precision — required for faithful interpretability, since quantization perturbs the very activations a probe reads), `"4bit"` or `"8bit"` via BitsAndBytes when memory forces it. Quantized loads place themselves and are never `.to()`'d. |
| `revision` | `str \| None` | `None` | pin a specific hub commit/branch/tag; `None` takes the default branch. |
| `max_memory` | `dict \| None` | `None` | per-device budget for a `device_map` strategy, e.g. `{0: "70GiB", 1: "70GiB", "cpu": "0GiB"}`. Use it to reserve headroom for KV cache and activations, which the automatic map does not know about, or to forbid cpu offload (an `"0GiB"` cpu entry turns a silent 100x slowdown into an out-of-memory error you can act on). Ignored without a strategy. |
