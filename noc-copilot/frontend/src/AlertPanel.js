export class AlertPanel {
    constructor(containerId) {
        this.containerId = containerId;
        this.history = [];
    }

    render(latestPayload, history) {
        if (history) this.history = history;
        
        const latest = latestPayload || (this.history.length > 0 ? this.history[this.history.length - 1] : null) || {
            metrics: {},
            anomaly: { is_anomaly: false, anomaly_score: 0 },
            rca: { cause: "Normal Baseline", impact: "No network anomalies detected. All SD-WAN tunnels active and healthy.", confidence: 100 }
        };

        const container = document.getElementById(this.containerId);
        if (!container) return;

        const isAnomaly = latest.anomaly.is_anomaly;
        const anomalyScore = latest.anomaly.anomaly_score;
        const rca = latest.rca;

        const dangerClass = isAnomaly ? 'danger-active' : '';
        const badgeClass = isAnomaly ? 'alert' : 'safe';
        const badgeText = isAnomaly ? 'Anomaly Detected' : 'System Healthy';
        const glowClass = isAnomaly ? 'glow-danger' : 'glow-safe';
        const scoreColor = isAnomaly ? 'var(--danger)' : 'var(--success)';

        // Format and render history logs (most recent first, capped at 20)
        const historyHtml = this.history.length === 0 
            ? `<div class="empty-state">Awaiting data stream...</div>`
            : this.history.slice().reverse().slice(0, 20).map(h => {
                const date = new Date(h.timestamp);
                const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                const rowAnomaly = h.anomaly.is_anomaly;
                const rowClass = rowAnomaly ? 'anomaly-row' : '';
                const rowLabel = rowAnomaly ? h.rca.cause : 'Telemetry OK';
                const statusTag = rowAnomaly ? 'CRITICAL' : 'NORMAL';
                const statusColor = rowAnomaly ? 'var(--danger)' : 'var(--success)';
                
                return `
                    <div class="alert-row ${rowClass}">
                        <div class="alert-row-left">
                            <span class="alert-row-title">${rowLabel}</span>
                            <span class="alert-row-time">
                                ${timeStr} | Lat: ${h.metrics.latency.toFixed(0)}ms | Loss: ${h.metrics.packet_loss.toFixed(1)}% | Jitter: ${h.metrics.jitter.toFixed(1)}ms | BW: ${h.metrics.bandwidth.toFixed(0)}%
                            </span>
                        </div>
                        <div class="alert-row-right">
                            <span class="alert-row-score" style="color: ${statusColor}">
                                ${statusTag} (${h.anomaly.anomaly_score})
                            </span>
                        </div>
                    </div>
                `;
            }).join('');

        container.innerHTML = `
            <div class="right-panel-section">
                <!-- ML Analytics Status & Diagnostics -->
                <div class="anomaly-alert-box ${dangerClass}">
                    <div class="alert-status-header">
                        <h2 class="panel-title">NOC Copilot Analytics</h2>
                        <span class="status-indicator-badge ${badgeClass}">
                            <span class="heartbeat connected" style="background-color: ${isAnomaly ? 'var(--danger)' : 'var(--success)'}"></span>
                            ${badgeText}
                        </span>
                    </div>

                    <div class="score-display-wrapper">
                        <div class="circular-score ${glowClass}">
                            <span class="score-num" style="color: ${scoreColor}">${anomalyScore}</span>
                        </div>
                        <div class="score-lbl">
                            <span>Anomaly Score</span>
                            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 400; max-width: 180px;">
                                ${isAnomaly ? 'Metrics deviate from baseline model' : 'Within normal baseline limits'}
                            </span>
                        </div>
                    </div>

                    <!-- Rule-Based RCA Diagnostics -->
                    <div class="rca-box">
                        <div class="rca-title">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle;">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="16" x2="12" y2="12"></line>
                                <line x1="12" y1="8" x2="12.01" y2="8"></line>
                            </svg>
                            Root Cause Diagnostics
                        </div>
                        <div class="rca-detail">${rca.impact}</div>
                        <div class="rca-pill-group">
                            <span class="rca-pill cause-tag">${rca.cause}</span>
                            <span class="rca-pill conf-tag">Confidence: ${rca.confidence}%</span>
                        </div>
                    </div>
                </div>

                <!-- Alert History Log -->
                <div class="alert-history-panel">
                    <h2 class="panel-title">Live Ingestion Stream</h2>
                    <div class="alerts-list">
                        ${historyHtml}
                    </div>
                </div>
            </div>
        `;
    }
}
