import { Dashboard } from './Dashboard.js';
import { AlertPanel } from './AlertPanel.js';
import { ChatPanel } from './ChatPanel.js';

class App {
    constructor() {
        // Base API URL can be set at build time using Vite env `VITE_API_BASE`
        this.API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) ? import.meta.env.VITE_API_BASE : '';
        this.history = [];
        this.latestPayload = null;
        this.systemContext = {};
        this.reconnectTimer = null;
        this.ws = null;
        this.notifications = [];

        // Instantiate child components
        this.dashboard = new Dashboard('dashboard-container');
        this.alertPanel = new AlertPanel('alert-panel-container');
        this.chatPanel = new ChatPanel('chat-panel-container');

        // Setup initial static layout
        this.initLayout();

        // Run bootstrap lifecycle
        this.bootstrap();
    }

    initLayout() {
        const appNode = document.getElementById('app');
        if (!appNode) return;

        appNode.innerHTML = `
            <header>
                <div class="brand">
                    <h1>AI NOC COPILOT</h1>
                    <span class="badge-tag">SD-WAN Edge</span>
                </div>
                <div class="header-actions">
                    <div class="connection-status">
                        <span class="heartbeat" id="connection-heartbeat"></span>
                        <span id="connection-status-text">Connecting...</span>
                    </div>
                    <div class="alert-badge" id="alert-badge">0 Alerts</div>
                </div>
            </header>
            <div class="dashboard-grid">
                <div id="dashboard-container"></div>
                <div id="alert-panel-container"></div>
            </div>
            <div id="chat-panel-container"></div>
            <div id="toast-container" class="toast-container"></div>
        `;
    }

    async bootstrap() {
        await this.loadHistory();
        await this.chatPanel.loadHistory();
        await this.loadSystemContext();
        this.renderComponents();
        this.connectWebSocket();
    }

    async loadHistory() {
        try {
            const url = this.API_BASE ? `${this.API_BASE}/api/history` : '/api/history';
            const response = await fetch(url);
            if (response.ok) {
                this.history = await response.json();
                console.log(`Loaded ${this.history.length} telemetry points from server logs.`);
                if (this.history.length > 0) {
                    this.latestPayload = this.history[this.history.length - 1];
                }
            }
        } catch (error) {
            console.error("Failed to load telemetry logs history:", error);
        }
    }

    async loadSystemContext() {
        try {
            const url = this.API_BASE ? `${this.API_BASE}/api/system/context` : '/api/system/context';
            const response = await fetch(url);
            if (response.ok) {
                this.systemContext = await response.json();
            }
        } catch (error) {
            console.warn('Unable to load system context:', error);
            this.systemContext = { summary: 'System context unavailable.' };
        }
    }

    connectWebSocket() {
        let wsUrl = '';
        if (this.API_BASE) {
            try {
                const api = new URL(this.API_BASE);
                const protocol = api.protocol === 'https:' ? 'wss:' : 'ws:';
                wsUrl = `${protocol}//${api.host}/ws`;
            } catch (err) {
                console.warn('Invalid API_BASE URL, falling back to window.location for websocket');
            }
        }
        if (!wsUrl) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            wsUrl = `${protocol}//${window.location.host}/ws`;
        }

        console.log(`Connecting live feed WebSocket: ${wsUrl}`);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log("WebSocket pipeline connected.");
            this.updateConnectionStatus(true, "Live Stream Active");
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                this.handlePayload(payload);
            } catch (err) {
                console.error("Failed to parse WebSocket ingestion frame:", err);
            }
        };

        this.ws.onclose = () => {
            console.warn("WebSocket connection terminated. Reconnecting in 3s...");
            this.updateConnectionStatus(false, "Offline - Reconnecting");
            this.triggerReconnect();
        };

        this.ws.onerror = (err) => {
            console.error("WebSocket connection failure:", err);
            this.ws.close();
        };
    }

    handlePayload(payload) {
        this.latestPayload = payload;
        this.history.push(payload);
        if (this.history.length > 100) {
            this.history.shift();
        }
        if (payload.anomaly && payload.anomaly.is_anomaly) {
            this.queueNotification(payload);
        }
        this.renderComponents();
    }

    queueNotification(payload) {
        const alert = payload.alert || {
            timestamp: payload.timestamp,
            device_name: 'Unknown Device',
            severity: payload.anomaly.anomaly_score >= 85 ? 'CRITICAL' : 'HIGH',
            root_cause: payload.rca.cause,
            business_impact: payload.rca.impact,
            recommended_action: payload.rca.impact,
        };

        const message = `${alert.root_cause} — ${alert.business_impact}`;
        this.notifications.push({
            id: `toast-${Date.now()}`,
            title: `${alert.severity} Alert: ${alert.device_name}`,
            message,
            severity: alert.severity,
            timestamp: alert.timestamp,
            action: alert.recommended_action
        });
        this.playAlertSound(alert.severity);
        this.renderNotifications();
    }

    playAlertSound(severity) {
        try {
            const context = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.type = 'sine';
            oscillator.frequency.value = severity === 'CRITICAL' ? 440 : 330;
            gain.gain.value = 0.1;
            oscillator.connect(gain);
            gain.connect(context.destination);
            oscillator.start();
            oscillator.stop(context.currentTime + 0.2);
        } catch (error) {
            console.warn('Sound playback unavailable:', error);
        }
    }

    renderNotifications() {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const activeNotifications = this.notifications.slice(-4);
        container.innerHTML = activeNotifications.map(n => `
            <div class="toast-card ${n.severity.toLowerCase()}">
                <div class="toast-title">${n.title}</div>
                <div class="toast-message">${n.message}</div>
                <div class="toast-action">${n.action}</div>
            </div>
        `).join('');
        setTimeout(() => {
            this.notifications.shift();
            this.renderNotifications();
        }, 8000);
    }

    triggerReconnect() {
        if (!this.reconnectTimer) {
            this.reconnectTimer = setTimeout(() => {
                this.reconnectTimer = null;
                this.connectWebSocket();
            }, 3000);
        }
    }

    updateConnectionStatus(connected, text) {
        const heartbeat = document.getElementById('connection-heartbeat');
        const statusText = document.getElementById('connection-status-text');
        const badge = document.getElementById('alert-badge');

        if (heartbeat && statusText) {
            statusText.textContent = text;
            if (connected) {
                heartbeat.className = 'heartbeat connected';
            } else {
                heartbeat.className = 'heartbeat disconnected';
            }
        }

        if (badge) {
            const alertCount = this.history.filter(entry => entry.anomaly && entry.anomaly.is_anomaly).length;
            badge.textContent = `${alertCount} Alerts`;
        }
    }

    renderComponents() {
        const metrics = this.latestPayload ? this.latestPayload.metrics : null;
        this.dashboard.render(metrics, this.history);
        this.alertPanel.render(this.latestPayload, this.history);
        this.chatPanel.render(this.systemContext);
        this.renderNotifications();
    }
}

export default App;
