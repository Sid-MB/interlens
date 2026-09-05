# `EpisodeView`

A parsed episode: seats, the turn series, the offer registry, per-round standing offer, and outcome.

```python
EpisodeView(
	episode_id: str,
	arm: str,
	model: str,
	seats: list[str],
	turns: list[TurnView],
	proposals: dict[Any, dict] = dict(),
	final_deal: Deal | None = None,
	reached: bool = False,
	outcome: dict = dict(),
	standing_offer_by_round: dict[int, Deal | None] = dict(),
)
```

Defined in [`interlens.arena.negotiation.analysis.episode_view`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/episode_view.py#L69-L118)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
| `arm` | `str` | *required* |  |
| `model` | `str` | *required* |  |
| `seats` | `list[str]` | *required* |  |
| `turns` | list[[TurnView](TurnView.md)] | *required* |  |
| `proposals` | `dict[Any, dict]` | `dict()` |  |
| `final_deal` | `Deal \| None` | `None` |  |
| `reached` | `bool` | `False` |  |
| `outcome` | `dict` | `dict()` |  |
| `standing_offer_by_round` | `dict[int, Deal \| None]` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `arm` | `str` |  |
| `episode_id` | `str` |  |
| `final_deal` | `Deal \| None` |  |
| `model` | `str` |  |
| `n_agents` | `int` |  |
| `outcome` | `dict` |  |
| `proposals` | `dict[Any, dict]` |  |
| `reached` | `bool` |  |
| `seats` | `list[str]` |  |
| `standing_offer_by_round` | `dict[int, Deal \| None]` |  |
| `turns` | list[[TurnView](TurnView.md)] |  |

## Methods {#methods}

## `from_episode` {#from_episode}

```python
from_episode(cls, episode: dict, game: GameAnalysis) -> 'EpisodeView'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/episode_view.py#L95-L118)

Parse a stored `Episode.to_json()` dict into an `EpisodeView` using `game` to canonicalize deals.

Robust to unknown seats (falls back to the episode's `seats` list) and to actions that fail to
canonicalize (kept as a turn with `parse_ok=False` and no deal, so nothing is silently dropped).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |

## `proposals_by` {#proposals_by}

```python
proposals_by(self, seat: str) -> list[TurnView]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/episode_view.py#L91-L93)

Every turn on which `seat` registered a proposal (in order).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |

## `seat_index` {#seat_index}

```python
seat_index(self, seat: str) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/episode_view.py#L88-L89)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
