import time
import datetime
import random
import requests

URL = "http://127.0.0.1:8000/api/ingest"

# Simulator State Machine
state = "NORMAL"
anomaly_ticks = 0
active_scenario = None

SCENARIOS = [
    "ISP_DEGRADATION",       # high packet loss
    "BANDWIDTH_SATURATION",   # high bandwidth + latency
    "ROUTE_INSTABILITY",     # high latency + jitter
    "CRC_ERRORS"             # moderate packet loss
]

def generate_metrics():
    global state, anomaly_ticks, active_scenario
    
    # State transitions
    if state == "NORMAL":
        # 12% chance to transition to an anomaly state
        if random.random() < 0.12:
            state = "ANOMALY"
            active_scenario = random.choice(SCENARIOS)
            anomaly_ticks = random.randint(3, 5)  # lasts 3-5 ticks (6-10s)
            print(f"\n>>> EVENT TRIGGERED: System entering anomaly state ({active_scenario}) for {anomaly_ticks} updates <<<")
    else:
        anomaly_ticks -= 1
        if anomaly_ticks <= 0:
            state = "NORMAL"
            active_scenario = None
            print("\n>>> EVENT RESOLVED: System returning to normal baseline operation <<<")
            
    # Metrics generation based on state
    if state == "NORMAL":
        latency = random.uniform(18.0, 32.0)
        packet_loss = random.uniform(0.1, 1.2)
        jitter = random.uniform(2.5, 6.5)
        bandwidth = random.uniform(30.0, 50.0)
    else:
        # Generate anomalous metrics tailored to specific scenarios
        if active_scenario == "ISP_DEGRADATION":
            latency = random.uniform(60.0, 95.0)
            packet_loss = random.uniform(65.0, 85.0)  # Critically high
            jitter = random.uniform(8.0, 14.0)
            bandwidth = random.uniform(5.0, 15.0)     # Low utilization
        elif active_scenario == "BANDWIDTH_SATURATION":
            latency = random.uniform(80.0, 120.0)     # High delay due to queuing
            packet_loss = random.uniform(2.0, 5.0)     # Heavy drops
            jitter = random.uniform(9.0, 14.0)
            bandwidth = random.uniform(88.0, 98.0)     # Maxed out bandwidth
        elif active_scenario == "ROUTE_INSTABILITY":
            latency = random.uniform(150.0, 220.0)    # Suboptimal high latency path
            packet_loss = random.uniform(1.0, 2.5)
            jitter = random.uniform(14.0, 24.0)        # Extreme jitter
            bandwidth = random.uniform(20.0, 40.0)
        elif active_scenario == "CRC_ERRORS":
            latency = random.uniform(22.0, 35.0)
            packet_loss = random.uniform(6.0, 14.0)    # High packet loss
            jitter = random.uniform(3.0, 7.5)
            bandwidth = random.uniform(25.0, 45.0)
        else:
            # Fallback random spike
            latency = random.uniform(70.0, 110.0)
            packet_loss = random.uniform(5.0, 12.0)
            jitter = random.uniform(8.0, 12.0)
            bandwidth = random.uniform(75.0, 85.0)

    timestamp = datetime.datetime.now().isoformat()
    
    return {
        "timestamp": timestamp,
        "latency": round(latency, 2),
        "packet_loss": round(packet_loss, 2),
        "jitter": round(jitter, 2),
        "bandwidth": round(bandwidth, 2)
    }

def main():
    print("==================================================")
    print("   AI NOC COPILOT - SD-WAN TELEMETRY SIMULATOR    ")
    print("==================================================")
    print(f"Target Backend API: {URL}")
    print("Streaming interval: 2 seconds")
    print("Press Ctrl+C to terminate.")
    print("--------------------------------------------------")
    
    while True:
        metrics = generate_metrics()
        try:
            response = requests.post(URL, json=metrics, timeout=2)
            if response.status_code == 200:
                print(f"[POST SUCCESS] Lat={metrics['latency']}ms | Loss={metrics['packet_loss']}% | Jitter={metrics['jitter']}ms | BW={metrics['bandwidth']}%")
            else:
                print(f"[POST ERROR] Received response code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[CONNECTION ERROR] Backend offline: {e}. Retrying in 2 seconds...")
            
        time.sleep(2)

if __name__ == "__main__":
    main()
