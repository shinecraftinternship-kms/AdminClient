import json
import time
import hmac
import hashlib
import logging
import random
import threading
import urllib.request
import urllib.error

logger = logging.getLogger("client")


class Communicator:
    """Handles HTTP communication with the admin server.

    Includes automatic retry with exponential backoff and jitter,
    plus an offline queue for events that fail to send.
    """

    def __init__(self, admin_url, max_retries=3, base_delay=1.0, max_delay=30.0):
        self.admin_url = admin_url.rstrip("/")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._offline_queue = []
        self._offline_lock = threading.Lock()
        self._consecutive_failures = 0

    def _request(self, method, path, data=None, timeout=30, extra_headers=None,
                 _retries=None):
        """Make an HTTP request with retry and exponential backoff.

        Retries on connection errors and 5xx responses. Does NOT retry
        on 4xx (client errors) except 429 (rate limit).
        """
        retries = _retries if _retries is not None else self.max_retries
        url = f"{self.admin_url}{path}"
        headers = {"Content-Type": "application/json", "User-Agent": "SystemScannerClient/1.0"}
        if extra_headers:
            headers.update(extra_headers)
        body = json.dumps(data).encode("utf-8") if data else None

        last_error = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = resp.read().decode("utf-8")
                    self._consecutive_failures = 0
                    if resp_data:
                        return json.loads(resp_data)
                    return {"status": "ok"}
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    last_error = e
                    if attempt < retries:
                        delay = self._backoff_delay(attempt)
                        logger.debug("HTTP %d on %s, retry %d/%d in %.1fs",
                                     e.code, path, attempt + 1, retries, delay)
                        time.sleep(delay)
                        continue
                try:
                    err_data = e.read().decode("utf-8")
                    return json.loads(err_data)
                except Exception:
                    return {"status": "error", "message": f"HTTP {e.code}"}
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                last_error = e
                if attempt < retries:
                    delay = self._backoff_delay(attempt)
                    logger.debug("Connection error on %s: %s, retry %d/%d in %.1fs",
                                 path, e, attempt + 1, retries, delay)
                    time.sleep(delay)
                    continue
            except Exception as e:
                last_error = e
                if attempt < retries:
                    delay = self._backoff_delay(attempt)
                    logger.debug("Error on %s: %s, retry %d/%d in %.1fs",
                                 path, e, attempt + 1, retries, delay)
                    time.sleep(delay)
                    continue

        self._consecutive_failures += 1
        if last_error:
            if isinstance(last_error, urllib.error.URLError):
                return {"status": "error", "message": f"Connection failed: {last_error.reason}"}
            return {"status": "error", "message": str(last_error)}
        return {"status": "error", "message": "Max retries exceeded"}

    def _backoff_delay(self, attempt):
        """Exponential backoff with jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0, delay * 0.3)
        return delay + jitter

    @property
    def is_online(self):
        """True if recent requests have been succeeding."""
        return self._consecutive_failures < 3

    def queue_offline(self, event_data):
        """Queue an event for later delivery when back online."""
        with self._offline_lock:
            self._offline_queue.append({
                "data": event_data,
                "queued_at": time.time(),
                "attempts": 0,
            })
            if len(self._offline_queue) > 500:
                self._offline_queue = self._offline_queue[-500:]

    def flush_offline_queue(self, key):
        """Send all queued offline events. Returns count of sent events."""
        sent = 0
        with self._offline_lock:
            pending = list(self._offline_queue)
            self._offline_queue.clear()

        for item in pending:
            item["attempts"] += 1
            if item["attempts"] > 5:
                continue
            result = self._request("POST", "/api/scan", item["data"], timeout=30)
            if result.get("status") == "ok":
                sent += 1
            else:
                with self._offline_lock:
                    self._offline_queue.append(item)

        return sent

    def register(self, key, hostname, platform_name, client_version="", device_fingerprint=""):
        return self._request("POST", "/api/register", {
            "registration_key": key,
            "hostname": hostname,
            "platform": platform_name,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint,
        })

    def ping(self, key, hostname, client_version="", device_fingerprint=""):
        return self._request("POST", "/api/ping", {
            "registration_key": key,
            "hostname": hostname,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint,
        })

    def fetch_latest_scan(self, key):
        return self._request("GET", f"/api/clients/{key}/scan-results")

    def check_status(self, key):
        return self._request("GET", f"/api/clients/{key}/status")

    def submit_scan(self, key, scan_data):
        payload = {"registration_key": key, "scan_type": "scheduled", **scan_data}
        return self._request("POST", "/api/scan", payload, timeout=120)

    def get_scan_config(self, key):
        return self._request("GET", f"/api/clients/{key}/scan-config")

    def update_admin_url(self, url):
        self.admin_url = url.rstrip("/")

    def is_reachable(self, url=None):
        try:
            target = url or self.admin_url
            req = urllib.request.Request(f"{target}/api/clients", method="GET")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def monitor_register(self, agent_id, fingerprint, hostname, platform_name, version):
        return self._request("POST", "/api/monitoring/agent/register", {
            "agent_id": agent_id,
            "fingerprint": fingerprint,
            "hostname": hostname,
            "platform": platform_name,
            "agent_version": version,
        })

    def monitor_heartbeat(self, agent_id, signature, timestamp, heartbeat_data):
        return self._request("POST", "/api/monitoring/agent/heartbeat", heartbeat_data,
                             extra_headers={
                                 "X-Agent-ID": agent_id,
                                 "X-Signature": signature,
                                 "X-Timestamp": str(timestamp),
                             })

    def monitor_inventory(self, agent_id, signature, timestamp, hw_data, sw_data):
        return self._request("POST", "/api/monitoring/agent/inventory",
                             {"hardware": hw_data, "software": sw_data},
                             extra_headers={
                                 "X-Agent-ID": agent_id,
                                 "X-Signature": signature,
                                 "X-Timestamp": str(timestamp),
                             })

    def monitor_version_check(self, current_version):
        return self._request("GET", f"/api/monitoring/agent/version-check?v={current_version}")

    def get_ws_url(self):
        """Convert HTTP admin URL to WebSocket URL."""
        url = self.admin_url
        if url.startswith("https://"):
            return "wss://" + url[8:]
        elif url.startswith("http://"):
            return "ws://" + url[5:]
        return "ws://" + url


class WebSocketClient:
    """Async WebSocket client for real-time agent communication.

    Connects to the admin server's WebSocket endpoint and handles:
    - Authentication
    - Heartbeat sending
    - Command receiving
    - Automatic reconnection
    """

    def __init__(self, admin_url, agent_id, secret_key, on_command=None):
        self.admin_url = admin_url.rstrip("/")
        self.agent_id = agent_id
        self.secret_key = secret_key
        self.on_command = on_command
        self.ws = None
        self.connected = False
        self.authenticated = False
        self._stop_event = threading.Event()
        self._thread = None
        self._reconnect_delay = 2
        self._max_reconnect_delay = 60
        self._message_queue = []
        self._queue_lock = threading.Lock()

    def start(self):
        """Start the WebSocket client in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("WebSocket client thread started")

    def stop(self):
        """Stop the WebSocket client."""
        self._stop_event.set()
        if self.ws:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.ws.close())
                loop.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("WebSocket client stopped")

    def send_message(self, msg_type, data=None):
        """Queue a message to be sent."""
        with self._queue_lock:
            self._message_queue.append({"type": msg_type, **(data or {})})

    def _run_loop(self):
        """Main reconnection loop."""
        try:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
        except ImportError:
            logger.error("asyncio not available")
            return

        while not self._stop_event.is_set():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._connect_and_run())
            except Exception as e:
                logger.error("WebSocket loop error: %s", e)
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

            if not self._stop_event.is_set():
                logger.info("Reconnecting in %ds...", self._reconnect_delay)
                self._stop_event.wait(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

    async def _connect_and_run(self):
        import websockets
        import asyncio

        ws_url = self._get_ws_url()
        logger.info("Connecting to %s", ws_url)

        async with websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self.ws = ws
            self.connected = True
            self._reconnect_delay = 2
            logger.info("WebSocket connected")

            await self._authenticate(ws)

            send_task = asyncio.create_task(self._send_loop(ws))
            recv_task = asyncio.create_task(self._recv_loop(ws))

            done, pending = await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            self.connected = False
            self.authenticated = False

    async def _authenticate(self, ws):
        import time as _time

        auth_msg = {
            "type": "auth",
            "agent_id": self.agent_id,
            "secret": self.secret_key,
            "timestamp": str(_time.time()),
        }
        await ws.send(json.dumps(auth_msg))
        logger.info("Authentication message sent")

    async def _send_loop(self, ws):
        import asyncio

        while not self._stop_event.is_set():
            with self._queue_lock:
                messages = list(self._message_queue)
                self._message_queue.clear()

            for msg in messages:
                try:
                    await ws.send(json.dumps(msg))
                except Exception as e:
                    logger.error("Failed to send message: %s", e)
                    return

            await asyncio.sleep(0.1)

    async def _recv_loop(self, ws):
        import asyncio

        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received")
        except Exception as e:
            logger.error("Receive loop error: %s", e)

    async def _handle_message(self, data):
        msg_type = data.get("type", "")

        if msg_type == "auth_success":
            self.authenticated = True
            logger.info("WebSocket authenticated successfully")
            pending = data.get("pending_commands", [])
            for cmd in pending:
                if self.on_command:
                    self.on_command(cmd)

        elif msg_type == "auth_failed":
            logger.error("Authentication failed: %s", data.get("message", ""))
            self.connected = False

        elif msg_type == "command":
            cmd_type = data.get("command_type", "")
            cmd_id = data.get("command_id", "")
            payload = data.get("payload", {})
            logger.info("Received command: %s (id=%s)", cmd_type, cmd_id)
            if self.on_command:
                self.on_command({
                    "command_type": cmd_type,
                    "command_id": cmd_id,
                    "payload": payload,
                })

        elif msg_type == "ping":
            self.send_message("pong")

        elif msg_type == "heartbeat_ack":
            health = data.get("health_level", "unknown")
            score = data.get("health_score", 0)
            logger.debug("Heartbeat ACK: health=%s score=%d", health, score)

    def _get_ws_url(self):
        url = self.admin_url
        if url.startswith("https://"):
            base = "wss://" + url[8:]
        elif url.startswith("http://"):
            base = "ws://" + url[5:]
        else:
            base = "ws://" + url
        return f"{base}/ws/agent/{self.agent_id}/"
