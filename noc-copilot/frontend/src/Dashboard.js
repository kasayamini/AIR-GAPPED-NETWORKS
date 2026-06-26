export class Dashboard {
    constructor(containerId) {
        this.containerId = containerId;
        this.activeTab = 'latency'; // Default active chart tab
        this.metrics = { latency: 0.0, packet_loss: 0.0, jitter: 0.0, bandwidth: 0.0 };
        this.history = [];
    }

    setActiveTab(tab) {
        this.activeTab = tab;
        this.renderCharts();
    }

    render(metrics, history) {
        if (metrics) this.metrics = metrics;
        if (history) this.history = history;
        
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Render layout
        container.innerHTML = `
            <div class="main-metrics-section">
                <!-- Metrics Status Cards -->
                <div class="metrics-cards">
                    ${this.renderCard('latency', 'Latency', this.metrics.latency, 'ms', 'Baseline: 18-32ms')}
                    ${this.renderCard('packet_loss', 'Packet Loss', this.metrics.packet_loss, '%', 'Baseline: 0-1.5%')}
                    ${this.renderCard('jitter', 'Jitter', this.metrics.jitter, 'ms', 'Baseline: 2.5-6.5ms')}
                    ${this.renderCard('bandwidth', 'Bandwidth', this.metrics.bandwidth, '%', 'Baseline: 30-50%')}
                </div>

                <!-- Live Metrics Trend Chart -->
                <div class="chart-container">
                    <div class="chart-header">
                        <h2 class="panel-title">Network Telemetry Trend</h2>
                        <div class="chart-tabs">
                            <button class="chart-tab ${this.activeTab === 'latency' ? 'active' : ''}" data-tab="latency">Latency</button>
                            <button class="chart-tab ${this.activeTab === 'packet_loss' ? 'active' : ''}" data-tab="packet_loss">Packet Loss</button>
                            <button class="chart-tab ${this.activeTab === 'jitter' ? 'active' : ''}" data-tab="jitter">Jitter</button>
                            <button class="chart-tab ${this.activeTab === 'bandwidth' ? 'active' : ''}" data-tab="bandwidth">Bandwidth</button>
                        </div>
                    </div>
                    <div class="chart-viewport" id="chart-viewport-box">
                        <!-- Rendered Chart SVG goes here -->
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
        this.renderCharts();
    }

    renderCard(key, label, value, unit, baselineText) {
        return `
            <div class="card ${key}">
                <div class="card-title">
                    <span>${label}</span>
                </div>
                <div class="card-value">
                    ${value !== undefined ? value.toFixed(1) : '--'}<span class="card-unit">${unit}</span>
                </div>
                <div class="card-trend">
                    ${baselineText}
                </div>
            </div>
        `;
    }

    bindEvents() {
        const tabs = document.querySelectorAll('.chart-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const targetTab = e.target.getAttribute('data-tab');
                this.setActiveTab(targetTab);
            });
        });

        // Re-render chart on window resize for responsiveness
        if (!this.resizeHandlerBound) {
            window.addEventListener('resize', () => this.renderCharts());
            this.resizeHandlerBound = true;
        }
    }

    renderCharts() {
        const viewport = document.getElementById('chart-viewport-box');
        if (!viewport) return;
        
        if (!this.history || this.history.length === 0) {
            viewport.innerHTML = `<div class="empty-state">Awaiting streaming updates from data generator...</div>`;
            return;
        }

        const width = viewport.clientWidth || 600;
        const height = viewport.clientHeight || 250;
        const padding = { top: 20, right: 30, bottom: 20, left: 50 };

        const tab = this.activeTab;
        
        // Extract history values for the selected tab
        const dataPoints = this.history.map(h => ({
            value: h.metrics[tab],
            is_anomaly: h.anomaly.is_anomaly,
            timestamp: h.timestamp
        }));

        let maxVal = Math.max(...dataPoints.map(d => d.value), 10.0);
        let minVal = Math.min(...dataPoints.map(d => d.value), 0.0);

        if (maxVal === minVal) {
            maxVal += 1.0;
            minVal = Math.max(0, minVal - 1.0);
        }

        // Add 10% vertical padding headroom
        const valRange = maxVal - minVal;
        maxVal += valRange * 0.15;
        minVal = Math.max(0, minVal - valRange * 0.05);

        const nPoints = dataPoints.length;
        const points = dataPoints.map((d, index) => {
            const x = padding.left + (index / Math.max(1, nPoints - 1)) * (width - padding.left - padding.right);
            const y = height - padding.bottom - ((d.value - minVal) / (maxVal - minVal)) * (height - padding.top - padding.bottom);
            return { x, y, value: d.value, is_anomaly: d.is_anomaly };
        });

        const polylinePoints = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

        // Draw horizontal grid lines
        let gridLines = '';
        const nTicks = 5;
        for (let i = 0; i < nTicks; i++) {
            const val = minVal + (i / (nTicks - 1)) * (maxVal - minVal);
            const y = height - padding.bottom - (i / (nTicks - 1)) * (height - padding.top - padding.bottom);
            gridLines += `
                <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(255, 255, 255, 0.05)" stroke-dasharray="4,4" />
                <text x="${padding.left - 10}" y="${y + 4}" fill="var(--text-muted)" font-size="10" text-anchor="end" font-family="var(--font-mono)">${val.toFixed(1)}</text>
            `;
        }

        // Get matching colors
        let strokeColor = 'var(--primary)';
        if (tab === 'packet_loss') strokeColor = 'var(--warning)';
        if (tab === 'jitter') strokeColor = '#d946ef'; // Purple
        if (tab === 'bandwidth') strokeColor = 'var(--success)';

        // Draw area path under trendline
        let areaPath = '';
        if (points.length > 0) {
            const first = points[0];
            const last = points[points.length - 1];
            areaPath = `M ${first.x.toFixed(1)} ${height - padding.bottom} ` +
                       points.map(p => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ') +
                       ` L ${last.x.toFixed(1)} ${height - padding.bottom} Z`;
        }

        // Draw anomaly markers
        const anomalyDots = points
            .filter(p => p.is_anomaly)
            .map(p => `
                <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="5" fill="var(--danger)" stroke="#ffffff" stroke-width="1.5" />
                <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="10" fill="none" stroke="var(--danger)" stroke-width="1.5" opacity="0.8">
                    <animate attributeName="r" values="5;15" dur="1.5s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0" dur="1.5s" repeatCount="indefinite" />
                </circle>
            `).join('');

        // Highlight latest current dot
        let currentDot = '';
        if (points.length > 0) {
            const lp = points[points.length - 1];
            currentDot = `
                <circle cx="${lp.x.toFixed(1)}" cy="${lp.y.toFixed(1)}" r="4.5" fill="${strokeColor}" />
                <circle cx="${lp.x.toFixed(1)}" cy="${lp.y.toFixed(1)}" r="10" fill="none" stroke="${strokeColor}" stroke-width="1.5">
                    <animate attributeName="r" values="4.5;12" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.7;0" dur="2s" repeatCount="indefinite" />
                </circle>
            `;
        }

        viewport.innerHTML = `
            <svg class="svg-chart" width="${width}" height="${height}">
                <defs>
                    <linearGradient id="chart-area-grad-${tab}" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.25"/>
                        <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0"/>
                    </linearGradient>
                </defs>
                
                <!-- Grid system -->
                ${gridLines}
                
                <!-- Base axis line -->
                <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="rgba(255, 255, 255, 0.12)" />
                
                <!-- Area path -->
                ${areaPath ? `<path d="${areaPath}" fill="url(#chart-area-grad-${tab})" />` : ''}
                
                <!-- Trend line -->
                ${polylinePoints ? `<polyline fill="none" stroke="${strokeColor}" stroke-width="2.5" points="${polylinePoints}" stroke-linecap="round" stroke-linejoin="round" />` : ''}
                
                <!-- Anomaly events -->
                ${anomalyDots}
                
                <!-- Pulse current value -->
                ${currentDot}
            </svg>
        `;
    }
}
