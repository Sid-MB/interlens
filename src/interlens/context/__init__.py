from .context_policy import ContextPolicy
from .error_policy import ErrorPolicy
from .drop_oldest_policy import DropOldestPolicy
from .sliding_window_policy import SlidingWindowPolicy
from .summarize_policy import SummarizePolicy

# Registry for (de)serializing policies by ``kind`` (their class name), so templates round-trip.
_POLICIES = {c.__name__: c for c in (ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy)}


def context_policy_from_dict(data: dict) -> ContextPolicy:
	params = {k: v for k, v in data.items() if k != "kind"}
	return _POLICIES[data["kind"]](**params)


__all__ = [
	"ContextPolicy",
	"ErrorPolicy",
	"DropOldestPolicy",
	"SlidingWindowPolicy",
	"SummarizePolicy",
	"context_policy_from_dict",
]
