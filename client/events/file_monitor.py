"""File system monitoring using watchdog.

Monitors critical system paths for suspicious changes:
- New driver files
- System file modifications
- Configuration changes
"""

import sys
import os
import time
import logging
import threading

logger = logging.getLogger("client.events.file_monitor")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent, FileMovedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logger.warning("watchdog not installed - file monitoring disabled")


MONITOR_PATHS_WINDOWS = [
    os.path.expandvars(r"%SystemRoot%\System32\drivers"),
    os.path.expandvars(r"%SystemRoot%\System32"),
]

MONITOR_PATHS_LINUX = [
    "/etc",
    "/usr/lib/modules",
    "/usr/lib/systemd",
]

MONITOR_PATHS_DARWIN = [
    "/Library/Extensions",
    "/Library/LaunchDaemons",
    "/Library/LaunchAgents",
    "/etc",
]

CRITICAL_EXTENSIONS = {
    ".sys", ".dll", ".drv", ".inf", ".cat",
    ".ko", ".so", ".dylib",
    ".conf", ".cfg", ".ini", ".plist",
    ".exe", ".sh", ".command",
}

CRITICAL_FILENAMES = {
    "hosts", "passwd", "shadow", "sudoers",
    "sshd_config", "firewalld.conf",
}


def get_monitor_paths():
    if sys.platform == "win32":
        return [p for p in MONITOR_PATHS_WINDOWS if os.path.isdir(p)]
    elif sys.platform == "linux":
        return [p for p in MONITOR_PATHS_LINUX if os.path.isdir(p)]
    elif sys.platform == "darwin":
        return [p for p in MONITOR_PATHS_DARWIN if os.path.isdir(p)]
    return []


def _is_critical_path(filepath):
    """Check if a file path is in a critical system location."""
    _, ext = os.path.splitext(filepath)
    if ext.lower() in CRITICAL_EXTENSIONS:
        return True
    basename = os.path.basename(filepath).lower()
    if basename in CRITICAL_FILENAMES:
        return True
    return False


class CriticalFileHandler(FileSystemEventHandler):
    """Handles watchdog events for critical system files."""

    def __init__(self, on_event=None, debounce_seconds=2):
        self.on_event = on_event
        self._debounce = debounce_seconds
        self._recent_events = {}
        self._lock = threading.Lock()

    def _should_report(self, filepath, event_type):
        key = f"{event_type}:{filepath}"
        now = time.time()
        with self._lock:
            last = self._recent_events.get(key, 0)
            if now - last < self._debounce:
                return False
            self._recent_events[key] = now
            if len(self._recent_events) > 1000:
                cutoff = now - 300
                self._recent_events = {
                    k: v for k, v in self._recent_events.items() if v > cutoff
                }
        return True

    def on_created(self, event):
        if event.is_directory:
            return
        if not _is_critical_path(event.src_path):
            return
        if not self._should_report(event.src_path, "created"):
            return

        evt = {
            "event_type": "file_created",
            "severity": "warning",
            "event_data": {
                "path": event.src_path,
                "description": f"Critical file created: {event.src_path}",
                "title": "Critical File Created",
            },
        }
        if self.on_event:
            self.on_event(evt)

    def on_modified(self, event):
        if event.is_directory:
            return
        if not _is_critical_path(event.src_path):
            return
        if not self._should_report(event.src_path, "modified"):
            return

        evt = {
            "event_type": "file_modified",
            "severity": "warning",
            "event_data": {
                "path": event.src_path,
                "description": f"Critical file modified: {event.src_path}",
                "title": "Critical File Modified",
            },
        }
        if self.on_event:
            self.on_event(evt)

    def on_deleted(self, event):
        if event.is_directory:
            return
        if not _is_critical_path(event.src_path):
            return
        if not self._should_report(event.src_path, "deleted"):
            return

        evt = {
            "event_type": "file_deleted",
            "severity": "critical",
            "event_data": {
                "path": event.src_path,
                "description": f"Critical file deleted: {event.src_path}",
                "title": "Critical File Deleted",
            },
        }
        if self.on_event:
            self.on_event(evt)

    def on_moved(self, event):
        if event.is_directory:
            return
        if not _is_critical_path(event.src_path) and not _is_critical_path(event.dest_path):
            return
        if not self._should_report(event.src_path, "moved"):
            return

        evt = {
            "event_type": "file_moved",
            "severity": "warning",
            "event_data": {
                "source": event.src_path,
                "destination": event.dest_path,
                "description": f"Critical file moved: {event.src_path} -> {event.dest_path}",
                "title": "Critical File Moved",
            },
        }
        if self.on_event:
            self.on_event(evt)


class FileMonitor:
    """Watches critical system paths for file changes using watchdog."""

    def __init__(self, on_event=None):
        self.on_event = on_event
        self._observer = None
        self._thread = None
        self._running = False

    def start(self):
        if not HAS_WATCHDOG:
            logger.warning("Cannot start file monitor: watchdog not installed")
            return

        paths = get_monitor_paths()
        if not paths:
            logger.warning("No monitorable paths found")
            return

        handler = CriticalFileHandler(on_event=self.on_event)
        self._observer = Observer()

        for path in paths:
            try:
                self._observer.schedule(handler, path, recursive=True)
                logger.info("Watching: %s", path)
            except Exception as e:
                logger.error("Failed to watch %s: %s", path, e)

        self._running = True
        self._observer.start()
        logger.info("File monitor started on %d paths", len(paths))

    def stop(self):
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._running = False
            logger.info("File monitor stopped")
