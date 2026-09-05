# `PassiveGatePolicy`

Pure veto discipline, zero strategy: NEVER proposes; accepts any standing offer that clears its own reservation (surplus >= 0) and declines everything below it, on ordinary turns and on the terminal vote alike.

```python
PassiveGatePolicy()
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L593-L614)

**Inherits from:** [Policy](Policy.md)

This is the anchor stripped down to the one thing every rational agent does — refusing to sign a deal that
is worse than no deal. It contributes no deals of its own, so anything it changes about a table's outcome
is the discipline channel and nothing else. Needs a chat-enabled arm (it emits
:class:`~interlens.arena.actions.Pass` when there is nothing to respond to).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |
| `vote` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L605-L609)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
