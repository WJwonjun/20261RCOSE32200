# Held Items

A Pokemon can hold one item during battle. Held items provide passive effects that activate automatically at specific times (end-of-turn, on damage taken, etc.).

## Implemented Items in MVP

### Leftovers

**Effect**: At end of turn, holder recovers 1/16 of max HP.

**Stacking**: Yes. If both Pokemon hold Leftovers, both recover 1/16 of their max HP.

### Life Orb

**Effect**: All of holder's moves deal 1.3× damage. Holder takes 1/10 recoil damage after attacking (only if the move hits).

**Interaction**: If holder's move is blocked (misses, is immune, target switches out, etc.), recoil does not apply.

## Unimplemented Items (Placeholder)

All other items act as noop in MVP. `[DATA: see db/item_master for available items]`

These items exist in the Pokemon spec but have no in-battle effect:

- Berry items (Cheri Berry, Lum Berry, etc.)
- Stat-boosting items (Assault Vest, Choice Specs, etc.)
- Type-modifying items (Plates, Memories, etc.)
- Other consumables and held items.

Future versions will implement more items; do not assume any effect for items not listed above.

## Item Persistence

Items do not change during battle. Once a Pokemon is sent into battle with an item, it keeps that item unless a move explicitly switches items (NOT IN MVP). Switching Pokemon does not change their held items.
