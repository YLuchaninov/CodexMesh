"""
Event bus for structured observability.

Per advanced.md: Key internal events should emit structured events.
MVP Note: Simple logging is acceptable for initial iterations.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypedDict

logger = logging.getLogger(__name__)


class Event(TypedDict):
    """Structured event format per advanced.md."""

    timestamp: str
    type: str
    payload: dict


EventHandler = Callable[[Event], None]


class EventBus:
    """
    Simple event bus for internal observability.

    Per advanced.md: Enables UI integration, logging, debuggability.
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._subscribers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        """Subscribe a handler to receive events."""
        self._subscribers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        """Unsubscribe a handler."""
        if handler in self._subscribers:
            self._subscribers.remove(handler)

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Also logs the event for MVP observability.
        """
        logger.debug(f"Event: {event['type']} - {event['payload']}")
        for handler in self._subscribers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def emit(self, event_type: str, payload: dict | None = None) -> None:
        """Convenience method to create and publish an event."""
        event: Event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event_type,
            "payload": payload or {},
        }
        self.publish(event)
