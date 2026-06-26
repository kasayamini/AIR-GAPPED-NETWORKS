class RCAEngine:
    @staticmethod
    def analyze(metrics: dict, is_anomaly: bool) -> dict:
        """
        Analyze telemetry metrics and return a root cause explanation if anomalous.
        """
        if not is_anomaly:
            return {
                "cause": "Normal Operation",
                "impact": "All network pathways are performing within normal operational baselines.",
                "confidence": 100
            }

        latency = metrics.get("latency", 0.0)
        packet_loss = metrics.get("packet_loss", 0.0)
        jitter = metrics.get("jitter", 0.0)
        bandwidth = metrics.get("bandwidth", 0.0)

        # Rule evaluation
        # Rule 1: Extreme packet loss (critical link degradation / ISP outage)
        if packet_loss > 40:
            return {
                "cause": "Critical ISP / Link Degradation",
                "impact": f"High packet loss ({packet_loss:.1f}%) is causing connection drops, broken VPN tunnels, and application failures.",
                "confidence": 95
            }
            
        # Rule 2: Bandwidth saturation
        elif bandwidth > 85:
            cause = "Bandwidth Saturation / Traffic Overload"
            impact = f"High bandwidth utilization ({bandwidth:.1f}%) is causing link congestion, queue delays, and minor packet loss."
            if latency > 70:
                impact += " Latency is also spiking due to queuing delay."
                confidence = 90
            else:
                confidence = 85
            return {
                "cause": cause,
                "impact": impact,
                "confidence": confidence
            }
            
        # Rule 3: Jitter + Latency spike (Route instability / routing loop)
        elif latency > 80 and jitter > 12:
            return {
                "cause": "SD-WAN Path Route Instability",
                "impact": f"High latency ({latency:.1f}ms) and jitter ({jitter:.1f}ms) indicate packet routing flux, leading to jitter buffer depletion and poor VoIP/video calls.",
                "confidence": 88
            }
            
        # Rule 4: Moderate latency spike
        elif latency > 100:
            return {
                "cause": "Routing Path Suboptimality",
                "impact": f"Increased latency ({latency:.1f}ms) suggests the SD-WAN controller may have routed traffic through a backup high-metric link or satellite path.",
                "confidence": 80
            }
            
        # Rule 5: Moderate packet loss
        elif packet_loss > 5:
            return {
                "cause": "Interface CRC Errors / Wireless Interference",
                "impact": f"Moderate packet loss ({packet_loss:.1f}%) is forcing TCP retransmissions, slowing down file transfers and web browsing.",
                "confidence": 75
            }
            
        # Rule 6: Jitter alone
        elif jitter > 15:
            return {
                "cause": "Micro-congestion on Switch Interfaces",
                "impact": f"Elevated jitter ({jitter:.1f}ms) points to intermittent bursty traffic causing inconsistent queuing times.",
                "confidence": 70
            }

        # Rule 7: Default case for statistical outliers detected by ML
        else:
            return {
                "cause": "Statistical Telemetry Outlier",
                "impact": "The telemetry profile deviates from the baseline model on multiple metrics simultaneously without exceeding individual hard thresholds.",
                "confidence": 65
            }

rca_engine = RCAEngine()
