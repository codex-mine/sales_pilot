"""Small shared helpers used across service modules."""

import uuid
from typing import Any


def json_safe(value: Any) -> Any:
    """Audit log `changes` is stored as JSONB — UUIDs (e.g. owner_id) aren't
    natively JSON-serializable, so stringify anything that isn't already a
    plain JSON-compatible type before it reaches the DB driver."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value
