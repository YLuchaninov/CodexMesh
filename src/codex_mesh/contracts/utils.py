"""
Contract utilities.

Provides compatibility helpers for Pydantic v1/v2.
"""

from typing import Any


def dump_model(obj: Any) -> Any:
    """
    Dump a Pydantic model to dict, compatible with both v1 and v2.

    Args:
        obj: Pydantic model instance or dict

    Returns:
        Dictionary representation of the model
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, "dict"):
        # Pydantic v1
        return obj.dict()
    return obj
