# Turn Order and Priority

Both players submit their chosen action simultaneously. Resolution happens in a strict priority and speed order.

## Priority Tiers

Actions resolve in this order:

1. **Priority 6**: Switch actions (always resolve first).
2. **Priority 5–1**: Moves with positive priority (Quick Attack, Aqua Jet, Trick Room, etc.).
3. **Priority 0**: Normal moves (the vast majority).
4. **Priority -1 to -7**: Moves with negative priority (Vital Throw, Focus Punch, etc.). NOT IN MVP.

Within the same priority tier, the Pokemon with the higher effective Speed acts first. Effective Speed is calculated as:

```
effective_speed = base_speed
if paralyzed:
  effective_speed = floor(base_speed * 0.5)
```

Speed ties are broken by RNG (coinflip).

## Resolution Example

```
Turn 1:
- Player A's Alakazam (Spe 120, not paralyzed) uses Psychic (priority 0)
- Player B's Machamp (Spe 65, not paralyzed) switches to Dragonite

Resolution:
1. Dragonite switches in (priority 6, highest tier) → active.
2. Alakazam moves (priority 0) → attacks Dragonite.
3. End-of-turn status ticks.
```

## Simultaneous Action Selection

Both players must declare their action before any action resolves. If Player A switches and Player B uses a move on the old active Pokemon, the move fails (target is no longer active). The move's PP is NOT consumed.
