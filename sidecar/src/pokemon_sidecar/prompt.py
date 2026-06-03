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

    legal_actions = turn_state.get("legal_actions", [])

    user_messages = [
        {
            "role": "user",
            "content": (
                "Opponent visible state:\n"
                + json.dumps(turn_state.get("opponent_visible", {}), indent=2)
                + "\n\nFull turn state:\n"
                + json.dumps(turn_state, indent=2)
                + "\n\nLegal actions this turn — you MUST pick exactly one of these "
                "{action, target} pairs:\n"
                + json.dumps(legal_actions, indent=2)
                + "\n\nFor action \"move\", target is the move slot (0-3). For action "
                "\"switch\", target is the bench slot among your selected Pokemon "
                "(idx_in_selection, 0-2), not a party slot.\n"
                "Choose the strongest legal action with the choose_action tool."
            ),
        }
    ]

    return system_blocks, user_messages
