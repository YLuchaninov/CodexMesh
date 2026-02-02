"""
Unit tests for EventBus.

Tests event subscription, publishing, and handler management.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.core.events import Event, EventBus


class TestEventBusInit:
    """Tests for EventBus initialization."""

    def test_init_empty_subscribers(self):
        """Test that EventBus starts with no subscribers."""
        bus = EventBus()

        assert len(bus._subscribers) == 0


class TestSubscribe:
    """Tests for subscribe method."""

    def test_subscribe_adds_handler(self):
        """Test that subscribe adds a handler to the list."""
        bus = EventBus()
        handler = MagicMock()

        bus.subscribe(handler)

        assert handler in bus._subscribers
        assert len(bus._subscribers) == 1

    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers."""
        bus = EventBus()
        handler1 = MagicMock()
        handler2 = MagicMock()
        handler3 = MagicMock()

        bus.subscribe(handler1)
        bus.subscribe(handler2)
        bus.subscribe(handler3)

        assert len(bus._subscribers) == 3

    def test_subscribe_same_handler_twice(self):
        """Test that same handler can be subscribed twice."""
        bus = EventBus()
        handler = MagicMock()

        bus.subscribe(handler)
        bus.subscribe(handler)

        # Both are added (implementation doesn't prevent duplicates)
        assert len(bus._subscribers) == 2


class TestUnsubscribe:
    """Tests for unsubscribe method."""

    def test_unsubscribe_removes_handler(self):
        """Test that unsubscribe removes a handler."""
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(handler)

        bus.unsubscribe(handler)

        assert handler not in bus._subscribers
        assert len(bus._subscribers) == 0

    def test_unsubscribe_nonexistent_handler(self):
        """Test that unsubscribing non-existent handler doesn't error."""
        bus = EventBus()
        handler = MagicMock()

        # Should not raise
        bus.unsubscribe(handler)

        assert len(bus._subscribers) == 0

    def test_unsubscribe_one_of_many(self):
        """Test unsubscribing one handler leaves others."""
        bus = EventBus()
        handler1 = MagicMock()
        handler2 = MagicMock()
        bus.subscribe(handler1)
        bus.subscribe(handler2)

        bus.unsubscribe(handler1)

        assert handler1 not in bus._subscribers
        assert handler2 in bus._subscribers
        assert len(bus._subscribers) == 1


class TestPublish:
    """Tests for publish method."""

    def test_publish_calls_all_handlers(self):
        """Test that publish calls all subscribed handlers."""
        bus = EventBus()
        handler1 = MagicMock()
        handler2 = MagicMock()
        bus.subscribe(handler1)
        bus.subscribe(handler2)

        event: Event = {
            "timestamp": "2024-01-01T00:00:00",
            "type": "test_event",
            "payload": {"key": "value"},
        }

        bus.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    def test_publish_no_handlers(self):
        """Test publishing with no handlers doesn't error."""
        bus = EventBus()

        event: Event = {"timestamp": "2024-01-01T00:00:00", "type": "test_event", "payload": {}}

        # Should not raise
        bus.publish(event)

    def test_publish_handler_error_doesnt_stop_others(self):
        """Test that handler errors don't prevent other handlers from running."""
        bus = EventBus()

        handler1 = MagicMock(side_effect=Exception("Handler 1 failed"))
        handler2 = MagicMock()

        bus.subscribe(handler1)
        bus.subscribe(handler2)

        event: Event = {"timestamp": "2024-01-01T00:00:00", "type": "test_event", "payload": {}}

        # Should not raise
        bus.publish(event)

        # handler2 should still be called
        handler2.assert_called_once_with(event)

    def test_publish_logs_debug(self):
        """Test that publish logs the event."""
        bus = EventBus()

        event: Event = {
            "timestamp": "2024-01-01T00:00:00",
            "type": "test_event",
            "payload": {"data": "test"},
        }

        with patch("codex_mesh.core.events.logger") as mock_logger:
            bus.publish(event)

            mock_logger.debug.assert_called()


class TestEmit:
    """Tests for emit convenience method."""

    def test_emit_creates_event(self):
        """Test that emit creates a properly structured event."""
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(handler)

        bus.emit("test_type", {"key": "value"})

        # Check the event passed to handler
        call_args = handler.call_args[0][0]
        assert call_args["type"] == "test_type"
        assert call_args["payload"] == {"key": "value"}
        assert "timestamp" in call_args

    def test_emit_with_no_payload(self):
        """Test emit with no payload uses empty dict."""
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(handler)

        bus.emit("test_type")

        call_args = handler.call_args[0][0]
        assert call_args["payload"] == {}

    def test_emit_timestamp_is_valid(self):
        """Test that emit creates a valid ISO timestamp."""
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(handler)

        bus.emit("test_type")

        call_args = handler.call_args[0][0]
        timestamp = call_args["timestamp"]

        # Should be parseable as ISO format
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp}' is not valid ISO format")


class TestEventTypedDict:
    """Tests for Event TypedDict structure."""

    def test_event_structure(self):
        """Test that Event TypedDict has correct fields."""
        event: Event = {"timestamp": "2024-01-01T00:00:00", "type": "test", "payload": {}}

        assert "timestamp" in event
        assert "type" in event
        assert "payload" in event
