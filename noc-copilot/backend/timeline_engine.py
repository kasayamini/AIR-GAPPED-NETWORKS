import datetime
from typing import Any, Dict, List


class TimelineEngine:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _format_step(timestamp: str, description: str) -> Dict[str, Any]:
        return {
            "timestamp": timestamp,
            "description": description,
        }

    def build_timeline(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        timeline: List[Dict[str, Any]] = []
        for incident in sorted(incidents, key=lambda value: value.get("timestamp", "")):
            timestamp = incident.get("timestamp") or datetime.datetime.utcnow().isoformat()
            summary = incident.get("summary", incident.get("incident", "Incident event"))
            timeline.append(self._format_step(timestamp, summary))

        if not timeline:
            timeline.append(self._format_step(datetime.datetime.utcnow().isoformat(), "No incident events have been detected."))

        return timeline


timeline_engine = TimelineEngine()
