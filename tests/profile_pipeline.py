"""Profile where wall-time actually goes in a captured generation turn, to decide whether the activation
offload (and its detok/retok neighbors) are worth optimizing vs. the forward passes.

Breaks one representative turn into: chat-template render, CPU tokenize, H2D copy, model.generate (the
generation forward), decode (D2H + detok), and the SEPARATE capture forward pass — with the capture pass further
split into forward-compute vs. GPU->CPU offload. Also compares three offload strategies:
  (a) current: per-record blocking .to('cpu') into pageable memory
  (b) batched: torch.stack the layers, one D2H copy
  (c) batched + pinned host buffer + non_blocking=True

Run on a GPU node (see profile_pipeline.sbatch). All timings are medians over N reps, CUDA-synchronized.

Usage:
    uv run python -m tests.profile_pipeline --model qwen2.5-3b --prompt-tokens 1024 --new-tokens 128 --reps 5
"""
from __future__ import annotations

import argparse
import statistics
import time

import torch

from interlens.loading import load_model
from interlens.interp.capture import capture_activations
from interlens.interp.activation_cache import CaptureSpec


def _sync():
	if torch.cuda.is_available():
		torch.cuda.synchronize()


def _timed(fn, reps: int) -> float:
	"""Median wall-seconds of ``fn`` over ``reps``, CUDA-synchronized around each call."""
	samples = []
	for _ in range(reps):
		_sync()
		t0 = time.perf_counter()
		fn()
		_sync()
		samples.append(time.perf_counter() - t0)
	return statistics.median(samples)


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--model", default="qwen2.5-3b", help="Short name or HF id to profile (a mid-size model is representative of the hot loop).")
	ap.add_argument("--prompt-tokens", type=int, default=1024, help="Synthetic prompt length in tokens (approximates a multi-turn transcript).")
	ap.add_argument("--new-tokens", type=int, default=128, help="max_new_tokens for the generation forward.")
	ap.add_argument("--reps", type=int, default=5, help="Repetitions per measurement; the median is reported.")
	ap.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float16", "float32"], help="Model dtype.")
	args = ap.parse_args()

	dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[args.dtype]
	device = "cuda" if torch.cuda.is_available() else "cpu"
	print(f"[invocation] model={args.model} prompt_tokens={args.prompt_tokens} new_tokens={args.new_tokens} reps={args.reps} dtype={args.dtype} device={device}", flush=True)

	model, tok = load_model(args.model, device=device, dtype=dtype)
	n_layers = model.config.num_hidden_layers
	print(f"[model] layers={n_layers} d_model={model.config.hidden_size} resolved_attn={getattr(model, '_resolved_attn', '?')}", flush=True)

	# Synthetic prompt of the requested token length (repeat a token, then wrap as one user turn's ids).
	base = tok("The quick brown fox jumps over the lazy dog. ", return_tensors="pt", add_special_tokens=False)["input_ids"]
	reps_needed = (args.prompt_tokens // base.shape[1]) + 1
	input_ids = base.repeat(1, reps_needed)[:, : args.prompt_tokens].to(device)
	prompt_text = tok.decode(input_ids[0], skip_special_tokens=True)
	gen_kwargs = dict(max_new_tokens=args.new_tokens, do_sample=True, temperature=0.8, top_p=0.95, pad_token_id=tok.pad_token_id)

	# --- warmup (kernels, autotune, allocator) ---
	with torch.inference_mode():
		model.generate(input_ids=input_ids, **gen_kwargs)
	_sync()

	results: dict[str, float] = {}

	# 1) CPU tokenize of the prompt text.
	results["tokenize (CPU)"] = _timed(lambda: tok(prompt_text, return_tensors="pt", add_special_tokens=False), args.reps)

	# 2) H2D copy of input_ids.
	cpu_ids = tok(prompt_text, return_tensors="pt", add_special_tokens=False)["input_ids"]
	results["H2D input_ids"] = _timed(lambda: cpu_ids.to(device), args.reps)

	# 3) generation forward (prefill + decode).
	def _gen():
		with torch.inference_mode():
			return model.generate(input_ids=input_ids, **gen_kwargs)
	results["model.generate"] = _timed(_gen, args.reps)

	# produce a realistic full sequence for decode + capture timing
	with torch.inference_mode():
		full = model.generate(input_ids=input_ids, **gen_kwargs)
	new_ids = full[0, input_ids.shape[1]:].contiguous()

	# 4) decode (D2H + detok) of the generated tokens.
	results["decode (D2H+detok)"] = _timed(lambda: tok.decode(new_ids, skip_special_tokens=True), args.reps)

	# 5) capture: the SEPARATE forward pass over the full sequence (residual, all layers), offload=None (no transfer).
	spec_gpu = CaptureSpec(sites=("residual",), layers=None, offload=None)
	def _capture_forward():
		with torch.inference_mode():
			return capture_activations(model, full, spec_gpu)
	results["capture forward (all layers, no offload)"] = _timed(_capture_forward, args.reps)

	# Grab one capture result set to profile offload strategies (tensors are [seq, d_model] on GPU).
	with torch.inference_mode():
		captured = capture_activations(model, full, spec_gpu)
	tensors = [t for (_li, _site, t) in captured]
	total_mb = sum(t.numel() * t.element_size() for t in tensors) / 1e6
	print(f"[capture] {len(tensors)} tensors, {total_mb:.1f} MB total on GPU", flush=True)

	# 6a) offload current: per-record blocking .to('cpu') into pageable memory.
	def _offload_per_record():
		return [t.detach().to("cpu") for t in tensors]
	results["offload (a) per-record blocking"] = _timed(_offload_per_record, args.reps)

	# 6b) offload batched: stack -> single D2H -> split.
	def _offload_batched():
		stacked = torch.stack(tensors)          # [L, seq, d]
		host = stacked.to("cpu")
		return list(host.unbind(0))
	results["offload (b) batched single D2H"] = _timed(_offload_batched, args.reps)

	# 6c) offload batched + pinned host buffer + non_blocking.
	L = len(tensors)
	pinned = torch.empty((L, *tensors[0].shape), dtype=tensors[0].dtype, device="cpu").pin_memory()
	def _offload_pinned():
		stacked = torch.stack(tensors)          # [L, seq, d]
		pinned.copy_(stacked, non_blocking=True)
		_sync()
		return list(pinned.unbind(0))
	results["offload (c) batched pinned non_blocking"] = _timed(_offload_pinned, args.reps)

	# --- report ---
	print("\n==================== PROFILE (median seconds) ====================", flush=True)
	width = max(len(k) for k in results)
	for k, v in results.items():
		print(f"  {k.ljust(width)} : {v * 1e3:9.3f} ms", flush=True)

	turn = results["tokenize (CPU)"] + results["H2D input_ids"] + results["model.generate"] + results["decode (D2H+detok)"]
	print(f"\n  [derived] uncaptured turn total (tok+H2D+generate+decode) : {turn*1e3:.2f} ms", flush=True)
	print(f"  [derived] generate share of turn                          : {results['model.generate']/turn*100:.1f}%", flush=True)
	print(f"  [derived] tokenize+decode share of turn                   : {(results['tokenize (CPU)']+results['decode (D2H+detok)'])/turn*100:.1f}%", flush=True)
	cap_fwd = results["capture forward (all layers, no offload)"]
	print(f"  [derived] capture forward vs generate                     : {cap_fwd/results['model.generate']*100:.1f}% of a generate", flush=True)
	off_a = results["offload (a) per-record blocking"]
	off_c = results["offload (c) batched pinned non_blocking"]
	print(f"  [derived] offload (c) speedup over (a)                    : {off_a/off_c:.2f}x", flush=True)
	print(f"  [derived] offload (a) vs capture forward                  : {off_a/cap_fwd*100:.1f}% of the capture pass", flush=True)


if __name__ == "__main__":
	main()
