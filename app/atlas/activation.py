from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActivationResult:
    status: str
    action: str
    reason: str
    execution_mode: str


def activate_atlas(
    action: str,
    decision: dict[str, Any],
    risk: dict[str, Any],
    execution_mode: str = "paper",
) -> ActivationResult:
    """Activate only an already-approved ATLAS decision.

    Live execution is deliberately blocked in this MVP.
    """
    action = action.upper()
    execution_mode = execution_mode.lower()

    if action not in {"BUY", "SELL"}:
        return ActivationResult("BLOCKED", action, "Only BUY or SELL can be activated.", execution_mode)

    if execution_mode == "live":
        return ActivationResult("BLOCKED", action, "Live execution is disabled in the MVP.", execution_mode)

    if str(decision.get("action", "WAIT")).upper() != action:
        return ActivationResult("BLOCKED", action, "Requested action does not match the current ATLAS decision.", execution_mode)

    if not bool(decision.get("approved", False)):
        return ActivationResult("BLOCKED", action, "ATLAS decision is not approved.", execution_mode)

    risk_level = str(risk.get("level", "HIGH")).upper()
    if risk_level in {"HIGH", "BLOCKED"}:
        return ActivationResult("BLOCKED", action, f"Risk gate: {risk_level}.", execution_mode)

    return ActivationResult("ACTIVATED", action, "ATLAS activation approved for paper/demo execution.", execution_mode)
