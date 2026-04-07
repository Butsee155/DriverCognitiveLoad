import cv2
import numpy as np
import mediapipe as mp
from scipy.spatial import distance
from collections import deque
import time

mp_face_mesh = mp.solutions.face_mesh
face_mesh    = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# ── Landmark indices ──────────────────────────────────────────────────────────
# Left eye
LEFT_EYE  = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
# Right eye
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
# Eye corners for EAR
LEFT_EAR_PTS  = [362, 385, 387, 263, 373, 380]
RIGHT_EAR_PTS = [33,  160, 158, 133, 153, 144]
# Nose tip for head pose
NOSE_TIP  = 1
CHIN      = 152
LEFT_EYE_CORNER  = 33
RIGHT_EYE_CORNER = 263

# ── Config ────────────────────────────────────────────────────────────────────
EAR_THRESHOLD    = 0.22   # below = eye closed
BLINK_CONSEC     = 2      # frames for blink
PERCLOS_WINDOW   = 60     # frames for PERCLOS (% eye closure)


class FaceAnalyzer:
    def __init__(self):
        self.blink_counter   = 0
        self.blink_total     = 0
        self.blink_start     = time.time()
        self.ear_history     = deque(maxlen=PERCLOS_WINDOW)
        self.head_pitch_hist = deque(maxlen=30)
        self.head_yaw_hist   = deque(maxlen=30)
        self.frame_count     = 0
        self.last_blink_time = time.time()

    def eye_aspect_ratio(self, landmarks, eye_pts, w, h):
        """Calculate Eye Aspect Ratio (EAR)"""
        pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h))
               for i in eye_pts]
        # Vertical distances
        v1 = distance.euclidean(pts[1], pts[5])
        v2 = distance.euclidean(pts[2], pts[4])
        # Horizontal distance
        h1 = distance.euclidean(pts[0], pts[3])
        ear = (v1 + v2) / (2.0 * h1 + 1e-6)
        return ear

    def get_head_pose(self, landmarks, w, h):
        """Estimate head pitch, yaw, roll from facial landmarks"""
        nose  = landmarks[NOSE_TIP]
        chin  = landmarks[CHIN]
        l_eye = landmarks[LEFT_EYE_CORNER]
        r_eye = landmarks[RIGHT_EYE_CORNER]

        # Pitch (nodding up/down)
        nose_y  = nose.y * h
        chin_y  = chin.y * h
        pitch   = (nose_y - chin_y) / h * 180

        # Yaw (turning left/right)
        l_x     = l_eye.x * w
        r_x     = r_eye.x * w
        nose_x  = nose.x * w
        mid_x   = (l_x + r_x) / 2
        yaw     = (nose_x - mid_x) / w * 180

        # Roll (tilting)
        dy      = (r_eye.y - l_eye.y) * h
        dx      = (r_eye.x - l_eye.x) * w
        roll    = np.degrees(np.arctan2(dy, dx))

        return pitch, yaw, roll

    def get_fatigue_score(self, ear, pitch, yaw):
        """
        Calculate fatigue score 0.0 - 1.0 based on:
        - PERCLOS (% of time eyes are closed)
        - Eye openness
        - Head drooping (pitch)
        - Head turning (yaw)
        """
        self.ear_history.append(ear)

        # PERCLOS — % of frames where eyes are closed
        closed_frames = sum(1 for e in self.ear_history if e < EAR_THRESHOLD)
        perclos       = closed_frames / len(self.ear_history) if self.ear_history else 0

        # Eye openness score
        eye_score = max(0, min(1, (ear - EAR_THRESHOLD) / 0.15))

        # Head drooping score (pitch > 10 degrees = nodding)
        head_droop = max(0, min(1, abs(pitch) / 20.0))

        # Head yaw score (looking away > 15 degrees)
        head_yaw_score = max(0, min(1, abs(yaw) / 25.0))

        # Combined fatigue score
        fatigue = (
            perclos        * 0.35 +
            (1 - eye_score) * 0.30 +
            head_droop     * 0.20 +
            head_yaw_score * 0.15
        )
        return min(1.0, fatigue)

    def get_blink_rate(self, ear):
        """Returns blinks per minute"""
        is_closed = ear < EAR_THRESHOLD

        if is_closed:
            self.blink_counter += 1
        else:
            if self.blink_counter >= BLINK_CONSEC:
                self.blink_total += 1
                self.last_blink_time = time.time()
            self.blink_counter = 0

        # Blinks per minute
        elapsed = max(1, time.time() - self.blink_start)
        bpm     = (self.blink_total / elapsed) * 60
        return min(bpm, 60)  # cap at 60 bpm

    def analyse_frame(self, frame):
        """
        Full face analysis on a single frame.
        Returns dict of all metrics.
        """
        h, w = frame.shape[:2]
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark

        # EAR
        left_ear  = self.eye_aspect_ratio(landmarks, LEFT_EAR_PTS, w, h)
        right_ear = self.eye_aspect_ratio(landmarks, RIGHT_EAR_PTS, w, h)
        avg_ear   = (left_ear + right_ear) / 2.0

        # Head pose
        pitch, yaw, roll = self.get_head_pose(landmarks, w, h)

        # Blink rate
        blink_rate = self.get_blink_rate(avg_ear)

        # Fatigue score
        fatigue = self.get_fatigue_score(avg_ear, pitch, yaw)

        return {
            "ear":         avg_ear,
            "eye_open":    min(1.0, avg_ear / 0.35),
            "blink_rate":  blink_rate,
            "head_pitch":  pitch,
            "head_yaw":    yaw,
            "head_roll":   roll,
            "fatigue":     fatigue,
            "landmarks":   landmarks,
            "w": w, "h": h,
        }

    def draw_annotations(self, frame, metrics):
        """Draw face mesh and metrics on frame"""
        if metrics is None:
            cv2.putText(frame, "No face detected",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)
            return frame

        h, w     = frame.shape[:2]
        landmarks = metrics["landmarks"]

        # Draw eye landmarks
        for idx in LEFT_EAR_PTS + RIGHT_EAR_PTS:
            pt = (int(landmarks[idx].x * w),
                  int(landmarks[idx].y * h))
            cv2.circle(frame, pt, 2, (0, 255, 255), -1)

        # Draw nose point
        nose = (int(landmarks[NOSE_TIP].x * w),
                int(landmarks[NOSE_TIP].y * h))
        cv2.circle(frame, nose, 4, (255, 0, 0), -1)

        # Eye status
        eye_color = (0, 255, 0) if metrics["ear"] > EAR_THRESHOLD else (0, 0, 255)
        cv2.putText(frame, f"EAR: {metrics['ear']:.3f}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, eye_color, 1)
        cv2.putText(frame, f"Blink: {metrics['blink_rate']:.1f}/min",
                    (10, 45), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (200, 200, 200), 1)
        cv2.putText(frame, f"Pitch: {metrics['head_pitch']:.1f}",
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (200, 200, 200), 1)
        cv2.putText(frame, f"Yaw: {metrics['head_yaw']:.1f}",
                    (10, 85), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (200, 200, 200), 1)
        cv2.putText(frame, f"Fatigue: {metrics['fatigue']:.2f}",
                    (10, 105), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 150, 0), 1)

        return frame