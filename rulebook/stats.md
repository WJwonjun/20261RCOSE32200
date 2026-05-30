# Pokemon Stats

Each Pokemon has six core stats that determine its effectiveness in battle. Stats are calculated from species base stats, IVs (Individual Values), EVs (Effort Values), Nature, and level.

## The Six Stats

- **HP**: Health points. Determines how much damage a Pokemon can take before fainting.
- **Atk** (Attack): Physical attack strength. Used for physical moves in damage calculation.
- **Def** (Defense): Physical defense. Reduces damage from physical moves.
- **SpA** (Special Attack): Special attack strength. Used for special moves in damage calculation.
- **SpD** (Special Defense): Special defense. Reduces damage from special moves.
- **Spe** (Speed): Determines action order in battle (see [Turn Order](turn-order.md)).

## Stat Calculation Formula

For all stats except HP:

```
stat = floor((2 * base + iv + ev/4) * level / 100) + 5
```

For HP (unique formula):

```
HP = floor((2 * base + iv + ev/4) * level / 100) + level + 10
```

Where:

- **base**: Species base stat (0–255 typically).
- **iv**: Individual Value (0–31, hidden, random or set per Pokemon).
- **ev**: Effort Value (0–252 per stat, max 508 total across all stats).
- **level**: Pokemon's level (typically 50 in MVP).

## Individual Values (IVs)

- Range: 0–31 per stat.
- Determined at creation (random in wild Pokemon, bred or set in trainer Pokemon).
- Cannot be changed in-battle.
- Represents hidden genetic variance. A perfect IV is 31.

## Effort Values (EVs)

- Range: 0–252 per stat, max 508 total across all six stats.
- Gained from defeating Pokemon or using items.
- Typically allocated to maximize 2–3 relevant stats.
- Common allocations: 252 Atk / 252 Spe / 4 HP (physical attacker), 252 SpA / 252 Spe / 4 HP (special attacker).
- Cannot be changed mid-battle.

## Nature

- Boosts one stat by 1.1× and reduces another by 0.9×.
- Does not change the stat calculation formula; instead, the final stat is multiplied by the Nature's modifier.

### Common Natures

| Nature | Boost | Reduce |
|---|---|---|
| Adamant | Atk | SpA |
| Modest | SpA | Atk |
| Jolly | Spe | SpA |
| Timid | Spe | Atk |
| Bold | Def | Atk |
| Calm | SpD | Atk |
| Relaxed | Def | Spe |
| Careful | SpD | SpA |

Other natures exist but follow the same ±10% pattern: 5 natures boost HP (no-op), 5 boost each of the 5 other stats, resulting in 25 natures total. Only 1 nature is "neutral" (Serious, Hardy, etc.: all +/− cancel).

## Example Stat Calculation

**Charizard with Adamant nature, level 50:**
- Base Atk: 84
- IV Atk: 31
- EV Atk: 252
- Formula: floor((2 × 84 + 31 + 252/4) × 50 / 100) + 5 = floor((168 + 31 + 63) × 50 / 100) + 5 = floor(131 × 0.5) + 5 = 65 + 5 = 70.
- Adamant boost: 70 × 1.1 = 77.

**Charizard with Adamant nature, level 50 (HP):**
- Base HP: 78
- IV HP: 31
- EV HP: 4
- Formula: floor((2 × 78 + 31 + 4/4) × 50 / 100) + 50 + 10 = floor((156 + 31 + 1) × 50 / 100) + 60 = floor(94 × 0.5) + 60 = 47 + 60 = 107.
- (Nature does not affect HP.)

## Stat Changes and Resets

In MVP, stat stage modifiers (Swords Dance, Curse, Dragon Dance, etc.) are NOT IMPLEMENTED. All stats are base stats with no stage multipliers. Switching does NOT reset stats.

`[DATA: see db/pokemon_master for base stats of all Pokemon]`
