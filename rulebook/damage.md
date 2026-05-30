# Damage Calculation

Damage is computed by a deterministic formula that combines base power, attacker/defender stats, type advantage, STAB, critical hits, and random variance.

## Formula

```
damage = floor(((2 * level / 5 + 2) * power * Atk / Def / 50 + 2)
              * stab * type_effectiveness * crit * random)
```

## Term Definitions

- **level**: Attacker's level (typically 50 in MVP).
- **power**: Move's base power. Status moves have power 0 and deal 0 damage.
- **Atk/Def**: For physical moves: attacker's Attack stat vs. defender's Defense stat.
  - If attacker is burned: Atk is halved before calculation.
- **SpA/SpD**: For special moves: attacker's Special Attack stat vs. defender's Special Defense stat.
- **stab** (Same Type Attack Bonus): 1.5 if move's type matches attacker's type; otherwise 1.0.
- **type_effectiveness**: Product of effectiveness multipliers for each of defender's types. See [Type Chart](type-chart.md).
  - Possible values: 0.0, 0.25, 0.5, 1.0, 2.0, 4.0.
  - Example: Water move vs. Fire/Rock defender = 2.0 × 2.0 = 4.0.
- **crit** (Critical Hit): 1.5 if critical hit occurs; 1.0 otherwise.
  - Base critical hit chance: 1/24 (≈4.17%).
  - MVP: No critical hit stage modifiers. Base chance only.
- **random**: Damage variance. Uniform random value in [0.85, 1.0].

## Status Effect Interactions

- **Burn**: Attacker's physical Attack is halved before damage calculation. This applies only to physical moves.
- **Paralysis**: Does not modify damage directly (see [Status](status.md) for movement restrictions).
- **Other statuses**: Do not modify damage in MVP.

## Status Moves

Moves with power 0 (status moves like Thunder Wave, Will-O-Wisp, Toxic Spikes) deal 0 damage. They apply status conditions or other effects instead. See the move's specification for effect details.

## Examples

**Example 1: Physical Move, No Advantage**
- Charizard (Atk 104, level 50) uses Earthquake (power 100, ground type) vs. Gyarados (Def 100).
- Charizard is not ground-type: stab = 1.0.
- Gyarados is water/flying. Earthquake is super-effective vs. water (2.0) but not flying (1.0): type_effectiveness = 2.0.
- Random hit, no crit: crit = 1.0, random = 0.95.
- Damage = floor(((2×50/5 + 2) × 100 × 104 / 100 / 50 + 2) × 1.0 × 2.0 × 1.0 × 0.95) ≈ 90.

**Example 2: Special Move, STAB, Super-Effective**
- Blastoise (SpA 105, level 50, water type) uses Hydro Pump (power 110, water type, special) vs. Charizard (SpD 100).
- Blastoise is water type, move is water type: stab = 1.5.
- Charizard is fire/flying. Hydro Pump is super-effective vs. fire (2.0) and neutral vs. flying (1.0): type_effectiveness = 2.0.
- Critical hit: crit = 1.5, random = 0.90.
- Damage = floor(((2×50/5 + 2) × 110 × 105 / 100 / 50 + 2) × 1.5 × 2.0 × 1.5 × 0.90) ≈ 202.
