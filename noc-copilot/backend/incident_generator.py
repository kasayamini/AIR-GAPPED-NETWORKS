import datetime
from typing import Dict, Any

from backend.config import DEFAULT_DEVICE_NAME


class IncidentGenerator:
    @staticmethod
    def build_incident(payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = payload.get("timestamp") or datetime.datetime.now().isoformat()
        metrics = payload.get("metrics", {})
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

        impacted_metrics = []
        for key, value in metrics.items():
            if key in ["latency", "packet_loss", "jitter", "bandwidth"] and value is not None:
                if key == "bandwidth" and value > 85:
                    impacted_metrics.append(key)
                elif key != "bandwidth" and value > 50:
                    impacted_metrics.append(key)

        root_cause = rca.get("cause", "Unknown root cause")
        business_impact = rca.get("impact", "Potential impact unavailable.")
        recommended_action = IncidentGenerator._recommend_action(rca, metrics)
        confidence = rca.get("confidence", 50)

        return {
            "id": f"incident-{timestamp}-{int(datetime.datetime.now().timestamp())}",
            "timestamp": timestamp,
            "device_name": DEFAULT_DEVICE_NAME,
            "severity": severity,
            "root_cause": root_cause,
            "technical_explanation": IncidentGenerator._technical_explanation(rca, metrics),
            "business_impact": business_impact,
            "recommended_resolution": recommended_action,
            "confidence_score": confidence,
            "affected_metrics": impacted_metrics,
            "affected_devices": [DEFAULT_DEVICE_NAME],
            "cisco_cli": IncidentGenerator._cisco_commands(rca, metrics),
            "linux_commands": IncidentGenerator._linux_commands(rca, metrics),
            "verification_steps": IncidentGenerator._verification_steps(rca, metrics),
            "preventive_recommendations": IncidentGenerator._preventive_recommendations(rca, metrics),
            "anomaly_score": anomaly.get("anomaly_score", 0),
            "rca": rca,
            "metrics": metrics,
        }

    @staticmethod
    def _recommend_action(rca: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        cause = rca.get("cause", "").lower()
        if "isp" in cause or "link" in cause:
            return "Validate the WAN provider circuit, check SLA dashboards, and fail over to the backup tunnel if available."
        if "bandwidth" in cause:
            return "Inspect traffic policies, throttle non-critical bulk flows, and consider applying QoS to prevent saturation."
        if "route" in cause or "suboptimal" in cause:
            return "Review the SD-WAN path selection, verify BGP/OSPF route metrics, and rebalance traffic away from the congested link."
        if "crc" in cause or "interference" in cause:
            return "Check physical interface statistics, inspect switch logs, and replace the faulty cable or interface if necessary."
        return "Investigate the affected path, validate device health, and enforce corrective actions based on metrics."

    @staticmethod
    def _technical_explanation(rca: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        cause = rca.get("cause", "Telemetry issue")
        impact = rca.get("impact", "Impact information unavailable.")
        score = metrics.get("bandwidth", 0)
        return f"{cause}. {impact} The current telemetry profile indicates a deviation from expected network health."

    @staticmethod
    def _cisco_commands(rca: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        if "isp" in rca.get("cause", "").lower():
            return "show interfaces | include (GigabitEthernet|TenGigabitEthernet)\nshow ip route summary\nshow logging | include BGP|OSPF"
        if "bandwidth" in rca.get("cause", "").lower():
            return "show policy-map interface\nshow queueing interface\nshow processes cpu"
        if "route" in rca.get("cause", "").lower():
            return "show sdwan policy-path\nshow ip cef | include \"(best|backup)\"\nshow ip route"
        return "show interfaces summary\nshow logging | include (ERROR|ALERT)"

    @staticmethod
    def _linux_commands(rca: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        if "isp" in rca.get("cause", "").lower():
            return "ping -c 5 8.8.8.8\ntraceroute 8.8.8.8\ncat /var/log/syslog | tail -n 50"
        if "bandwidth" in rca.get("cause", "").lower():
            return "iftop -t -s 10\nnethogs\ncat /proc/net/dev"
        if "route" in rca.get("cause", "").lower():
            return "ip route show\nss -tunapl\njournalctl -u network.service --no-pager | tail -n 50"
        return "dmesg | tail -n 30\nvmstat 1 5"

    @staticmethod
    def _verification_steps(rca: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        return "Confirm alert details, verify the affected circuit and device status, then validate the fix by comparing new telemetry to baseline thresholds."

    @staticmethod
    def _preventive_recommendations(rca: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        return "Document the incident, tune traffic engineering policies, and schedule a maintenance window to validate WAN stability."
