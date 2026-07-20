"""Event types, event data model, and in-process event bus.

The EventBus provides a lightweight publish/subscribe mechanism
for decoupled communication between monitoring subsystems:

  - Change detection → alerts
  - Change detection → WebSocket broadcasts
  - Heartbeat processing → health score updates
  - Any future cross-module communication

Events are processed synchronously in-process. For persistence or
replay, subscribers can write to DeviceHistory or other stores.
"""

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("monitoring")


# ── Event Types ──────────────────────────────────────────────────────────────

class EventType(str, Enum):
    # Hardware
    HW_COMPONENT_ADDED = "hw_component_added"
    HW_COMPONENT_REMOVED = "hw_component_removed"
    HW_COMPONENT_MODIFIED = "hw_component_modified"

    # Software
    SW_INSTALLED = "sw_installed"
    SW_REMOVED = "sw_removed"
    SW_VERSION_CHANGED = "sw_version_changed"
    SW_UNAUTHORIZED = "sw_unauthorized"
    SW_ANTIVIRUS_REMOVED = "sw_antivirus_removed"

    # Health
    HEALTH_LEVEL_CHANGED = "health_level_changed"
    HEALTH_SCORE_UPDATED = "health_score_updated"

    # Alerts
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_DISMISSED = "alert_dismissed"

    # Device lifecycle
    DEVICE_REGISTERED = "device_registered"
    DEVICE_STATUS_CHANGED = "device_status_changed"
    DEVICE_APPROVED = "device_approved"
    DEVICE_BLOCKED = "device_blocked"
    DEVICE_OFFLINE = "device_offline"
    DEVICE_ONLINE = "device_online"

    # Heartbeat
    HEARTBEAT_RECEIVED = "heartbeat_received"

    # Scan
    SCAN_COMPLETED = "scan_completed"
    SCAN_SCHEDULED = "scan_scheduled"


# ── Event Data ───────────────────────────────────────────────────────────────

@dataclass
class Event:
    """A single event occurrence."""

    event_type: EventType
    client_id: Optional[int] = None
    client_key: Optional[str] = None
    hostname: Optional[str] = None
    severity: str = "info"
    title: str = ""
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "system"

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "client_id": self.client_id,
            "client_key": self.client_key,
            "hostname": self.hostname,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


# ── Event Bus ────────────────────────────────────────────────────────────────

class EventBus:
    """In-process pub/sub event bus with typed subscribers.

    Thread-safe. Subscribers are called synchronously in registration order.
    Exceptions in subscribers are logged but do not prevent other subscribers
    from being called.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._wildcard_subscribers: List[Callable] = []
        self._lock = threading.Lock()
        self._event_log: List[Event] = []
        self._max_log_size = 500

    def subscribe(self, event_type: EventType, handler: Callable):
        """Register a handler for a specific event type."""
        with self._lock:
            self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type.value)

    def subscribe_all(self, handler: Callable):
        """Register a handler that receives ALL events."""
        with self._lock:
            self._wildcard_subscribers.append(handler)
        logger.debug("Subscribed %s to all events", handler.__name__)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Remove a handler for a specific event type."""
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event: Event):
        """Publish an event to all matching subscribers.

        Subscribers are called synchronously. If a subscriber raises,
        the exception is logged and remaining subscribers still execute.
        """
        with self._lock:
            handlers = list(self._subscribers.get(event.event_type, []))
            wildcards = list(self._wildcard_subscribers)

        self._log_event(event)

        for handler in handlers + wildcards:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for event %s",
                    handler.__name__,
                    event.event_type.value,
                )

    def _log_event(self, event: Event):
        """Keep a small in-memory ring buffer of recent events."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

    def get_recent_events(self, limit: int = 50, event_type: Optional[EventType] = None) -> list:
        """Return recent events from the in-memory log."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    def subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        if event_type:
            return len(self._subscribers.get(event_type, []))
        total = sum(len(v) for v in self._subscribers.values())
        total += len(self._wildcard_subscribers)
        return total


# ── Global singleton ─────────────────────────────────────────────────────────

event_bus = EventBus()
