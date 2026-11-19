"""Privacy safeguards for people data.

People analytics works with personal data, so the report follows three rules:
1. Only pseudonymous employee IDs are used; no names or contact details.
2. Any group smaller than MIN_GROUP people is hidden ("<5"), so no individual can be singled out.
3. Only aggregated numbers leave the tool, including what is sent to an AI model.
"""

from __future__ import annotations

MIN_GROUP = 5
SUPPRESSED = f"<{MIN_GROUP}"


def suppress(value, group_size: int):
    """Return the value, or the suppression marker if the group is too small to report."""
    return SUPPRESSED if group_size < MIN_GROUP else value


def is_suppressed(value) -> bool:
    return value == SUPPRESSED
