from typing import Dict, Any, List, Tuple


class CorrelationEngine:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _match_patterns(incident: Dict[str, Any]) -> List[str]:
        summary = incident.get("summary", "").lower()
        labels = []

        if any(term in summary for term in ["latency", "packet loss", "jitter", "throughput", "bandwidth"]):
            labels.append("performance")
        if any(term in summary for term in ["timeout", "reset", "dropped", "connection refused"]):
            labels.append("connectivity")
        if any(term in summary for term in ["isp", "link", "wan", "circuit"]):
            labels.append("wan")
        if any(term in summary for term in ["acl", "firewall", "security", "blocked"]):
            labels.append("security")
        if any(term in summary for term in ["bgp", "ospf", "routing", "route", "path"]):
            labels.append("routing")
        return labels

    @staticmethod
    def _similarity_score(a: Dict[str, Any], b: Dict[str, Any]) -> int:
        tags_a = set(a.get("labels", []))
        tags_b = set(b.get("labels", []))
        score = len(tags_a.intersection(tags_b))

        if a.get("service") == b.get("service"):
            score += 1
        if a.get("device") == b.get("device"):
            score += 1
        return score

    def correlate(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        correlated: List[Dict[str, Any]] = []
        clusters: List[Dict[str, Any]] = []

        for incident in incidents:
            labels = self._match_patterns(incident)
            incident_copy = dict(incident)
            incident_copy["labels"] = labels
            incident_copy["correlation_id"] = incident["id"]
            incident_copy["related_incidents"] = []
            clusters.append(incident_copy)

        for i, incident in enumerate(clusters):
            for j in range(i + 1, len(clusters)):
                other = clusters[j]
                score = self._similarity_score(incident, other)
                if score >= 2:
                    incident["related_incidents"].append(other["id"])
                    other["related_incidents"].append(incident["id"])

        for cluster in clusters:
            if cluster["related_incidents"]:
                group = {
                    "correlation_id": cluster["correlation_id"],
                    "primary_incident": cluster,
                    "related_incidents": [inc for inc in clusters if inc["id"] in cluster["related_incidents"]],
                }
                correlated.append(group)

        return correlated


correlation_engine = CorrelationEngine()
