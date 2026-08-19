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
#
# [implement: live-play/lane0] 2026-08-16
# [implement: live-play/lobby-defaults] 2026-08-19
"""The seam between the live server and whatever experiment supplies its games.

The server knows how to run a negotiation live — stream it, block a seat on a browser, swap an occupant — and
knows NOTHING about instance banks, framings, scaffolds, oracle stacks or which models an experiment can afford
to call. All of that enters through :class:`ScenarioProvider`, which the experiment implements (for the rational
agents work, ``experiments/rational_agents/live_play.py`` implements it over ``run.py``'s existing assembly
helpers).

That direction of dependency is the whole design: an experiment's scenario assembly is intricate, versioned and
changes with the research, and copying any of it into the library would create a second copy that goes stale.
The provider hands over already-assembled objects, so interlens never learns what a "framing" is.

Nothing here does any work. These are the shapes the four implementation lanes agree on.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Protocol

# What can sit in a seat. ``llm`` is a hosted or local model, ``rational``/``oracle`` are computable
# PolicyParticipants (private-information belief model vs full-information GameTables — the same policy zoo, the
# difference is what the seat is allowed to know), ``human`` is the browser, ``scripted`` is a fixed-string seat
# used for smoke tests and demos.
SEAT_KINDS = ("llm", "rational", "oracle", "human", "scripted")

#: Seat kind -> the prefix of its occupant label (``SeatConfig.occupant_label``). Two kinds are spelled by ROLE
#: rather than by kind: an ``llm`` seat is served over an API (``api:claude-fable-5``) and a ``rational`` seat by
#: a computable policy (``policy:bayes-rational``), which is the vocabulary the rest of the arena already uses.
#: A kind with no entry keeps its own name, so a new seat kind gets a sensible label before it gets a mapping.
_OCCUPANT_PREFIX = {"llm": "api", "rational": "policy"}

#: Thinking modes best-first: which mode a model seat takes when nobody has said. Extended thinking is on
#: WHEREVER the model accepts it, because a live game is watched rather than batched — a seat that reasons before
#: it moves is the interesting one, and the token cost of one hand-played game is not what a budget cap is for.
#: ``on`` (an explicit adaptive request) is preferred over ``auto`` (the model's own default, which happens to be
#: adaptive on current Claude models) so the episode RECORDS the condition it played under rather than leaving it
#: unset; ``off`` is last and is only ever chosen by a model that offers nothing else. A model's own
#: ``thinking_modes`` still decides — this is a preference order over that list, never an addition to it.
THINKING_PREFERENCE = ("on", "auto", "off")


def _attr(model: Any, key: str, fallback: Any = None) -> Any:
    """One field of a model description, whether it arrived as a :class:`ModelInfo` or as its ``to_json()`` dict.

    The lobby renders from the dicts (that is what crosses the wire) and the session validates against the
    objects, so the default-resolution helpers below have to read both or there would be two copies of the rule
    that disagree at exactly the moment they matter."""
    if isinstance(model, dict):
        value = model.get(key, fallback)
    else:
        value = getattr(model, key, fallback)
    return fallback if value is None else value


def default_thinking(model: Any) -> str:
    """The thinking mode a seat on this model starts in: the first of :data:`THINKING_PREFERENCE` the model
    accepts, falling back to its first declared mode if it accepts none of them (a provider free to invent mode
    names must still get a mode that model can take). ``model`` is a :class:`ModelInfo` or its wire dict; a
    missing model resolves to ``"off"``, the only mode every backend has."""
    modes = [str(m) for m in _attr(model, "thinking_modes", ()) or ()] if model else []
    if not modes:
        return "off"
    return next((m for m in THINKING_PREFERENCE if m in modes), modes[0])


def default_model_id(models: Any) -> str:
    """Which model a seat that has just become an ``llm`` seat is pre-selected to.

    The provider decides, by flagging one :class:`ModelInfo` with ``default=True`` — the lobby must not know the
    name of anybody's favourite model, and an id hardcoded in the page would be a second place to edit every time
    the frontier moves. Preference order, ties broken by list order: the flagged model if it can be used, then
    any model that can be used, then the flagged one anyway, then the first entry. Pre-selecting a model whose
    key is missing over one that would actually run is the one case where honouring the flag helps nobody, and
    the flag still wins when NOTHING is usable, so a lobby with no credential still opens on the right name (and
    on the "no Anthropic credential" reason next to it). ``""`` when there is nothing to offer.
    """
    entries = list(models or [])
    if not entries:
        return ""

    def rank(model: Any) -> int:
        flagged, usable = bool(_attr(model, "default", False)), bool(_attr(model, "available", True))
        return 0 if (flagged and usable) else 1 if usable else 2 if flagged else 3

    return str(_attr(min(entries, key=rank), "model_id", "") or "")


@dataclass
class ModelInfo:
    """One model the lobby may offer for an ``llm`` seat.

    Parameters
    ----------
    model_id : str
        The provider's id, exactly as a participant factory wants it (``"claude-fable-5"``, a HF repo id, ...).
    label : str
        What the lobby shows a human. Free text.
    provider : str
        Which backend serves it (``"anthropic"``, ``"openai"``, ``"local"``, ...) — drives the "needs an API key"
        warning and whether the seat is metered.
    thinking_modes : tuple[str, ...]
        The extended-thinking settings this model actually accepts, in the order the lobby should show them
        (e.g. ``("off", "on")``, or ``("on",)`` for a model that cannot turn thinking off). The lobby offers ONLY
        these: the Claude-5 family rejects several combinations outright (Fable cannot disable thinking, Haiku
        refuses adaptive thinking and effort levels), and a 400 from a live seat mid-game is a wasted session.
    supports_temperature : bool
        Whether a temperature may be sent at all. False for the Claude-5 models, which hard-error on any
        temperature — so the lobby hides the control rather than sending a default and failing.
    available : bool
        Whether this model can be used right now (API key present, local weights on disk / a GPU visible). An
        unavailable model is still LISTED — greyed out with ``unavailable_reason`` — because silently omitting it
        looks like the model does not exist.
    unavailable_reason : str | None
        Why not, in the user's terms (``"ANTHROPIC_API_KEY is not set"``). ``None`` when available.
    metered : bool
        Whether turns from this model cost money and must count against the session's budget cap.
    default : bool
        Whether this is the model a new ``llm`` seat starts on. The PROVIDER owns that choice — it is the half
        that knows which model this experiment actually wants played — so the lobby never spells a model id of
        its own. Flag at most one; :func:`default_model_id` resolves several (or none) by availability and list
        order rather than raising, since a lobby is the wrong place to discover a misconfigured flag.
    """

    model_id: str
    label: str
    provider: str
    thinking_modes: tuple[str, ...] = ("off",)
    supports_temperature: bool = True
    available: bool = True
    unavailable_reason: str | None = None
    metered: bool = True
    default: bool = False

    def to_json(self) -> dict:
        """The lobby's wire form (see :func:`~interlens.arena.live.events.lobby_state`)."""
        return {"model_id": self.model_id, "label": self.label, "provider": self.provider,
                "thinking_modes": list(self.thinking_modes), "supports_temperature": self.supports_temperature,
                "available": self.available, "unavailable_reason": self.unavailable_reason,
                "metered": self.metered, "default": self.default}


