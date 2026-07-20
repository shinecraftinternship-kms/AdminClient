/**
 * Dashboard WebSocket Client
 *
 * Connects to ws/dashboard/ for real-time updates. Provides:
 * - Auto-reconnection with exponential backoff
 * - Event dispatching to registered handlers
 * - Device subscription/unsubscription
 * - Connection status indicator
 *
 * Usage:
 *   DashboardWS.connect();
 *   DashboardWS.on('device_update', (data) => { ... });
 *   DashboardWS.on('alert', (data) => { ... });
 *   DashboardWS.subscribeDevice(deviceId);
 */

const DashboardWS = (() => {
    let ws = null;
    let connected = false;
    let reconnectDelay = 2;
    const maxReconnectDelay = 60;
    let reconnectTimer = null;
    let handlers = {};
    let statusCallback = null;

    function getWsUrl() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${proto}//${location.host}/ws/dashboard/`;
    }

    function connect() {
        if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
            return;
        }

        try {
            ws = new WebSocket(getWsUrl());
        } catch (e) {
            console.error('[WS] Connection error:', e);
            scheduleReconnect();
            return;
        }

        ws.onopen = () => {
            connected = true;
            reconnectDelay = 2;
            console.log('[WS] Connected to dashboard');
            if (statusCallback) statusCallback('connected');
            send({ type: 'auth', token: getCSRFToken() });
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleMessage(msg);
            } catch (e) {
                console.warn('[WS] Invalid message:', e);
            }
        };

        ws.onclose = (event) => {
            connected = false;
            console.log('[WS] Disconnected (code:', event.code, ')');
            if (statusCallback) statusCallback('disconnected');
            scheduleReconnect();
        };

        ws.onerror = (error) => {
            console.error('[WS] Error:', error);
        };
    }

    function disconnect() {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        if (ws) {
            ws.close();
            ws = null;
        }
        connected = false;
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        const delay = Math.min(reconnectDelay, maxReconnectDelay);
        console.log(`[WS] Reconnecting in ${delay}s...`);
        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
        }, delay * 1000);
        reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
    }

    function send(data) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
        }
    }

    function handleMessage(msg) {
        const type = msg.type || msg.event_type || '';
        const handlers_list = handlers[type] || [];
        const all_handlers = handlers['*'] || [];

        for (const h of [...handlers_list, ...all_handlers]) {
            try {
                h(msg);
            } catch (e) {
                console.error('[WS] Handler error:', e);
            }
        }
    }

    function on(eventType, handler) {
        if (!handlers[eventType]) handlers[eventType] = [];
        handlers[eventType].push(handler);
    }

    function off(eventType, handler) {
        if (!handlers[eventType]) return;
        handlers[eventType] = handlers[eventType].filter(h => h !== handler);
    }

    function subscribeDevice(deviceId) {
        send({ type: 'subscribe_device', device_id: deviceId });
    }

    function unsubscribeDevice(deviceId) {
        send({ type: 'unsubscribe_device', device_id: deviceId });
    }

    function isConnected() {
        return connected;
    }

    function onStatusChange(callback) {
        statusCallback = callback;
    }

    function getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (const c of cookies) {
            const [key, val] = c.trim().split('=');
            if (key === name) return decodeURIComponent(val || '');
        }
        return '';
    }

    return {
        connect,
        disconnect,
        send,
        on,
        off,
        subscribeDevice,
        unsubscribeDevice,
        isConnected,
        onStatusChange,
    };
})();
