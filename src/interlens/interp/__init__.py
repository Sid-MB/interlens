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
]