@dataclass
class BankInfo:
    """One instance bank the lobby may draw a game from.

    Parameters
    ----------
    bank_id : str
        Stable identifier passed back to :meth:`ScenarioProvider.prepare` (for the rational-agents launcher, the
        instances directory name, e.g. ``"instances_realistic_demo"``).
    label : str
        Display name.
    instance_ids : tuple[str, ...]
        The instances in the bank, in a stable order. The lobby offers a pick from these plus "random".
    n_parties : int | None
        Seat count, when every instance in the bank shares one (the usual case) — the lobby builds that many seat
        cards before an instance is chosen. ``None`` for a mixed bank, where the cards wait for :meth:`prepare`.
    description : str
        One line about what the bank contains, shown under the picker.
    """

    bank_id: str
    label: str
    instance_ids: tuple[str, ...] = ()
    n_parties: int | None = None
    description: str = ""

    def to_json(self) -> dict:
        """The lobby's wire form."""
        return {"bank_id": self.bank_id, "label": self.label, "instance_ids": list(self.instance_ids),
                "n_parties": self.n_parties, "description": self.description}


@dataclass
class SeatConfig:
    """What the lobby says should sit in one seat — the unit of both initial configuration and a mid-game swap.

    The same dataclass travels in three directions (lobby form -> server, server -> participant construction,
    server -> browser as part of ``lobby_state``), so a seat is described exactly once.

    Parameters
    ----------
    kind : str
        One of :data:`SEAT_KINDS`.
    model_id : str | None
        For ``kind="llm"``: which model (a :class:`ModelInfo` ``model_id``). Ignored otherwise.
    policy : str | None
        For ``kind="rational"`` / ``"oracle"``: the policy name (a key of ``arena.table.POLICY_FACTORIES``, e.g.
        ``"bayes-rational"``). The kind, not the policy, decides whether the seat gets full-information tables.
    thinking : str
        For ``kind="llm"``: the extended-thinking mode, restricted to the model's ``thinking_modes``. The empty
        string means "whatever this model's default is" (:func:`default_thinking`, i.e. thinking on wherever the
        model allows it) and is what an unconfigured seat carries — spelled as its own value rather than as a
        literal mode because ``off`` has to keep meaning a deliberate ``off``, and a seat that had thinking
        turned off by hand must not have it turned back on by a re-validation.
    instructions : str
        Extra PRIVATE instructions for this seat, appended to its ``private_context`` as one labelled segment.
        This is how a live operator gives one seat a persona or a hidden agenda without editing a scaffold. Empty
        string means none. Meaningless for computable seats (the lobby greys the field out) since a policy does
        not read prose.
    display_name : str
        Who the transcript says is playing — the ``human:<name>`` label for a human seat, and the occupant badge
        for any other. Empty string means "derive it from the kind and model/policy".
    """

    kind: str = "llm"
    model_id: str | None = None
    policy: str | None = None
    thinking: str = ""
    instructions: str = ""
    display_name: str = ""

    def occupant_label(self) -> str:
        """The ``kind:detail`` string stamped on every turn this seat plays (``TurnRecord.occupant``).

        One function so the label the router stamps, the badge the transcript draws and the swap event's
        ``from``/``to`` are all the same string — an occupant timeline assembled from three spellings of the same
        seat would be unreadable. ``display_name`` overrides the detail when set.

        The prefix is the seat's ROLE rather than its ``kind`` verbatim (``llm`` -> ``api:``, ``rational`` ->
        ``policy:``), matching the vocabulary the rest of the arena already uses for seat kinds. The detail
        defaults to whatever identifies that role: the model id, the policy name, the player's name.
        """
        detail = self.occupant_detail()
        return f"{_OCCUPANT_PREFIX.get(self.kind, self.kind)}:{detail}"

    def occupant_detail(self) -> str:
        """The half of :meth:`occupant_label` after the colon — the model, policy or person.

        Exposed separately for one reason: a ``HumanParticipant`` stamps ``human:<its own name>`` on the turns it
        plays (it knows who is at the keyboard; the table only knows who it was told about), so the session MUST
        construct it with this exact string or the seat would report two different players for the same person.
        """
        named = (self.display_name or "").strip()
        if named:
            return named
        fallback = {"llm": self.model_id, "rational": self.policy, "oracle": self.policy,
                    "human": "player"}.get(self.kind)
        return (fallback or self.kind).strip()

    def resolved(self, models: Any) -> "SeatConfig":
        """This seat with the choices nobody made filled in from the offered models — the ONE place defaults land.

        For an ``llm`` seat: an empty ``model_id`` becomes :func:`default_model_id` (the provider's flagged
        model), and an empty ``thinking`` becomes that model's :func:`default_thinking` (thinking on wherever it
        is allowed). Any other seat, and any field already set, is returned untouched — including a deliberate
        ``off``, which is why the unset value is ``""`` rather than a mode name.

        Called by the session on every lobby edit, every start and every swap, so a client that posts a bare
        ``{"kind": "llm"}`` gets the same seat the lobby page would have shown it. Idempotent: resolving a
        resolved config returns it unchanged (the same object, in fact).
        """
        if self.kind != "llm":
            return self
        offered = list(models or [])
        model_id = self.model_id or default_model_id(offered)
        info = next((m for m in offered if _attr(m, "model_id", None) == model_id), None)
        thinking = self.thinking or default_thinking(info)
        if (model_id, thinking) == (self.model_id, self.thinking):
            return self
        return replace(self, model_id=model_id, thinking=thinking)

    def to_json(self) -> dict:
        """The wire form the lobby page and ``lobby_state`` events carry."""
        return {"kind": self.kind, "model_id": self.model_id, "policy": self.policy, "thinking": self.thinking,
                "instructions": self.instructions, "display_name": self.display_name}

    @classmethod
    def from_json(cls, d: dict) -> "SeatConfig":
        """Rebuild from a browser-supplied dict, ignoring keys this version does not know (the same
        forward-compatible rule ``TurnRecord.from_json`` follows). Does NOT validate — the session validates,
        because it is the half that knows which models and policies actually exist."""
        fields = {"kind", "model_id", "policy", "thinking", "instructions", "display_name"}
        return cls(**{k: v for k, v in d.items() if k in fields})


