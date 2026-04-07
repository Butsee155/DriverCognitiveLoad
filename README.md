# 🚗 Real-Time Driver Cognitive Load Predictor

> An AI-powered real-time system that analyses driver eye movement, head position, facial expressions, steering micro-corrections, and braking behaviour to predict cognitive load and fatigue — automatically adjusting autopilot engagement level accordingly.

---

## 📌 Overview

The **Real-Time Driver Cognitive Load Predictor** is a desktop application that monitors a driver's cognitive state in real time using a combination of computer vision, facial landmark analysis, and vehicle input signals. The system continuously analyses six data streams — eye movement, blink rate, head position, facial expressions, steering micro-corrections, and braking frequency — and combines them into a unified cognitive load score. Based on this score, the system automatically adjusts the autopilot engagement level and triggers alerts when the driver's mental presence falls below safe thresholds.

> This project addresses a genuine gap in current automotive AI: Tesla and other manufacturers have cameras inside vehicles but no system that truly measures *how mentally present* the driver is beyond basic eye tracking.

---

## ✨ Features

- 👁 **Eye Tracking** — EAR (Eye Aspect Ratio) + PERCLOS blink detection
- 🎯 **Head Pose Estimation** — Pitch, Yaw, Roll via MediaPipe FaceMesh
- 😴 **Fatigue Scoring** — Combined PERCLOS + eye openness + head drooping
- 🚗 **Steering Analysis** — Micro-correction variance from steering wheel controller
- 🛑 **Brake Analysis** — Brake frequency per minute
- 🧠 **Cognitive Load Engine** — Rule-based + Gradient Boosting ML model
- 🤖 **Autopilot Adjustment** — 3 levels: OFF / ASSIST / ENGAGED — auto-adjusts
- 📊 **Live History Chart** — 60-second cognitive load trend graph
- ⚠️ **Alert System** — Sound + overlay popup on HIGH / CRITICAL load
- 💾 **SQL Server Logging** — Sessions, readings, and alerts auto-saved
- 📊 **Admin Dashboard** — Full stats, session history, readings, alerts
- 📤 **Export Reports** — Excel and CSV export for all data

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10 |
| Face & Eye Analysis | MediaPipe FaceMesh (468 landmarks) |
| Image Processing | OpenCV |
| ML Model | Scikit-learn (Gradient Boosting Classifier) |
| Fatigue Algorithm | EAR + PERCLOS + Head Pose fusion |
| Controller Input | pygame (steering wheel / joystick / keyboard) |
| GUI Framework | Tkinter (Tesla-style dark + red theme) |
| Database | Microsoft SQL Server 2019 + SSMS 20 |
| DB Connector | pyodbc |
| Export | openpyxl, csv |

---

## 📁 Project Structure

```
DriverCognitiveLoad/
│
├── main_app.py              # Login screen & session launcher
├── driver_monitor.py        # Real-time monitoring dashboard
├── face_analyzer.py         # Eye tracking + head pose + fatigue analysis
├── vehicle_simulator.py     # Steering wheel + keyboard input handler
├── cognitive_engine.py      # ML cognitive load prediction engine
├── alert_system.py          # Sound + visual overlay alerts
├── dashboard.py             # Admin dashboard (sessions, readings, export)
├── db_config.py             # SQL Server connection
├── models/
│   ├── cognitive_model.pkl  # Trained Gradient Boosting model
│   └── cognitive_scaler.pkl # Feature scaler
└── data/
    └── training_data.csv    # Labelled training dataset
```

---

## 🗄️ Database Schema

```sql
CREATE DATABASE DriverCognitiveLoad;

-- Driving sessions
CREATE TABLE DrivingSessions (
    SessionID        INT IDENTITY(1,1) PRIMARY KEY,
    DriverName       VARCHAR(200),
    StartTime        DATETIME DEFAULT GETDATE(),
    EndTime          DATETIME,
    AvgCognitiveLoad FLOAT,
    MaxCognitiveLoad FLOAT,
    AlertsTriggered  INT DEFAULT 0,
    SessionDuration  INT
);

-- Real-time readings (sampled every 5 seconds)
CREATE TABLE CognitiveReadings (
    ReadingID        INT IDENTITY(1,1) PRIMARY KEY,
    SessionID        INT,
    CognitiveLoad    FLOAT,
    LoadLevel        VARCHAR(20),   -- LOW/MEDIUM/HIGH/CRITICAL
    BlinkRate        FLOAT,
    EyeOpenness      FLOAT,
    HeadPitch        FLOAT,
    HeadYaw          FLOAT,
    FatigueScore     FLOAT,
    SteeringVariance FLOAT,
    BrakeFrequency   FLOAT,
    AutopilotLevel   INT,           -- 0=OFF 1=ASSIST 2=ENGAGED
    Timestamp        DATETIME DEFAULT GETDATE()
);

-- Alert logs
CREATE TABLE AlertLogs (
    AlertID         INT IDENTITY(1,1) PRIMARY KEY,
    SessionID       INT,
    AlertType       VARCHAR(100),
    CognitiveLoad   FLOAT,
    LoadLevel       VARCHAR(20),
    AutopilotAction VARCHAR(200),
    AlertTime       DATETIME DEFAULT GETDATE()
);
```

