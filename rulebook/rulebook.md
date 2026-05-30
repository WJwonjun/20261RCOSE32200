# Pokemon Champions Single Battle Rulebook (MVP)

A 6v6 single-battle format where both players simultaneously choose an action each turn—move or switch—which resolves based on priority and Speed, with the last team standing declared the winner.

## Turn Structure

Each turn follows three steps:

1. **Action Selection**: Both players independently choose an action (use a move or switch Pokemon).
2. **Resolution**: Actions resolve in order of priority (switches at 6, then priority moves, then normal moves), with Speed as tiebreaker within priority tier.
3. **End-of-Turn**: Status damage is applied, abilities tick (MVP: none), items tick (Leftovers etc.).

See [Turn Order](turn-order.md) for detailed priority and speed resolution.

## Actions You Can Take

On your turn, choose exactly one action from:

- **Move**: Use one of your active Pokemon's four known moves. Move must have PP > 0. Accuracy check happens at execution.
- **Switch**: Swap your active Pokemon with one from your bench (team). Costs your turn (no move that turn). Switching always resolves before any move.

See [Actions](actions.md) for full specifications.

## Damage Calculation

Damage follows a deterministic formula accounting for base power, attacker/defender stats, type advantage, STAB, critical hits, and RNG variance:

```
damage = floor(((2 * level / 5 + 2) * power * Atk / Def / 50 + 2)
              * stab * type_effectiveness * crit * random)
```

- **stab**: 1.5 if move type matches attacker's type, else 1.0.
- **type_effectiveness**: Product of effectiveness vs each defender's types (see type chart). Values: 0 / 0.5 / 1.0 / 2.0.
- **crit**: 1.5 with 1/24 base probability (no crit-stage modifiers in MVP).
- **random**: Uniform variance in range [0.85, 1.0].
- **Burn**: Halves physical Atk stat.

See [Damage](damage.md) and [Type Chart](type-chart.md).

## Status Conditions

Five status conditions can be inflicted and persist until cured or the Pokemon is switched (in MVP, status does NOT clear on switch):

- **Burn**: Inflicted by moves marked with burn. 1/16 max HP damage end of turn. Halves physical Atk.
- **Poison**: Inflicted by moves marked with poison. 1/8 max HP damage end of turn.
- **Paralysis**: Inflicted by moves marked with paralysis. 25% chance to be fully paralyzed each turn (skip that turn's move). Speed halved.
- **Freeze**: Inflicted by moves marked with freeze. Cannot move. 20% chance to thaw each turn.
- **Sleep**: Inflicted by moves marked with sleep. Cannot move. Duration 1–3 turns (RNG).

See [Status Conditions](status.md).

## Pokemon Stats

Each Pokemon has six base stats that determine battle effectiveness:

- **HP**: Health points.
- **Atk**: Physical attack strength.
- **Def**: Physical defense.
- **SpA**: Special attack strength.
- **SpD**: Special defense.
- **Spe**: Speed (determines action order).

Stats are computed from base stats (species), IVs (0–31 per stat, hidden), EVs (0–252 per stat, max 508 total), Nature (+10% one stat, −10% another), and level:

```
stat = floor((2 * base + iv + ev/4) * level / 100) + 5
HP   = floor((2 * base + iv + ev/4) * level / 100) + level + 10
```

See [Stats](stats.md).

## Items (Held)

Held items provide passive effects during battle. In MVP, only two items are implemented:

- **Leftovers**: 1/16 max HP recovery at end of turn.
- **Life Orb**: Moves deal ×1.3 damage; attacker takes 1/10 recoil damage.

Other items act as noop. `[DATA: see db/item_master for available items]`

See [Items](items.md).

## Abilities

**NOT IMPLEMENTED IN MVP.** All abilities act as noop. Ability slots exist in the Pokemon spec for future use. Do not reference abilities in your action reasoning.

See [Abilities](abilities.md) (placeholder).

## Output Format (CRITICAL for LLM Agent)

The LLM agent must respond with a `choose_action` tool call. The schema is:

```json
{
  "action_type": "move" | "switch",
  "move_index": 0 | 1 | 2 | 3,          // if action_type == "move"
  "switch_to_index": 0 | 1 | 2 | 3 | 4 | 5  // if action_type == "switch"
}
```

**Critical rule**: Pick an action from the `legal_actions` list provided in the turn state. Do not invent moves or Pokemon not in that list.

## What Is NOT in This MVP

Explicitly out of scope to prevent LLM hallucination:

- **Weather** (sun, rain, hail, sandstorm) and **terrain** (grassy, psychic, misty, electric).
- **Abilities** (all treated as noop).
- **Z-Moves**, **Dynamax**, **Terastallize**, and other Galar/Alola/Sword&Shield/Scarlet&Violet mechanics.
- **Double Battles**, **Triple Battles**, or **Rotation Battles**.
- **Field Hazards** (stealth rock, spikes, toxic spikes, reflect, light screen).
- **Stat Stages** (menus like AtheniumBoost/Calm Mind chains). All stat changes are reset on switch.
- **Held item effects beyond Leftovers and Life Orb**.
- **Toxic** (badly-poisoned). Only regular poison (1/8 HP) is in scope.
- **Crit-stage modifiers** (e.g., Scope Lens, high-crit moves). Base 1/24 only.
- **Escape moves** (Teleport, Baton Pass, U-turn in MVP).

Anything not listed in this rulebook does not exist in the battle simulator.
