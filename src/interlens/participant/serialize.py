# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Persist a participant to / from its own constructor kwargs (for ``Conversation.save`` / ``load``).

This is same-type persistence — a participant serializes the recipe it was built from (an HF id + generation
settings, or an API provider + model id) and rebuilds an *equivalent lazy* participant. It is NOT a conversion to
a separate config type (participants ARE their own recipe now); weights are never serialized and reload lazily on
the target device. ``private_context`` (``ContextItem``s) is inlined; local tools are stored by name and
re-resolved from the tool registry on load."""
from __future__ import annotations

from ..context_item import ContextItem


def participant_to_dict(p) -> dict:
	"""Serialize participant ``p`` to a plain dict of its constructor kwargs (no weights). Dispatches on the
	participant kind via duck-typed attributes (a local model participant has ``hf_id``; an API one has
	``provider``)."""
	base = {
		"name": p.name,
		"system_prompt": p.system_prompt,
		"private_context": [{"content": c.content, "role_hint": c.role_hint, "author": c.author}
		                    for c in p.private_context],
		"self_role": p.self_role,
		"others_role": p.others_role,
	}
	if hasattr(p, "hf_id"):  # local ModelParticipant
		base.update(kind="model", hf_id=p.hf_id, weights_path=p.weights_path, dtype=p.dtype, attn=p.attn,
		            quant=p.quant, revision=p.revision, max_new_tokens=p.max_new_tokens, temperature=p.temperature,
		            top_p=p.top_p, seed=p.seed, thinking=p.thinking, tool_names=[t.name for t in p.tools],
		            max_tool_iters=p.max_tool_iters, kv_reuse=p.kv_reuse)
	else:  # APIParticipant
		base.update(kind="api", model_id=p.model_id, provider=p.provider, max_tokens=p.max_tokens,
		            temperature=p.temperature, batch=p.batch)
	return base


def participant_from_dict(data: dict, device="cuda", registry=None):
	"""Rebuild a (lazy) participant from :func:`participant_to_dict` output. Local models resolve their family class
	from the HF config and load lazily on ``device``; API participants are reconstructed directly."""
	private_context = tuple(ContextItem(c["content"], c.get("role_hint", "user"), c.get("author", "moderator"))
	                        for c in data.get("private_context", []))
	if data["kind"] == "model":
		from ..factories import AutoModelParticipant
		tools = ()
		if data.get("tool_names"):
			from ..tools.registry import DEFAULT_REGISTRY
			tools = tuple((registry or DEFAULT_REGISTRY).resolve(tuple(data["tool_names"])))
		return AutoModelParticipant.from_pretrained(
			data["hf_id"], name=data["name"], device=device,
			load_kwargs={"dtype": data.get("dtype", "bfloat16"), "attn": data.get("attn", "flash_attention_2"),
			             "quant": data.get("quant"), "revision": data.get("revision"),
			             "weights_path": data.get("weights_path")},
			system_prompt=data.get("system_prompt"), private_context=private_context,
			max_new_tokens=data.get("max_new_tokens", 512), temperature=data.get("temperature", 0.8),
			top_p=data.get("top_p", 0.95), seed=data.get("seed"), thinking=data.get("thinking", "auto"),
			tools=tools, max_tool_iters=data.get("max_tool_iters", 4), kv_reuse=data.get("kv_reuse", "auto"))
	if data["kind"] == "api":
		from .participants.api_participant import APIParticipant
		return APIParticipant(name=data["name"], system_prompt=data.get("system_prompt"),
		                      private_context=private_context, model_id=data["model_id"],
		                      provider=data.get("provider", "anthropic"), max_tokens=data.get("max_tokens", 512),
		                      temperature=data.get("temperature", 1.0), batch=data.get("batch", False))
	raise ValueError(f"unknown participant kind {data.get('kind')!r}")