---

## ⚙️ Installation & Setup

### 1. Create Virtual Environment (Recommended)
```bash
py -3.10 -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install mediapipe==0.10.9 opencv-python numpy pandas scikit-learn pyodbc pillow openpyxl pygame scipy inputs
```

### 3. Set Up Database
Run the SQL script in SSMS to create the database and all tables.

### 4. Configure Connection
Edit `db_config.py` with your SQL Server instance name.

### 5. Launch
```bash
python main_app.py
```

> Default password: `admin123`

### Keyboard Controls (if no steering wheel)
| Key | Action |
|---|---|
| ← → Arrows | Steer left / right |
| ↑ Arrow | Accelerate |
| ↓ / Space | Brake |

---

## 🧠 How Cognitive Load Is Calculated

The system fuses 9 biometric and behavioural signals into a single cognitive load score (0.0 – 1.0):

| Signal | Weight | What It Measures |
|---|---|---|
| PERCLOS | 35% | % of time eyes are closed |
| Eye Openness (EAR) | 20% | Real-time eye opening ratio |
| Blink Rate | 15% | Abnormal blink frequency |
| Head Pitch | 10% | Forward head drooping |
| Head Yaw | 10% | Looking away from road |
| Steering Variance | 5% | Erratic micro-corrections |
| Brake Frequency | 5% | Panic braking patterns |

### Autopilot Engagement Levels
| Load Score | Level | Autopilot Action |
|---|---|---|
| 0.00 – 0.30 | LOW | OFF — Driver fully in control |
| 0.30 – 0.55 | MEDIUM | ASSIST — Lane keeping + alerts |
| 0.55 – 0.75 | HIGH | ENGAGED — System taking control |
| 0.75 – 1.00 | CRITICAL | ENGAGED — Emergency intervention |

---

## ⚠️ Challenges & Solutions

| Challenge | Solution |
|---|---|
| protobuf version conflict between MediaPipe and TensorFlow | Used dedicated virtual environment per project to isolate dependencies |
| EAR threshold varies per person | Used relative PERCLOS (% over time window) instead of absolute threshold |
| Steering wheel axis mapping varies by controller brand | Built auto-detection with keyboard fallback for universal compatibility |
| False fatigue detection from looking at mirrors | Added minimum duration threshold — blink/head events must persist for N frames |
| UI freezing during heavy face analysis | Processed every 2nd frame only and ran DB saves in background threads |

---

## 📸 Screenshots

> _Add your screenshots here_

| Login Screen | Live Monitor |
|---|---|
| ![Login](screenshots/login.png) | ![Monitor](screenshots/monitor.png) |

| Cognitive Load Gauge | Admin Dashboard |
|---|---|
| ![Gauge](screenshots/gauge.png) | ![Dashboard](screenshots/dashboard.png) |

---

## 🔮 Future Improvements

- [ ] Trained ML model on real driver fatigue datasets (NTHU, UTA-RLDD)
- [ ] Physiological signal integration (heart rate via smartwatch API)
- [ ] Vehicle CAN bus integration for real steering/braking data
- [ ] Edge deployment on Raspberry Pi / NVIDIA Jetson
- [ ] Multi-driver profile personalisation
- [ ] Integration with Tesla API / FSD system

---

## 👤 Author

**R.M. Nisitha Nethsilu**
🔗 [LinkedIn](https://linkedin.com/in/nisithanethsilu)
🐙 [GitHub](https://github.com/Butsee155)

---

## 📄 License

This project is licensed under the MIT License.

---

> ⭐ If you found this project interesting, please give it a star!
