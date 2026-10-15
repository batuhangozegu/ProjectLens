"""Pure task status transition rules."""

ALLOWED_TRANSITIONS = {
    "TODO": frozenset({"IN_PROGRESS", "DONE", "BLOCKED"}),
    "IN_PROGRESS": frozenset({"TODO", "DONE", "BLOCKED"}),
    "BLOCKED": frozenset({"TODO", "IN_PROGRESS"}),
    "DONE": frozenset({"TODO", "IN_PROGRESS"}),
}


class InvalidTransition(ValueError):
    def __init__(self, from_status: str, to_status: str):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Task status cannot transition from {from_status} to {to_status}.")


def validate_transition(from_status: str, to_status: str) -> None:
    """Accept a same-state no-op; otherwise require an explicitly allowed edge."""
    if from_status == to_status:
        return
    if to_status not in ALLOWED_TRANSITIONS.get(from_status, ()):
        raise InvalidTransition(from_status, to_status)