@dataclass
class PreparedGame:
    """One playable game, fully assembled — the provider's answer to a lobby configuration.

    Everything the session needs to construct a table and run an episode, and nothing about WHO plays: the seats
    are configured separately (:class:`SeatConfig`) so the same prepared game can be replayed with a different
    lineup, and so a mid-game swap has the game objects already in hand.

    Parameters
    ----------
    instance : Any
        The ``Instance`` to play, already framed (the provider applies the framing before returning).
    scenario : Any
        The ``Scenario`` object (a ``ScorableNegotiation`` for negotiation play), with its oracle stack attached.
    game : Any
        The ``GameSpec`` behind the instance — the source of the private score sheets, the deal space and the
        discount. The human dock reads its seat's sheet from here, and computable seats are bound against it.
    arm : str
        The arm the episode is played under, recorded on it and passed to ``scenario.make_state``. REQUIRED, and
        deliberately without a default: the scenario validates it and a value it does not know is fatal on the
        first wave (``ScorableNegotiation`` accepts ``moves_chat`` / ``moves_only`` / ``team`` / ``solo``, or any
        ``team``-prefixed variant, and raises ``unknown arm`` otherwise). There is no arm every scenario would
        accept, so any default here would be a value that happens to work for one scenario and kills the session
        for the next — better to make the provider name one. ``moves_chat`` is the usual choice for live
        negotiation, since a live game with no talk channel gives a human nothing to do but submit moves.
    deadline : int
        Total rounds ``T``. REQUIRED for the same reason: it is bound into every computable seat's concession
        schedule (``policy_seat(deadline=...)``) and shown to the human as the round they are deciding under, so
        a deadline that disagrees with the game is not a cosmetic default but a table playing to the wrong clock
        — and silently, unlike a bad ``arm``. Read it off the game (``spec.rounds``) rather than restating it.
    cfg : dict
        The episode ``cfg`` (cell id and sweep configuration) passed to ``run_episode``.
    seat_names : tuple[str, ...]
        Seat display names in seat order (``arena.schema.PERSONAS`` for negotiation). The routing key.
    instance_json : dict
        ``instance.to_json()`` — what the visualizer's geometry is built from, kept beside the object so the
        session does not re-serialize it once per turn.
    scaffold : Any
        The framing/scaffold record, when the provider has one, for provenance on the page. Optional.
    manifest : dict
        Run-level provenance to hand the page (invocation, oracle list, seat kinds), shaped like a run's
        ``manifest.json`` so the visualizer reads it with the code it already has.
    """

    instance: Any
    scenario: Any
    game: Any
    arm: str
    deadline: int
    cfg: dict = field(default_factory=dict)
    seat_names: tuple[str, ...] = ()
    instance_json: dict = field(default_factory=dict)
    scaffold: Any = None
    manifest: dict = field(default_factory=dict)


