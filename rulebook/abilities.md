# Abilities

Abilities are NOT IMPLEMENTED IN MVP. All abilities act as noop (no operation).

## Current Status

- Ability slots exist in the Pokemon spec for future implementation.
- The LLM agent should NOT reference or reason about abilities when choosing actions.
- No ability effects are active during MVP battles.

## Future

In post-MVP versions, abilities will provide passive effects such as:

- Type-based stat boosts (Overland, Sand Stream, etc.).
- Weather setups (Drought, Drizzle, etc.).
- Stat modifications on switch or in-battle (Intimidate, etc.).
- Damage reductions or immunities (Water Absorb, Flash Fire, etc.).
- And many others.

Until then, treat all Pokemon as if they have no ability.

`[DATA: see db/ability_master for ability definitions (future use)]`
