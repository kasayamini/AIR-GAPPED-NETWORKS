import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.02, random_state=42)
        self.is_trained = False
        self.train_on_normal()

    def train_on_normal(self):
        # Generate 1000 normal baseline samples
        np.random.seed(42)
        n_samples = 1000
        
        # Normal ranges:
        # Latency: 15-35 ms
        # Packet Loss: 0-1.5 %
        # Jitter: 2-8 ms
        # Bandwidth: 25-65 %
        latency = np.random.normal(25, 4, n_samples)
        packet_loss = np.random.normal(0.4, 0.2, n_samples)
        packet_loss = np.clip(packet_loss, 0, 100)
        jitter = np.random.normal(5, 1.2, n_samples)
        bandwidth = np.random.normal(45, 8, n_samples)
        bandwidth = np.clip(bandwidth, 0, 100)
        
        df = pd.DataFrame({
            'latency': latency,
            'packet_loss': packet_loss,
            'jitter': jitter,
            'bandwidth': bandwidth
        })
        
        self.model.fit(df)
        self.is_trained = True
        print("ML Model (Isolation Forest) trained successfully on normal baseline.")

    def predict(self, latency: float, packet_loss: float, jitter: float, bandwidth: float):
        if not self.is_trained:
            self.train_on_normal()
            
        df = pd.DataFrame([{
            'latency': latency,
            'packet_loss': packet_loss,
            'jitter': jitter,
            'bandwidth': bandwidth
        }])
        
        prediction = self.model.predict(df)[0]
        # decision_function: lower score means more anomalous.
        # Typically yields values in [-0.5, 0.5]
        score = self.model.decision_function(df)[0]
        
        is_anomaly = bool(prediction == -1)
        
        # Normalize anomaly score to [0, 100] range for UI presentation
        # If score is > 0 (normal), map to [0, 49]. If < 0 (anomalous), map to [50, 100].
        if score >= 0:
            # high score (0.3) -> 0 anomaly, low score (0.0) -> 49 anomaly
            anomaly_score = int(max(0, min(49, (1.0 - (score / 0.3)) * 50)))
        else:
            # negative score (-0.1) -> 60 anomaly, very negative (-0.4) -> 100 anomaly
            anomaly_score = int(max(50, min(100, 50 + (abs(score) / 0.4) * 50)))
            
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "decision_score": float(score)
        }

# Global detector instance
detector = AnomalyDetector()