class ScenarioProvider(Protocol):
    """What an experiment must supply for its games to be playable live.

    Implement it anywhere — it is a structural protocol, so no import of interlens is needed to satisfy it — and
    hand an instance to :func:`~interlens.arena.live.run_live_server`. The listing methods drive the lobby and
    are called on every lobby render (keep them cheap or cache them); ``prepare`` and ``build_model_seat`` are
    called when a game starts and when a seat is swapped.
    """

    def list_banks(self) -> list[BankInfo]:
        """The instance banks the lobby may draw from, in display order. May be empty (the lobby then says so
        rather than offering a broken picker)."""

    def list_framings(self) -> list[dict]:
        """The framings/skins available, as ``{"framing_id", "label", "description"}`` dicts. A framing rewrites
        an instance's surface story (issue names, party names, the cover narrative) without touching its payoff
        structure, so it is chosen independently of the bank."""

    def list_models(self) -> list[ModelInfo]:
        """Every model an ``llm`` seat may be assigned, INCLUDING ones that are currently unavailable (each
        carrying its own reason). Availability is reported, never silently filtered — see :class:`ModelInfo`."""

    def prepare(self, bank: str, framing: str, instance_id: str | None,
                overrides: dict | None = None) -> PreparedGame:
        """Assemble one playable game.

        ``bank`` and ``framing`` are ids from the listings; ``instance_id`` picks an instance from the bank, and
        ``None`` means "choose one" (the provider decides how — random, or the bank's first). ``overrides`` is
        the lobby's free-form extra configuration (seed, deadline, difficulty, oracle selection) — a dict rather
        than fixed parameters because what is tunable is the experiment's business, not the server's.

        Raises ``ValueError`` for an unknown bank/framing/instance, which the server turns into a 400 with the
        message shown in the lobby.
        """

    def build_model_seat(self, model_id: str, *, thinking: str = "off", meter: Any = None,
                         extra_instructions: str = "") -> Any:
        """Construct the participant for one ``llm`` seat and return it.

        ``thinking`` is one of that model's ``thinking_modes``; ``meter`` is the session's ``UsageMeter``, which
        the participant must charge so the budget cap actually binds; ``extra_instructions``, when non-empty, is
        appended to the participant's ``private_context`` as one labelled segment.

        The returned participant must be SAFE TO OWN: the session may set per-seat instructions on it and may
        hold several seats on the same model at once, so a provider that caches participants by model id has to
        return a wrapper or copy rather than a shared object — otherwise one seat's private instructions leak
        into another's view.
        """
