# interlens examples

Runnable, self-contained scripts (as opposed to the prose walkthroughs under [`docs/examples/`](../docs/examples/)). Each is invoked directly and documents its flags via `--help`.

| Example | What it shows |
| --- | --- |
| [`gsm8k_benchmark_rollout.py`](gsm8k_benchmark_rollout.py) | Evaluate a **collaborative solver/critic conversation on a real benchmark** (GSM8K): ONE data-parameterized `Conversation` (`dataset_field` templates the question) expanded to one conversation per problem via `.data(...).rollout()`, graded in an `analyzer`, run with default multi-GPU + batched co-stepping. |

```bash
python examples/gsm8k_benchmark_rollout.py --n 50 --turns 3        # local model on one GPU
python examples/gsm8k_benchmark_rollout.py --help                  # all flags
```

To evaluate a **hosted** model instead, edit `build_conversation` to use `APIParticipant`s (set `batch=True` to route through the provider's async batch API — anthropic/openai only). See [`docs/examples/08_rollouts_and_scale.md`](../docs/examples/08_rollouts_and_scale.md).
