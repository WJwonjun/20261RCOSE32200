# Actions: Move and Switch

On each turn, you must select exactly one action.

## Move Action

**Select**: Move index (0, 1, 2, or 3) from your active Pokemon's known moves.

**Requirement**: Move must have PP > 0. If a move has 0 PP, it cannot be selected and will not appear in `legal_actions`.

**Execution**: At resolution time, accuracy is checked. If the move misses, damage/effect does not apply, but PP is still consumed.

**Move Properties**:
- **Power**: Base damage (varies by move; status moves have power 0 and deal no damage).
- **Category**: Physical, Special, or Status.
  - **Physical**: Uses attacker Atk vs. defender Def.
  - **Special**: Uses attacker SpA vs. defender SpD.
  - **Status**: No damage, applies status or other effects.
- **Accuracy**: Chance to hit. Base 100% for most moves; some moves have lower accuracy (e.g., Hydro Pump at 80%).
- **Priority**: Default 0. Some moves have priority > 0 (Quick Attack +1) or < 0 (Vital Throw -1). See [Turn Order](turn-order.md).

## Switch Action

**Select**: Target Pokemon index (0–5) from your bench (team). Cannot switch to the currently active Pokemon. Cannot switch to a fainted Pokemon.

**Effect**: Your active Pokemon is replaced with the target. The old Pokemon goes to the bench; the new Pokemon enters the field. No move is used that turn.

**Speed**: Switch always has priority 6 (resolves before any move).

**Status Persistence**: In MVP, status conditions do NOT clear when a Pokemon switches in. A burned Pokemon remains burned; a paralyzed Pokemon remains paralyzed. (This is intentional MVP behavior.)

**Turn Cost**: Switching uses your turn. You cannot switch and use a move in the same turn.
