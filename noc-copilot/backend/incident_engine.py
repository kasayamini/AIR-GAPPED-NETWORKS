import datetime
import re
from typing import Any, Dict, List, Optional

from backend.config import DEFAULT_DEVICE_NAME


class IncidentEngine:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _normalize_timestamp(value: Optional[str]) -> str:
        if not value:
            return datetime.datetime.utcnow().isoformat()
        try:
            return datetime.datetime.fromisoformat(value).isoformat()
        except ValueError:
            return value

    @staticmethod
    def _severity_from_score(score: float) -> str:
        if score >= 85:
            return "CRITICAL"
        if score >= 70:
            return "HIGH"
        if score >= 55:
            return "MEDIUM"
        if score > 0:
            return "LOW"
        return "INFO"

    @staticmethod
    def _service_from_text(text: str) -> str:
        text = text.lower()
        if any(token in text for token in ["vpn", "tunnel", "ipsec", "vpn-gateway"]):
            return "VPN"
        if any(token in text for token in ["bgp", "ospf", "route", "routing"]):
            return "Routing"
        if any(token in text for token in ["latency", "packet loss", "jitter", "bandwidth", "throughput"]):
            return "WAN"
        if any(token in text for token in ["firewall", "acl", "security"]):
            return "Security"
        if any(token in text for token in ["dns", "dhcp", "domain"]):
            return "Infrastructure"
        return "Network"

    @staticmethod
    def _build_summary(source: Dict[str, Any], alert: Optional[Dict[str, Any]] = None) -> str:
        parts: List[str] = []
        if alert:
            title = alert.get("summary") or alert.get("title") or alert.get("alert") or "Alert event"
            parts.append(f"Alert: {title}")
        if source.get("metrics"):
            metrics = source.get("metrics", {})
            metric_pairs = [f"{k}={v}" for k, v in metrics.items() if v is not None]
            if metric_pairs:
                parts.append("Telemetry: " + ", ".join(metric_pairs))
        if source.get("anomaly"):
            anomaly = source.get("anomaly", {})
            parts.append(f"Anomaly score {anomaly.get('anomaly_score', 0)}")
        if source.get("rca"):
            parts.append(f"RCA: {source.get('rca', {}).get('cause', 'Unknown')}")
        if not parts:
            parts.append("Incident generated from telemetry or alert source.")
        return "; ".join(parts)

    @staticmethod
    def _extract_root_cause(record: Dict[str, Any]) -> str:
        rca = record.get("rca") or {}
        cause = rca.get("cause")
        if cause:
            return cause
        if record.get("metrics"):
            metrics = record["metrics"]
            if metrics.get("packet_loss", 0) > 40:
                return "Critical packet loss or link degradation"
            if metrics.get("bandwidth", 0) > 85:
                return "Bandwidth saturation"
            if metrics.get("latency", 0) > 100:
                return "High latency on active path"
        if record.get("alert"):
            return str(record.get("alert"))
        return "Unknown root cause"

    def _make_incident_id(self, timestamp: str, summary: str) -> str:
        normalized = re.sub(r"[^0-9A-Za-z]+", "-", summary).strip("-")[:40]
        suffix = int(datetime.datetime.utcnow().timestamp())
        return f"incident-{normalized[:40]}-{suffix}"

    def _incident_from_history(self, record: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = self._normalize_timestamp(record.get("timestamp"))
        anomaly = record.get("anomaly", {})
        severity = self._severity_from_score(anomaly.get("anomaly_score", 0))
        summary = self._build_summary(record)
        service = self._service_from_text(summary)
        root_cause = self._extract_root_cause(record)

        return {
            "id": self._make_incident_id(timestamp, summary),
            "timestamp": timestamp,
            "incident": summary,
            "severity": severity,
            "service": service,
            "device": record.get("device_name", DEFAULT_DEVICE_NAME),
            "summary": summary,
            "root_cause": root_cause,
            "details": record,
        }

    def _incident_from_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = self._normalize_timestamp(alert.get("timestamp"))
        severity = str(alert.get("severity", "MEDIUM")).upper()
        summary_text = alert.get("summary") or alert.get("message") or alert.get("title") or "Alert event"
        service = self._service_from_text(summary_text)
        root_cause = alert.get("cause") or summary_text

        return {
            "id": self._make_incident_id(timestamp, summary_text),
            "timestamp": timestamp,
            "incident": summary_text,
            "severity": severity,
            "service": service,
            "device": alert.get("device_name", DEFAULT_DEVICE_NAME),
            "summary": summary_text,
            "root_cause": root_cause,
            "details": alert,
        }

    def parse_incidents(self, history: List[Dict[str, Any]], alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        incidents: List[Dict[str, Any]] = []
        seen_keys = set()

        for record in history:
            if record.get("anomaly", {}).get("is_anomaly") or record.get("rca") or record.get("metrics"):
                incident = self._incident_from_history(record)
                key = (incident["timestamp"], incident["summary"])
                if key not in seen_keys:
                    incidents.append(incident)
                    seen_keys.add(key)

        for alert in alerts:
            incident = self._incident_from_alert(alert)
            key = (incident["timestamp"], incident["summary"])
            if key not in seen_keys:
                incidents.append(incident)
                seen_keys.add(key)

        incidents.sort(key=lambda value: value.get("timestamp", ""))
        return incidents


incident_engine = IncidentEngine()
