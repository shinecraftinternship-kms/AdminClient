# API Route Constants
API_REGISTER = "/api/register"
API_APPROVE = "/api/approve"
API_APPROVE_MULTIPLE = "/api/approve-multiple"
API_PING = "/api/ping"
API_SCAN = "/api/scan"
API_CLIENTS = "/api/clients"
API_CLIENT_DETAIL = "/api/clients/<key>"
API_CLIENT_STATUS = "/api/clients/<key>/status"
API_MANUAL_UPDATE = "/api/clients/<key>/manual"
API_ADDONS = "/api/clients/<key>/addons"
API_ADDON_DELETE = "/api/clients/<key>/addons/<addon_id>"
API_SCAN_CONFIG = "/api/clients/<key>/scan-config"
API_TRIGGER_SCAN = "/api/clients/<key>/scan-now"
API_SCAN_RESULTS = "/api/clients/<key>/scan-results"
API_SCAN_LOCAL = "/api/scan/local"
API_SCAN_ALL = "/api/scan/all"
API_DELETE_CLIENT = "/api/clients/<key>"
API_DELETE_MULTIPLE = "/api/clients/delete-multiple"
API_ADMIN_CLIENT = "/api/admin-client"
API_ACTIVITY_LOG = "/api/activity-log"
API_GROUPS = "/api/groups"
API_GROUP_DELETE = "/api/groups/<group_id>"
API_SETTINGS = "/api/settings"

KEY_LENGTH = 8
HEARTBEAT_INTERVAL = 30
DEFAULT_SCAN_INTERVAL = 3600
CLIENT_VERSION = "1.0.0"

# Monitoring API Routes
API_MONITORING_REGISTER = "/api/monitoring/agent/register"
API_MONITORING_HEARTBEAT = "/api/monitoring/agent/heartbeat"
API_MONITORING_INVENTORY = "/api/monitoring/agent/inventory"
API_MONITORING_VERSION_CHECK = "/api/monitoring/agent/version-check"
API_MONITORING_DASHBOARD = "/api/monitoring/dashboard"
API_MONITORING_DEVICES = "/api/monitoring/devices"
API_MONITORING_ALERTS = "/api/monitoring/alerts"

# WebSocket Routes
WS_AGENT_TEMPLATE = "ws/agent/{agent_id}/"
WS_DASHBOARD = "ws/dashboard/"

# WebSocket Message Types
WS_MSG_AUTH = "auth"
WS_MSG_AUTH_SUCCESS = "auth_success"
WS_MSG_AUTH_FAILED = "auth_failed"
WS_MSG_HEARTBEAT = "heartbeat"
WS_MSG_HEARTBEAT_ACK = "heartbeat_ack"
WS_MSG_COMMAND = "command"
WS_MSG_SCAN_RESULT = "scan_result"
WS_MSG_EVENT = "event"
WS_MSG_PING = "ping"
WS_MSG_PONG = "pong"

# Command Types
CMD_SCAN_NOW = "scan_now"
CMD_CONFIG_UPDATE = "config_update"
CMD_PING = "ping"
