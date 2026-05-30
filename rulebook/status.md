# Status Conditions

Status conditions are persistent debuffs applied during battle. In MVP, five status conditions exist. A Pokemon can have exactly one status condition at a time.

## Burn

**Infliction**: Moves marked with the burn effect (e.g., Will-O-Wisp, Scald).

**Effect**: 
- End-of-turn damage: 1/16 of max HP.
- Physical attacks deal 50% damage (attacker's Attack is halved in damage calculation).

**Duration**: Permanent (does not clear on switch in MVP).

**Cure**: Use an item, move, or ability that cures burn. In MVP, switch does NOT cure it.

## Poison

**Infliction**: Moves marked with the poison effect (e.g., Poison Powder, Toxic Spikes).

**Effect**:
- End-of-turn damage: 1/8 of max HP.

**Duration**: Permanent.

**Cure**: Use an item or move that cures poison.

**Note**: Toxic (badly-poisoned) is NOT IN MVP. Only regular poison (1/8 HP per turn) exists.

## Paralysis

**Infliction**: Moves marked with the paralysis effect (e.g., Thunder Wave, Stun Spore, Body Slam).

**Effect**:
- Speed is halved (effective speed = floor(base speed × 0.5)).
- 25% chance to be fully paralyzed each turn (Pokemon cannot move that turn; move does not execute, PP not consumed).

**Duration**: Permanent.

**Cure**: Use an item or move that cures paralysis.

## Freeze

**Infliction**: Moves marked with the freeze effect (e.g., Ice Beam, Powder Snow with freeze chance).

**Effect**:
- Pokemon cannot move. All moves fail (PP not consumed).

**Duration**: Until thawed. 20% chance to thaw spontaneously at end of turn.

**Cure**: Use an item or move that cures freeze, or thaw randomly.

## Sleep

**Infliction**: Moves marked with the sleep effect (e.g., Sleep Powder, Spore).

**Effect**:
- Pokemon cannot move. All moves fail (PP not consumed).

**Duration**: 1–3 turns (random). After duration expires, Pokemon wakes up automatically.

**Cure**: Use an item or move that cures sleep, or sleep duration expires.

## End-of-Turn Status Damage

At the end of each turn (after all moves resolve), the following happen in order:

1. Burn damage: 1/16 max HP.
2. Poison damage: 1/8 max HP.
3. Paralysis full paralysis roll: 25% chance to skip next turn.
4. Freeze thaw roll: 20% chance to cure freeze.
5. Sleep counter: Decrement sleep turns; if reaches 0, cure.

If damage from status reduces HP to 0, the Pokemon faints immediately.

## Interaction Notes

- **Dual status**: NOT POSSIBLE IN MVP. A Pokemon has at most one status condition.
- **Status on switch**: In MVP, status does NOT clear when a Pokemon switches in or out.
- **Status immunity via ability**: NOT IN MVP. Abilities are noop.
