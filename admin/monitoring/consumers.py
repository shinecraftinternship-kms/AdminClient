import json
import logging
import time
from datetime import timedelta

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from django.utils import timezone as tz

logger = logging.getLogger("monitoring")


class AgentConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for client agents.

    Handles:
    - Agent authentication via first message (HMAC-based)
    - Heartbeat processing
    - Command dispatch (scan_now, config_update, etc.)
    - Connection lifecycle tracking
    """

    async def connect(self):
        self.agent_id = self.scope["url_route"]["kwargs"].get("agent_id", "")
        self.authenticated = False
        self.agent_secret_obj = None
        self.last_heartbeat = time.time()

        if not self.agent_id:
            await self.close(code=4001)
            return

        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "auth_required",
            "message": "Send authentication credentials",
            "agent_id": self.agent_id,
        }))

    async def disconnect(self, close_code):
        if self.authenticated and self.agent_secret_obj:
            await self._handle_disconnect()
            group_name = f"agent_{self.agent_id}"
            await self.channel_layer.group_discard(group_name, self.channel_name)
            logger.info("Agent %s disconnected (code=%s)", self.agent_id, close_code)
        else:
            logger.info("Unauthenticated client disconnected (code=%s)", close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid JSON",
            }))
            return

        msg_type = data.get("type", "")

        if not self.authenticated:
            if msg_type == "auth":
                await self._handle_auth(data)
            else:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Not authenticated. Send auth message first.",
                }))
            return

        handlers = {
            "heartbeat": self._handle_heartbeat,
            "scan_result": self._handle_scan_result,
            "event": self._handle_event,
            "status_update": self._handle_status_update,
            "pong": self._handle_pong,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(data)
        else:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}",
            }))

    async def _handle_auth(self, data):
        agent_id = data.get("agent_id", "")
        secret = data.get("secret", "")
        signature = data.get("signature", "")
        timestamp = data.get("timestamp", 0)

        if agent_id != self.agent_id:
            await self.send(text_data=json.dumps({
                "type": "auth_failed",
                "message": "Agent ID mismatch",
            }))
            return

        if not secret:
            await self.send(text_data=json.dumps({
                "type": "auth_failed",
                "message": "Missing secret",
            }))
            return

        if abs(time.time() - float(timestamp)) > 300:
            await self.send(text_data=json.dumps({
                "type": "auth_failed",
                "message": "Timestamp expired",
            }))
            return

        result = await self._verify_agent(agent_id, secret)
        if not result:
            await self.send(text_data=json.dumps({
                "type": "auth_failed",
                "message": "Invalid credentials",
            }))
            await self.close(code=4003)
            return

        self.authenticated = True
        self.agent_secret_obj = result

        group_name = f"agent_{self.agent_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)

        await self._mark_online()

        pending_commands = await self._get_pending_commands()

        await self.send(text_data=json.dumps({
            "type": "auth_success",
            "message": "Authenticated successfully",
            "server_time": tz.now().isoformat(),
            "pending_commands": pending_commands,
        }))

        await self._broadcast_agent_status("online")
        logger.info("Agent %s authenticated via WebSocket", self.agent_id)

    async def _handle_heartbeat(self, data):
        metrics = {
            "cpu_usage_pct": data.get("cpu_usage_pct", 0),
            "ram_usage_pct": data.get("ram_usage_pct", 0),
            "disk_usage_pct": data.get("disk_usage_pct", 0),
            "disk_free_gb": data.get("disk_free_gb", 0),
            "disk_total_gb": data.get("disk_total_gb", 0),
            "network_connected": data.get("network_connected", True),
            "uptime_seconds": data.get("uptime_seconds", 0),
            "load_average": data.get("load_average", 0),
            "agent_version": data.get("agent_version", ""),
            "hostname": data.get("hostname", ""),
            "current_user": data.get("current_user", ""),
        }

        result = await self._process_heartbeat(metrics)
        self.last_heartbeat = time.time()

        pending_commands = await self._get_pending_commands()

        await self.send(text_data=json.dumps({
            "type": "heartbeat_ack",
            "health_score": result.get("health_score", 0),
            "health_level": result.get("health_level", "unknown"),
            "pending_commands": pending_commands,
            "server_time": tz.now().isoformat(),
        }))

        await self._broadcast_dashboard_update({
            "type": "device_heartbeat",
            "agent_id": self.agent_id,
            "health_score": result.get("health_score", 0),
            "health_level": result.get("health_level", "unknown"),
            "cpu": metrics["cpu_usage_pct"],
            "ram": metrics["ram_usage_pct"],
            "disk": metrics["disk_usage_pct"],
            "timestamp": tz.now().isoformat(),
        })

        for cmd in pending_commands:
            await self.send(text_data=json.dumps({
                "type": "command",
                "command_type": cmd["command_type"],
                "command_id": cmd["command_id"],
                "payload": cmd.get("payload", {}),
            }))

    async def _handle_scan_result(self, data):
        scan_type = data.get("scan_type", "scheduled")
        scan_data = data.get("scan_data", {})

        result = await self._submit_scan_result(scan_type, scan_data)

        await self.send(text_data=json.dumps({
            "type": "scan_ack",
            "status": "ok" if result else "error",
            "message": "Scan results received" if result else "Failed to store scan results",
        }))

        if result:
            await self._broadcast_dashboard_update({
                "type": "scan_completed",
                "agent_id": self.agent_id,
                "scan_type": scan_type,
                "timestamp": tz.now().isoformat(),
            })

    async def _handle_event(self, data):
        event_type = data.get("event_type", "")
        event_data = data.get("event_data", {})
        severity = data.get("severity", "info")

        await self._store_event(event_type, event_data, severity)

        await self._broadcast_dashboard_update({
            "type": "device_event",
            "agent_id": self.agent_id,
            "event_type": event_type,
            "severity": severity,
            "timestamp": tz.now().isoformat(),
        })

        if severity in ("warning", "critical"):
            await self._broadcast_alert({
                "agent_id": self.agent_id,
                "event_type": event_type,
                "severity": severity,
                "details": event_data,
                "timestamp": tz.now().isoformat(),
            })

    async def _handle_status_update(self, data):
        await self._update_agent_status(data)
        await self._broadcast_dashboard_update({
            "type": "device_status_update",
            "agent_id": self.agent_id,
            "status": data.get("status", ""),
            "timestamp": tz.now().isoformat(),
        })

    async def _handle_pong(self, data):
        self.last_heartbeat = time.time()

    async def _handle_disconnect(self):
        await self._mark_offline()
        await self._broadcast_agent_status("offline")

    # ── Outbound commands (server → agent) ──

    async def send_command(self, event):
        command = event.get("command", {})
        await self.send(text_data=json.dumps({
            "type": "command",
            "command_type": command.get("command_type", ""),
            "command_id": command.get("command_id", ""),
            "payload": command.get("payload", {}),
        }))

    async def send_ping(self, event):
        await self.send(text_data=json.dumps({
            "type": "ping",
            "server_time": tz.now().isoformat(),
        }))

    # ── Database helpers ──

    @database_sync_to_async
    def _verify_agent(self, agent_id, secret):
        from monitoring.models import AgentSecret
        try:
            return AgentSecret.objects.select_related("client").get(
                agent_id=agent_id, secret_key=secret, is_active=True
            )
        except AgentSecret.DoesNotExist:
            return None

    @database_sync_to_async
    def _mark_online(self):
        if not self.agent_secret_obj:
            return
        from monitoring.models import DeviceMonitoringInfo
        client = self.agent_secret_obj.client
        client.status = "online"
        client.last_seen = tz.now()
        client.save(update_fields=["status", "last_seen"])
        info, _ = DeviceMonitoringInfo.objects.get_or_create(
            client=client, defaults={"monitoring_status": "online"}
        )
        info.monitoring_status = "online"
        info.last_heartbeat = tz.now()
        info.save(update_fields=["monitoring_status", "last_heartbeat", "updated_at"])

    @database_sync_to_async
    def _mark_offline(self):
        if not self.agent_secret_obj:
            return
        from monitoring.models import DeviceMonitoringInfo
        client = self.agent_secret_obj.client
        try:
            info = DeviceMonitoringInfo.objects.get(client=client)
            if info.monitoring_status == "online":
                info.monitoring_status = "offline"
                info.save(update_fields=["monitoring_status", "updated_at"])
        except DeviceMonitoringInfo.DoesNotExist:
            pass

    @database_sync_to_async
    def _process_heartbeat(self, metrics):
        if not self.agent_secret_obj:
            return {"health_score": 0, "health_level": "unknown"}
        from monitoring.models import (
            DeviceHeartbeat, DeviceMonitoringInfo, SoftwareInventory, DeviceHistory,
        )
        from monitoring.health import calculate_health_score
        from monitoring.alerts import check_and_create_alerts
        from django.db.models import F

        client = self.agent_secret_obj.client

        hb = DeviceHeartbeat.objects.create(
            client=client,
            cpu_usage_pct=metrics.get("cpu_usage_pct", 0),
            ram_usage_pct=metrics.get("ram_usage_pct", 0),
            disk_usage_pct=metrics.get("disk_usage_pct", 0),
            disk_free_gb=metrics.get("disk_free_gb", 0),
            disk_total_gb=metrics.get("disk_total_gb", 0),
            network_connected=metrics.get("network_connected", True),
            uptime_seconds=metrics.get("uptime_seconds", 0),
            load_average=metrics.get("load_average", 0),
            agent_version=metrics.get("agent_version", ""),
        )

        client.status = "online"
        client.last_seen = tz.now()
        if metrics.get("agent_version"):
            client.client_version = metrics["agent_version"]
        client.save(update_fields=["status", "last_seen", "client_version"])

        sw_data = list(SoftwareInventory.objects.filter(
            client=client, is_present=True
        ).values("name", "version", "publisher")[:200])

        score, level = calculate_health_score(
            {
                "cpu_usage_pct": metrics.get("cpu_usage_pct", 0),
                "ram_usage_pct": metrics.get("ram_usage_pct", 0),
                "disk_usage_pct": metrics.get("disk_usage_pct", 0),
                "network_connected": metrics.get("network_connected", True),
            },
            sw_data,
        )

        info, _ = DeviceMonitoringInfo.objects.get_or_create(
            client=client, defaults={"monitoring_status": "online"}
        )
        info.health_score = score
        info.health_level = level
        info.last_heartbeat = tz.now()
        info.heartbeat_count = F("heartbeat_count") + 1
        info.monitoring_status = "online"
        if metrics.get("agent_version"):
            info.agent_version = metrics["agent_version"]
        if metrics.get("hostname"):
            client.hostname = metrics["hostname"]
            client.save(update_fields=["hostname"])
        if metrics.get("current_user"):
            info.current_user = metrics["current_user"]
        info.save(update_fields=[
            "health_score", "health_level", "last_heartbeat",
            "heartbeat_count", "monitoring_status", "agent_version",
            "current_user", "updated_at",
        ])

        check_and_create_alerts(client, hb, sw_data)

        return {"health_score": score, "health_level": level}

    @database_sync_to_async
    def _get_pending_commands(self):
        if not self.agent_secret_obj:
            return []
        from monitoring.models import DeviceMonitoringInfo
        client = self.agent_secret_obj.client
        try:
            info = DeviceMonitoringInfo.objects.get(client=client)
            return info.notes.split(";") if info.notes else []
        except DeviceMonitoringInfo.DoesNotExist:
            return []

    @database_sync_to_async
    def _submit_scan_result(self, scan_type, scan_data):
        if not self.agent_secret_obj:
            return False
        from scanner_api.models import ScanResult
        client = self.agent_secret_obj.client
        try:
            ScanResult.objects.create(
                client=client,
                scan_type=scan_type,
                scan_data=scan_data,
            )
            client.last_seen = tz.now()
            client.save(update_fields=["last_seen"])
            return True
        except Exception as e:
            logger.error("Failed to store scan result: %s", e)
            return False

    @database_sync_to_async
    def _store_event(self, event_type, event_data, severity):
        if not self.agent_secret_obj:
            return
        from monitoring.models import DeviceHistory, DeviceAlert
        client = self.agent_secret_obj.client
        DeviceHistory.objects.create(
            client=client,
            category="security_event" if severity == "critical" else "status_change",
            event_type=event_type,
            description=event_data.get("description", event_type),
            severity=severity,
            new_value=event_data,
            source="agent",
        )
        if severity in ("warning", "critical"):
            DeviceAlert.objects.create(
                client=client,
                alert_type=event_type,
                severity=severity,
                title=event_data.get("title", event_type),
                message=event_data.get("message", ""),
                details=event_data,
            )

    @database_sync_to_async
    def _update_agent_status(self, data):
        if not self.agent_secret_obj:
            return
        from monitoring.models import DeviceMonitoringInfo
        client = self.agent_secret_obj.client
        info, _ = DeviceMonitoringInfo.objects.get_or_create(
            client=client, defaults={"monitoring_status": "online"}
        )
        new_status = data.get("status", "")
        if new_status:
            info.monitoring_status = new_status
            info.save(update_fields=["monitoring_status", "updated_at"])

    # ── Broadcasting helpers ──

    async def _broadcast_agent_status(self, status):
        channel_layer = get_channel_layer()
        await channel_layer.group_send("dashboard", {
            "type": "dashboard.agent_status",
            "data": {
                "type": "agent_status",
                "agent_id": self.agent_id,
                "status": status,
                "timestamp": tz.now().isoformat(),
            },
        })

    async def _broadcast_dashboard_update(self, data):
        channel_layer = get_channel_layer()
        await channel_layer.group_send("dashboard", {
            "type": "dashboard.update",
            "data": data,
        })

    async def _broadcast_alert(self, alert_data):
        channel_layer = get_channel_layer()
        await channel_layer.group_send("dashboard", {
            "type": "dashboard.alert",
            "data": {
                "type": "new_alert",
                **alert_data,
            },
        })


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for admin dashboard.

    Receives real-time updates about agents, alerts, and system status.
    """

    async def connect(self):
        self.user = self.scope.get("user")

        if self.user and self.user.is_authenticated:
            await self.accept()
            await self.channel_layer.group_add("dashboard", self.channel_name)
            await self.send(text_data=json.dumps({
                "type": "connected",
                "message": "Dashboard connected to real-time updates",
                "server_time": tz.now().isoformat(),
            }))
            logger.info("Dashboard user %s connected via WebSocket", self.user.username)
        else:
            await self.accept()
            await self.channel_layer.group_add("dashboard", self.channel_name)
            await self.send(text_data=json.dumps({
                "type": "connected",
                "message": "Dashboard connected (read-only mode)",
                "server_time": tz.now().isoformat(),
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("dashboard", self.channel_name)
        logger.info("Dashboard client disconnected (code=%s)", close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({
                "type": "pong",
                "server_time": tz.now().isoformat(),
            }))
        elif msg_type == "subscribe_device":
            device_id = data.get("device_id", "")
            if device_id:
                group_name = f"device_{device_id}"
                await self.channel_layer.group_add(group_name, self.channel_name)
                await self.send(text_data=json.dumps({
                    "type": "subscribed",
                    "device_id": device_id,
                }))
        elif msg_type == "unsubscribe_device":
            device_id = data.get("device_id", "")
            if device_id:
                group_name = f"device_{device_id}"
                await self.channel_layer.group_discard(group_name, self.channel_name)
                await self.send(text_data=json.dumps({
                    "type": "unsubscribed",
                    "device_id": device_id,
                }))

    # ── Inbound message handlers from group_send ──

    async def dashboard_update(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))

    async def dashboard_agent_status(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))

    async def dashboard_alert(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))

    async def device_update(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))
