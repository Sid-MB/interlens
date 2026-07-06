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

"""First-class interpretability layer.

All four tools hook into the *same* generation path (real turns, ``sample``, and every generation inside the
future tool loop) and are tagged to conversation structure, so downstream consumers (logit lens, SAEs, probes,
CKA/Procrustes) read the ``ActivationCache`` via the raw-model escape hatch without any harness change.
"""

from .activation_cache import ActivationCache, CaptureSpec, ActivationRecord, OffloadLocation, Site, Phase
from .capture import capture_activations, CaptureRequest, CapturedSite
from .steering import SteeringSpec
from .logprobs import token_logprobs
from .patching import Patch
from .layers import decoder_layers
from .grad import GradCaptureSpec, GradForwardOutput, forward_with_grad, continuation_logprob
from .bridge import soft_embed, gumbel_softmax_tokens, LinearBridge
from .routing import (RoutingCapture, RoutingStats, RouterSteeringSpec, capture_router_logits, routing_stats,
                      message_token_spans, moe_num_experts, moe_topk, moe_layer_indices, kl_divergence,
                      js_divergence, topk_expert_overlap)

__all__ = [
	"ActivationCache",
	"CaptureSpec",
	"ActivationRecord",
	"OffloadLocation",
	"Site",
	"Phase",
	"CaptureRequest",
	"capture_activations",
	"CapturedSite",
	"SteeringSpec",
	"token_logprobs",
	"Patch",
	"decoder_layers",
	"GradCaptureSpec",
	"GradForwardOutput",
	"forward_with_grad",
	"continuation_logprob",
	"soft_embed",
	"gumbel_softmax_tokens",
	"LinearBridge",
	"RoutingCapture",
	"RoutingStats",
	"RouterSteeringSpec",
	"capture_router_logits",
	"routing_stats",
	"message_token_spans",
	"moe_num_experts",
	"moe_topk",
	"moe_layer_indices",
	"kl_divergence",
	"js_divergence",
	"topk_expert_overlap",
]
