from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TurnState(BaseModel):
    model_config = {"extra": "allow"}

    rulebook_hash: str
    acting_team: dict
    opponent_visible: dict
    turn_no: int
    side: str
    legal_actions: list


class Action(BaseModel):
    action: Literal["move", "switch"]
    target: int
    reason: str | None = None


class LLMCallResult(BaseModel):
    action: Action | None
    failure_reason: Literal[None, "timeout", "rate_limit", "parse_fail", "schema_violation"] = None
    latency_ms: int
    cached_tokens: int
    prompt_tokens: int
    idempotency_key: str


class SelectionState(BaseModel):
    """Team-preview request payload: the full 6-Pokemon party for one side."""

    model_config = {"extra": "allow"}

    side: str
    party: list  # 6 entries, each with slot/name/types/stats/moves
    select_count: int = 3


class SelectionResult(BaseModel):
    """Team-preview response: which party slots (0-5) to field, lead first.

    Mirrors the C++ SelectionResponse / parse_selection_response contract:
    `selection` is 3 distinct party indices and `lead_idx_in_party` is the
    initial active mon (must be one of `selection`)."""

    selection: list[int] | None
    lead_idx_in_party: int | None = None
    failure_reason: Literal[None, "timeout", "rate_limit", "parse_fail", "schema_violation"] = None
    latency_ms: int = 0
    cached_tokens: int = 0
    prompt_tokens: int = 0
    idempotency_key: str = ""
