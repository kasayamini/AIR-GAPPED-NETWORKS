import datetime
from typing import Any, Dict

from backend.config import DEFAULT_DEVICE_NAME


class AlertGenerator:
    @staticmethod
    def build_alert(payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = payload.get("timestamp") or datetime.datetime.now().isoformat()
        anomaly = payload.get("anomaly", {})
        rca = payload.get("rca", {})

        severity = "INFO"
        if anomaly.get("is_anomaly"):
            score = anomaly.get("anomaly_score", 0)
            if score >= 85:
                severity = "CRITICAL"
            elif score >= 70:
                severity = "HIGH"
            elif score >= 55:
                severity = "MEDIUM"
            else:
                severity = "LOW"

        if "isp" in rca.get("cause", "").lower() or "link" in rca.get("cause", "").lower():
            severity = "CRITICAL" if anomaly.get("anomaly_score", 0) >= 70 else severity
        if "bandwidth" in rca.get("cause", "").lower() and anomaly.get("anomaly_score", 0) >= 70:
            severity = "HIGH"

        return {
            "id": f"alert-{timestamp}-{int(datetime.datetime.now().timestamp())}",
            "timestamp": timestamp,
            "device_name": DEFAULT_DEVICE_NAME,
            "severity": severity,
            "root_cause": rca.get("cause", "Unknown"),
            "business_impact": rca.get("impact", "Impact unavailable."),
            "recommended_action": AlertGenerator._recommended_action(rca),
            "anomaly_score": anomaly.get("anomaly_score", 0),
            "metrics": payload.get("metrics", {}),
            "rca": rca,
        }

    @staticmethod
    def _recommended_action(rca: Dict[str, Any]) -> str:
        cause = rca.get("cause", "").lower()
        if "isp" in cause or "link" in cause:
            return "Engage the WAN provider, validate WAN circuit health, and shift traffic to backup tunnels."
        if "bandwidth" in cause:
            return "Throttle non-critical flows, verify QoS policies, and investigate heavy traffic sources."
        if "route" in cause:
            return "Review SD-WAN route selection, optimize path preferences, and check route health metrics."
        if "crc" in cause or "interference" in cause:
            return "Inspect interface diagnostics, replace faulty cables, and review switch port statistics."
        return "Investigate the topology, verify device status, and validate metrics against baseline thresholds."
