import numpy as np
import pickle
import os
from collections import deque
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from db_config import get_connection
from datetime import datetime

MODEL_PATH     = "models/cognitive_model.pkl"
SCALER_PATH    = "models/cognitive_scaler.pkl"
os.makedirs("models", exist_ok=True)

# ── Cognitive load levels ─────────────────────────────────────────────────────
LEVELS = {
    0: ("LOW",      "#00C896", 0),    # name, color, autopilot_level
    1: ("MEDIUM",   "#FFB84C", 1),
    2: ("HIGH",     "#FF6B35", 2),
    3: ("CRITICAL", "#FF2020", 2),
}

# ── Autopilot descriptions ────────────────────────────────────────────────────
AUTOPILOT_ACTIONS = {
    0: "Autopilot OFF — Driver fully in control",
    1: "Autopilot ASSIST — Lane keeping + alerts active",
    2: "Autopilot ENGAGED — System taking control",
}


class CognitiveEngine:
    def __init__(self):
        self.model       = None
        self.scaler      = None
        self.history     = deque(maxlen=30)
        self.load_model()

    def load_model(self):
        """Load trained model or use rule-based fallback"""
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                self.scaler = pickle.load(f)
            print("[INFO] Cognitive model loaded.")
        else:
            print("[INFO] No trained model found — using rule-based engine.")

    def extract_features(self, face_metrics, vehicle_metrics):
        """
        Extract feature vector from face + vehicle metrics.
        Features: [ear, blink_rate, fatigue, head_pitch, head_yaw,
                   head_roll, steering_variance, brake_frequency, speed]
        """
        if face_metrics is None:
            ear = 0.25
            blink_rate = 20.0
            fatigue    = 0.5
            pitch = yaw = roll = 0.0
        else:
            ear        = face_metrics.get("ear", 0.25)
            blink_rate = face_metrics.get("blink_rate", 20.0)
            fatigue    = face_metrics.get("fatigue", 0.0)
            pitch      = face_metrics.get("head_pitch", 0.0)
            yaw        = face_metrics.get("head_yaw", 0.0)
            roll       = face_metrics.get("head_roll", 0.0)

        steer_var  = vehicle_metrics.get("steering_variance", 0.0)
        brake_freq = vehicle_metrics.get("brake_frequency", 0.0)
        speed      = vehicle_metrics.get("speed", 0.0) / 130.0  # normalise

        return np.array([
            ear, blink_rate / 40.0, fatigue,
            abs(pitch) / 30.0, abs(yaw) / 30.0, abs(roll) / 30.0,
            min(steer_var * 100, 1.0),
            min(brake_freq / 20.0, 1.0),
            speed
        ], dtype=np.float32)

    def rule_based_load(self, features):
        """
        Rule-based cognitive load when no ML model available.
        Returns load score 0.0 - 1.0
        """
        ear        = features[0]
        blink_norm = features[1]
        fatigue    = features[2]
        pitch_norm = features[3]
        yaw_norm   = features[4]
        steer_var  = features[6]
        brake_freq = features[7]

        # Abnormal blink rate (too slow = fatigue, too fast = stress)
        blink_score = abs(blink_norm - 0.45) * 1.5

        load = (
            fatigue    * 0.35 +
            (1 - ear / 0.35) * 0.20 +
            blink_score      * 0.15 +
            pitch_norm       * 0.10 +
            yaw_norm         * 0.10 +
            steer_var        * 0.05 +
            brake_freq       * 0.05
        )
        return float(np.clip(load, 0.0, 1.0))

    def predict(self, face_metrics, vehicle_metrics):
        """
        Predict cognitive load level and score.
        Returns (load_score, level_idx, level_name, color, autopilot_level, action)
        """
        features = self.extract_features(face_metrics, vehicle_metrics)
        self.history.append(features)

        # Smooth over recent history
        if len(self.history) >= 5:
            smooth = np.mean(list(self.history)[-5:], axis=0)
        else:
            smooth = features

        if self.model is not None:
            try:
                scaled  = self.scaler.transform([smooth])
                level   = int(self.model.predict(scaled)[0])
                proba   = self.model.predict_proba(scaled)[0]
                score   = float(np.dot(proba, [0.0, 0.33, 0.66, 1.0]))
            except Exception:
                score = self.rule_based_load(smooth)
                level = self._score_to_level(score)
        else:
            score = self.rule_based_load(smooth)
            level = self._score_to_level(score)

        level = min(3, max(0, level))
        name, color, autopilot = LEVELS[level]
        action = AUTOPILOT_ACTIONS[autopilot]

        return {
            "score":     round(score, 3),
            "level":     level,
            "name":      name,
            "color":     color,
            "autopilot": autopilot,
            "action":    action,
        }

    def _score_to_level(self, score):
        if score < 0.30:  return 0
        if score < 0.55:  return 1
        if score < 0.75:  return 2
        return 3

    def save_reading(self, session_id, result,
                      face_metrics, vehicle_metrics):
        """Save cognitive reading to SQL Server"""
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO CognitiveReadings
                (SessionID, CognitiveLoad, LoadLevel,
                 BlinkRate, EyeOpenness, HeadPitch, HeadYaw, HeadRoll,
                 FatigueScore, SteeringVariance, BrakeFrequency, AutopilotLevel)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                session_id,
                result["score"], result["name"],
                face_metrics.get("blink_rate", 0) if face_metrics else 0,
                face_metrics.get("eye_open",   0) if face_metrics else 0,
                face_metrics.get("head_pitch", 0) if face_metrics else 0,
                face_metrics.get("head_yaw",   0) if face_metrics else 0,
                face_metrics.get("head_roll",  0) if face_metrics else 0,
                face_metrics.get("fatigue",    0) if face_metrics else 0,
                vehicle_metrics.get("steering_variance", 0),
                vehicle_metrics.get("brake_frequency",   0),
                result["autopilot"]
            ))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"[ERROR] Save reading: {db_err}")

    def save_alert(self, session_id, alert_type, result):
        """Save alert to SQL Server"""
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO AlertLogs
                (SessionID, AlertType, CognitiveLoad, LoadLevel, AutopilotAction)
                VALUES (?,?,?,?,?)
            """, (session_id, alert_type,
                   result["score"], result["name"], result["action"]))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"[ERROR] Save alert: {db_err}")