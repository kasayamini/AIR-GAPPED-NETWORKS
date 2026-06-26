import os
from fastapi import APIRouter
from pydantic import BaseModel
from backend.ml_model import detector
from backend.rca_engine import rca_engine
from backend.websocket import manager
from backend.alert_generator import AlertGenerator
from backend.incident_generator import IncidentGenerator
from backend.storage import append_history, append_alert, append_incident

router = APIRouter()

class TelemetryData(BaseModel):
    timestamp: str
    latency: float
    packet_loss: float
    jitter: float
    bandwidth: float

@router.post("/ingest")
async def ingest_metrics(data: TelemetryData):
    # 1. Run ML Anomaly Detection
    prediction = detector.predict(
        latency=data.latency,
        packet_loss=data.packet_loss,
        jitter=data.jitter,
        bandwidth=data.bandwidth
    )
    
    # 2. Run Rule-Based RCA Engine
    rca = rca_engine.analyze(
        metrics={
            "latency": data.latency,
            "packet_loss": data.packet_loss,
            "jitter": data.jitter,
            "bandwidth": data.bandwidth
        },
        is_anomaly=prediction["is_anomaly"]
    )
    
    # 3. Aggregate full telemetry update payload
    payload = {
        "timestamp": data.timestamp,
        "metrics": {
            "latency": data.latency,
            "packet_loss": data.packet_loss,
            "jitter": data.jitter,
            "bandwidth": data.bandwidth
        },
        "anomaly": {
            "is_anomaly": prediction["is_anomaly"],
            "anomaly_score": prediction["anomaly_score"],
            "decision_score": prediction["decision_score"]
        },
        "rca": rca
    }
    
    # 4. Save metrics, alerts, and incidents to persistent local JSON storage
    append_history(payload)

    if payload["anomaly"]["is_anomaly"]:
        alert = AlertGenerator.build_alert(payload)
        incident = IncidentGenerator.build_incident(payload)
        append_alert(alert)
        append_incident(incident)
        payload["alert"] = alert
        payload["incident"] = incident

    # 5. Stream data live over WebSockets
    await manager.broadcast(payload)
    
    return {"status": "success", "data": payload}
