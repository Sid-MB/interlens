from __future__ import annotations

from dataclasses import dataclass

from ..template import ConversationTemplate


@dataclass
class ConversationSpec:
	"""A unit of work for the runner: a fully-serializable ``ConversationTemplate`` + a ``job_id`` + turn count.

	Being serializable is what lets a spec cross the process boundary to a spawned GPU worker. ``job_id`` keys
	results and the on-disk checkpoint directory, so a resumed run can tell which specs are already done.
	"""

	template: ConversationTemplate
	job_id: str
	turns: int | None = None

	def to_dict(self) -> dict:
		return {"template": self.template.to_dict(), "job_id": self.job_id, "turns": self.turns}

	@classmethod
	def from_dict(cls, data: dict) -> "ConversationSpec":
		return cls(template=ConversationTemplate.from_dict(data["template"]),
		           job_id=data["job_id"], turns=data.get("turns"))
