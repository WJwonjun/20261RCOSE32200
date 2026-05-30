from __future__ import annotations

import json


def build_messages(
    rulebook_text: str,
    acting_team_spec: str,
    turn_state: dict,
) -> tuple[list[dict], list[dict]]:
    # Cache rulebook and team spec as separate system blocks so repeated calls
    # within a session reuse the cached KV instead of re-encoding each time.
    # Opponent state and turn_no change every turn, so they stay uncached.
    system_blocks = [
        {
            "type": "text",
            "text": rulebook_text,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": acting_team_spec,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    user_messages = [
        {
            "role": "user",
            "content": (
                "Opponent visible state:\n"
                + json.dumps(turn_state.get("opponent_visible", {}), indent=2)
                + "\n\nFull turn state:\n"
                + json.dumps(turn_state, indent=2)
                + "\n\nChoose the best action using the choose_action tool."
            ),
        }
    ]

    return system_blocks, user_messages
