# Interlens: Framework for Multi-Agent Interaction and Interpretability

This library provides a harness, optimized utilities, and interpretability hooks for multi-agent conversation rollouts. 

A harness for **multi-agent (model-to-model) conversations** with **first-class interpretability**—activation capture, steering, activation patching, and token logprobs—all hooked into the *same* generation path as real turns and tagged to conversation structure. Scales from one interactive dialogue to thousands of checkpointed, multi-GPU rollouts.

```python
from interlens import Conversation

conv = Conversation.from_models(
    ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-0.5B-Instruct"), names=("alice", "bob"),
    shared_context="Let's debate: is cereal a soup?",
)
conv.run(turns=4, first="alice")
print(conv.transcript)
```

See [`docs/examples`](docs/examples) for sample code.

## Install

```bash
pip install interlens
# with hosted-API participants (APIParticipant):
pip install "interlens[api]"
```

### PyTorch / CUDA note
`torch` is declared as a plain, build-agnostic dependency — install the wheel matching **your** platform (CUDA / CPU / MPS) *before or alongside* `interlens`. E.g. for CUDA 13.0:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu130
```
See <https://pytorch.org/get-started/locally/>.

## What's inside

- **`Conversation`** — turn-taking over a shared, perspective-neutral `Transcript`; per-speaker view pipeline (system/private framing → context-fit → family-correct chat template).
- **`AutoModelParticipant`** — HF-style factory (`from_pretrained` / `from_model` / `from_`) that returns the family-correct participant (Qwen/Gemma/…); **`APIParticipant`** for hosted models.
- **Interpretability** — `conv.capture(...)`, `SteeringSpec`, `Patch`, `token_logprobs`, backed by a queryable `ActivationCache`.
- **Scale** — `rollout` / `run_conversations`: multi-GPU, checkpointed, resumable, batched co-stepping, with in-worker `analyze` callbacks.
- **Serialization** — `ConversationTemplate` (recipe) and full save/load (template + transcript).

See [`docs/examples/`](docs/examples/) for a simple→advanced walkthrough of the whole API.

## Develop

```bash
git clone https://github.com/Sid-MB/interlens && cd interlens
pip install -e ".[dev]"
pytest                      
# fast tests; opt-in to thorough tests requiring downloading models + a GPU with: pytest -m slow
```

## License

GNU AGPLv3 — see [LICENSE](LICENSE).
