import json
import logging
import asyncio

from channels.layers import get_channel_layer

logger = logging.getLogger("monitoring")


def _get_channel_layer():
    return get_channel_layer()


def send_to_agent_sync(agent_id, command_type, payload=None, command_id=None):
    """Send a command to a specific agent via WebSocket (sync wrapper)."""
    try:
        channel_layer = _get_channel_layer()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                _send_to_agent(channel_layer, agent_id, command_type, payload, command_id)
            )
        else:
            loop.run_until_complete(
                _send_to_agent(channel_layer, agent_id, command_type, payload, command_id)
            )
    except Exception as e:
        logger.error("Failed to send command to agent %s: %s", agent_id, e)


async def _send_to_agent(channel_layer, agent_id, command_type, payload, command_id):
    import uuid as _uuid
    group_name = f"agent_{agent_id}"
    cmd_id = command_id or str(_uuid.uuid4())
    await channel_layer.group_send(group_name, {
        "type": "send_command",
        "command": {
            "command_type": command_type,
            "command_id": cmd_id,
            "payload": payload or {},
        },
    })
    logger.info("Sent command %s to agent %s", command_type, agent_id)


def notify_agent(agent_id, command_type, payload=None, command_id=None):
    """Send a command to a specific agent via WebSocket.

    This is the primary API for dispatching commands to agents.
    Commands are queued if the agent is offline and delivered on reconnect.
    """
    send_to_agent_sync(agent_id, command_type, payload, command_id)


def broadcast_to_dashboard(event_type, data):
    """Push a real-time update to all connected dashboard clients."""
    try:
        channel_layer = _get_channel_layer()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                _broadcast(channel_layer, event_type, data)
            )
        else:
            loop.run_until_complete(
                _broadcast(channel_layer, event_type, data)
            )
    except Exception as e:
        logger.error("Failed to broadcast to dashboard: %s", e)


async def _broadcast(channel_layer, event_type, data):
    await channel_layer.group_send("dashboard", {
        "type": "dashboard.update",
        "data": {
            "type": event_type,
            **data,
        },
    })


def broadcast_alert(alert_data):
    """Push a new alert to all connected dashboard clients."""
    try:
        channel_layer = _get_channel_layer()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                _broadcast_alert(channel_layer, alert_data)
            )
        else:
            loop.run_until_complete(
                _broadcast_alert(channel_layer, alert_data)
            )
    except Exception as e:
        logger.error("Failed to broadcast alert: %s", e)


async def _broadcast_alert(channel_layer, alert_data):
    await channel_layer.group_send("dashboard", {
        "type": "dashboard.alert",
        "data": {
            "type": "new_alert",
            **alert_data,
        },
    })


def send_device_update(device_id, data):
    """Push an update for a specific device to subscribers."""
    try:
        channel_layer = _get_channel_layer()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                _send_device_update(channel_layer, device_id, data)
            )
        else:
            loop.run_until_complete(
                _send_device_update(channel_layer, device_id, data)
            )
    except Exception as e:
        logger.error("Failed to send device update: %s", e)


async def _send_device_update(channel_layer, device_id, data):
    group_name = f"device_{device_id}"
    await channel_layer.group_send(group_name, {
        "type": "device.update",
        "data": data,
    })
