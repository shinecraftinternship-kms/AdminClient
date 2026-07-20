"""Central event dispatcher for client-side monitoring.

Queues events from all monitors, batches them, and sends to the server
via WebSocket (preferred) or HTTP (fallback).

When offline, events are persisted to disk so they survive restarts
and are replayed when connectivity returns.
"""

import os
import time
import json
import hmac
import hashlib
import logging
import threading
from collections import deque
from pathlib import Path

logger = logging.getLogger("client.events.dispatcher")

OFFLINE_QUEUE_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "SystemScannerPro", "offline_events",
)


class EventDispatcher:
    """Central event queue that collects events from all monitors.

    Events are batched and sent at configurable intervals to reduce
    network overhead. Supports both WebSocket and HTTP transport.
    Failed batches are persisted to disk for retry on reconnect.
    """

    def __init__(self, ws_client=None, http_comm=None, client_key=None,
                 batch_interval=5, max_batch_size=50):
        self.ws_client = ws_client
        self.http_comm = http_comm
        self.client_key = client_key
        self.batch_interval = batch_interval
        self.max_batch_size = max_batch_size

        self._queue = deque()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._monitoring_agent_id = None
        self._monitoring_secret = None
        self._stats = {
            "total_events": 0,
            "events_sent": 0,
            "events_failed": 0,
            "events_diskqueued": 0,
            "events_replayed": 0,
            "batches_sent": 0,
        }

        os.makedirs(OFFLINE_QUEUE_DIR, exist_ok=True)
        self._replay_disk_queue()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Event dispatcher started (batch interval: %ds)", self.batch_interval)

    def stop(self):
        self._stop.set()
        self._flush_now()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Event dispatcher stopped (stats: %s)", self._stats)

    def dispatch(self, event):
        """Add an event to the queue for batched sending."""
        event["_timestamp"] = time.time()
        with self._lock:
            self._queue.append(event)
            self._stats["total_events"] += 1

        queue_size = len(self._queue)
        if queue_size >= self.max_batch_size:
            threading.Thread(target=self._flush_now, daemon=True).start()

    def set_ws_client(self, ws_client):
        self.ws_client = ws_client

    def set_http_comm(self, http_comm, client_key):
        self.http_comm = http_comm
        self.client_key = client_key

    def set_monitoring_credentials(self, agent_id, secret):
        self._monitoring_agent_id = agent_id
        self._monitoring_secret = secret

    def get_stats(self):
        with self._lock:
            return dict(self._stats)

    def _run(self):
        while not self._stop.is_set():
            self._stop.wait(self.batch_interval)
            if not self._stop.is_set():
                self._flush_now()

    def _flush_now(self):
        with self._lock:
            if not self._queue:
                return
            batch = []
            while self._queue and len(batch) < self.max_batch_size:
                batch.append(self._queue.popleft())

        if not batch:
            return

        success = self._send_batch(batch)
        with self._lock:
            if success:
                self._stats["events_sent"] += len(batch)
                self._stats["batches_sent"] += 1
            else:
                self._stats["events_failed"] += len(batch)
                self._persist_to_disk(batch)

    def _send_batch(self, batch):
        if self.ws_client and self.ws_client.connected and self.ws_client.authenticated:
            return self._send_via_websocket(batch)
        elif self.http_comm and self.client_key:
            return self._send_via_http(batch)
        else:
            logger.warning("No transport available, %d events disk-queued", len(batch))
            return False

    def _send_via_websocket(self, batch):
        try:
            for event in batch:
                msg = {
                    "type": "event",
                    "event_type": event.get("event_type", "unknown"),
                    "severity": event.get("severity", "info"),
                    "event_data": event.get("event_data", {}),
                }
                self.ws_client.send_message("event", msg)
            logger.debug("Sent %d events via WebSocket", len(batch))
            return True
        except Exception as e:
            logger.error("WebSocket send failed: %s", e)
            return False

    def _send_via_http(self, batch):
        if not self._monitoring_agent_id or not self._monitoring_secret:
            logger.warning("No monitoring credentials, disk-queuing %d events", len(batch))
            return False
        try:
            for event in batch:
                payload = {
                    "registration_key": self.client_key,
                    "event_type": event.get("event_type", "unknown"),
                    "severity": event.get("severity", "info"),
                    "event_data": event.get("event_data", {}),
                }
                body = json.dumps(payload).encode("utf-8")
                sig = hmac.new(
                    self._monitoring_secret.encode("utf-8"), body,
                    hashlib.sha256,
                ).hexdigest()
                self.http_comm._request("POST", "/api/monitoring/agent/heartbeat", payload,
                                        extra_headers={
                                            "X-Agent-ID": self._monitoring_agent_id,
                                            "X-Signature": sig,
                                            "X-Timestamp": str(time.time()),
                                        })
            logger.debug("Sent %d events via HTTP", len(batch))
            return True
        except Exception as e:
            logger.error("HTTP send failed: %s", e)
            return False

    def _persist_to_disk(self, batch):
        """Write failed batch to a timestamped JSON file on disk."""
        try:
            ts = int(time.time() * 1000)
            path = os.path.join(OFFLINE_QUEUE_DIR, f"batch_{ts}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(batch, f, default=str)
            self._stats["events_diskqueued"] += len(batch)
            logger.info("Persisted %d events to %s", len(batch), path)
        except Exception as e:
            logger.error("Failed to persist events to disk: %s", e)

    def _replay_disk_queue(self):
        """Load and replay any events persisted from a previous session."""
        try:
            files = sorted(Path(OFFLINE_QUEUE_DIR).glob("batch_*.json"))
            replayed = 0
            for path in files:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        batch = json.load(f)
                    if batch:
                        with self._lock:
                            for event in batch:
                                self._queue.append(event)
                        replayed += len(batch)
                    path.unlink()
                except Exception:
                    pass

            if replayed:
                self._stats["events_replayed"] = replayed
                logger.info("Replayed %d events from disk queue", replayed)
        except Exception as e:
            logger.error("Failed to replay disk queue: %s", e)
