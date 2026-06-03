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


def build_selection_messages(
    rulebook_text: str,
    team_spec: str,
    selection_state: dict,
) -> tuple[list[dict], list[dict]]:
    """Messages for the team-preview (6 -> 3) decision."""
    system_blocks = [
        {"type": "text", "text": rulebook_text, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": team_spec, "cache_control": {"type": "ephemeral"}},
    ]

    party = selection_state.get("party", [])
    n = selection_state.get("select_count", 3)
    user_messages = [
        {
            "role": "user",
            "content": (
                f"Team preview. Choose exactly {n} of your 6 Pokemon to bring to "
                "this battle (the rest stay benched the whole match).\n\n"
                "Your full party (index = party slot 0-5):\n"
                + json.dumps(party, indent=2)
                + "\n\nReturn the chosen party slot indices with the choose_selection "
                "tool. selection must be 3 distinct indices in 0-5; lead_idx_in_party "
                "is the slot that starts active and must be one of them."
            ),
        }
    ]
    return system_blocks, user_messages
