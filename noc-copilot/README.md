# AI NOC Copilot MVP 🚀

A real-time, self-contained Network Operations Center (NOC) Copilot MVP designed for SD-WAN telemetry ingestion, ML-driven anomaly detection, rule-based Root Cause Analysis (RCA), and live dashboard visualization. Built to run fully client-side (air-gapped friendly) without complex compilation steps.

---

## 🏗️ Architecture Overview

```
 [ Data Generator (simulator.py) ]
             ↓ (POST HTTP /api/ingest every 2s)
 [ FastAPI Backend (main.py) ]
             ↓
 [ ML Engine: Isolation Forest (ml_model.py) ] ── (predicts anomaly & severity score)
             ↓
 [ Alert & RCA Engine (rca_engine.py) ] ──────── (generates cause, impact & confidence)
             ↓
 [ WebSocket Server ] ────────────────────────── (streams real-time JSON frames)
             ↓
 [ Vanilla HTML/CSS/JS Dashboard (App.js) ] ──── (visualizes live metrics and alerts)
```

---

## 🛠️ Key Components

1. **Telemetry Ingestion**: A POST endpoint (`/api/ingest`) that processes incoming latency, packet loss, jitter, and bandwidth metrics.
2. **ML Anomaly Detector**: Employs scikit-learn's `IsolationForest`. Upon application startup, the model baseline trains on 1,000 normal baseline telemetry samples, learning normal network profiles. Live metrics are then categorized as normal (`1`) or anomalous (`-1`), and scaled to an anomaly score between `0` (healthy) and `100` (critical).
3. **RCA Diagnostics**: A rule-based interpreter that correlates anomalous metric deviations with exact root-cause descriptions (e.g. ISP outages, routing instabilities, switched interface errors, or micro-congestion).
4. **Real-time Live Feed**: Streams metrics and anomaly reports via WebSockets to the web interface.
5. **Air-Gapped Dashboard**: A responsive, modern glassmorphic dashboard built using native ES6 Modules and Vanilla CSS. Real-time charting is driven by a custom lightweight SVG sparkline engine (no heavy external chart dependencies).

---

## 🚀 Getting Started

### 1. Installation

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Start the Backend API & Dashboard

Run the FastAPI backend server:
```bash
python backend/main.py
```
* **API Documentation**: Available at `http://127.0.0.1:8000/docs`
* **Dashboard Web Interface**: Open `http://127.0.0.1:8000/` in your browser.

### 3. Install Ollama and the Offline Model

This project integrates a local Ollama assistant using the `llama3.1:latest` model.

If Ollama is not installed, follow these steps:
1. Install Ollama from `https://ollama.ai` for Windows.
2. Pull the local model if not already installed:
```bash
ollama pull llama3.1:latest
```
3. Start the Ollama server:
```bash
ollama serve
```

The application will automatically detect Ollama and the model, and will show a friendly status message if the local service is unavailable.

### 4. Run the Telemetry Simulator

In a separate terminal window, start the SD-WAN simulator to feed telemetry data into the dashboard:
```bash
python backend/simulator.py
```

The simulator runs in a loop, broadcasting normal baseline telemetry metrics and periodically triggering network anomalies (like severe ISP packet loss, bandwidth saturation, or path routing loop spikes) to test the ML detection pipeline.
