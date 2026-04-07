import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import pygame
import numpy as np
import threading
import time
from PIL import Image, ImageTk
from datetime import datetime
from face_analyzer import FaceAnalyzer
from vehicle_simulator import VehicleSimulator
from cognitive_engine import CognitiveEngine
from alert_system import play_alert, show_alert_overlay
from db_config import get_connection

# ── Tesla-style colours ───────────────────────────────────────────────────────
BG_DARK    = "#0A0A0A"
BG_PANEL   = "#111111"
BG_CARD    = "#1A1A1A"
TESLA_RED  = "#E31937"
TESLA_GRAY = "#393C41"
TEXT_WHITE = "#FFFFFF"
TEXT_GRAY  = "#8E8E93"
SUCCESS    = "#00C896"
WARNING    = "#FFB84C"
DANGER     = "#FF4C4C"
CRITICAL   = "#FF2020"


class DriverMonitor:
    def __init__(self, root, driver_name, session_id):
        self.root        = root
        self.driver_name = driver_name
        self.session_id  = session_id
        self.root.title(f"Tesla Cognitive Monitor — {driver_name}")
        self.root.geometry("1400x820")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        self.center(1400, 820)

        # ── Components ────────────────────────────────────────────────────────
        self.face_analyzer   = FaceAnalyzer()
        self.vehicle_sim     = VehicleSimulator()
        self.cognitive_engine = CognitiveEngine()

        # ── State ─────────────────────────────────────────────────────────────
        self.cap             = cv2.VideoCapture(0)
        self.running         = True
        self.frame_count     = 0
        self.last_save       = time.time()
        self.last_alert      = time.time()
        self.alert_cooldown  = 8      # seconds between alerts
        self.save_interval   = 5      # save reading every 5 seconds
        self.current_result  = None
        self.session_start   = time.time()

        # ── History for charts ────────────────────────────────────────────────
        self.load_history    = [0.0] * 60
        self.alert_count     = 0

        self.build_ui()
        self.update_frame()
        self.update_clock()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Build UI ──────────────────────────────────────────────────────────────
    def build_ui(self):
        # ── Top bar ───────────────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=BG_PANEL, height=55)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        # Tesla logo style
        tk.Label(topbar, text="T",
                 font=("Segoe UI", 22, "bold"),
                 bg=BG_PANEL, fg=TESLA_RED).pack(side="left", padx=(20, 5), pady=8)
        tk.Label(topbar, text="COGNITIVE LOAD MONITOR",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack(side="left", pady=15)

        self.clock_var = tk.StringVar()
        tk.Label(topbar, textvariable=self.clock_var,
                 font=("Segoe UI", 10),
                 bg=BG_PANEL, fg=TEXT_GRAY).pack(side="right", padx=20)

        tk.Label(topbar, text=f"Driver: {self.driver_name}",
                 font=("Segoe UI", 10),
                 bg=BG_PANEL, fg=TEXT_GRAY).pack(side="right", padx=20)

        tk.Button(topbar, text="END SESSION",
                  font=("Segoe UI", 9, "bold"),
                  bg=TESLA_RED, fg=TEXT_WHITE, relief="flat",
                  cursor="hand2", padx=12,
                  command=self.on_close).pack(side="right", pady=10, padx=10)

        tk.Frame(self.root, bg=TESLA_RED, height=2).pack(fill="x")

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        # ── Left: Camera feed ─────────────────────────────────────────────────
        left = tk.Frame(body, bg=BG_DARK, width=520)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="DRIVER CAMERA",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_DARK, fg=TEXT_GRAY).pack(anchor="w", pady=(0, 4))

        self.cam_label = tk.Label(left, bg="#000000",
                                   text="Initializing camera...",
                                   font=("Segoe UI", 11), fg=TEXT_GRAY)
        self.cam_label.pack(fill="both", expand=True)

        # Eye status bar
        eye_bar = tk.Frame(left, bg=BG_CARD)
        eye_bar.pack(fill="x", pady=(6, 0))
        self.eye_status = tk.Label(eye_bar, text="👁  Eyes Open",
                                    font=("Segoe UI", 9),
                                    bg=BG_CARD, fg=SUCCESS)
        self.eye_status.pack(side="left", padx=10, pady=6)
        self.head_status = tk.Label(eye_bar, text="🎯  Head Forward",
                                     font=("Segoe UI", 9),
                                     bg=BG_CARD, fg=SUCCESS)
        self.head_status.pack(side="right", padx=10)

        # ── Centre: Cognitive Load Gauge ──────────────────────────────────────
        centre = tk.Frame(body, bg=BG_DARK, width=380)
        centre.pack(side="left", fill="both", padx=(0, 10))
        centre.pack_propagate(False)

        # Main load display
        self.gauge_frame = tk.Frame(centre, bg=BG_CARD)
        self.gauge_frame.pack(fill="x", pady=(0, 8))

        tk.Label(self.gauge_frame, text="COGNITIVE LOAD",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(pady=(12, 4))

        self.load_score_var = tk.StringVar(value="0.00")
        self.load_score_lbl = tk.Label(self.gauge_frame,
                                        textvariable=self.load_score_var,
                                        font=("Segoe UI", 52, "bold"),
                                        bg=BG_CARD, fg=SUCCESS)
        self.load_score_lbl.pack()

        self.load_level_var = tk.StringVar(value="LOW")
        self.load_level_lbl = tk.Label(self.gauge_frame,
                                        textvariable=self.load_level_var,
                                        font=("Segoe UI", 16, "bold"),
                                        bg=BG_CARD, fg=SUCCESS)
        self.load_level_lbl.pack(pady=(0, 8))

        # Load bar
        bar_frame = tk.Frame(self.gauge_frame, bg=BG_CARD)
        bar_frame.pack(fill="x", padx=20, pady=(0, 12))
        self.load_bar_bg = tk.Frame(bar_frame, bg=TESLA_GRAY, height=14)
        self.load_bar_bg.pack(fill="x")
        self.load_bar    = tk.Frame(self.load_bar_bg, bg=SUCCESS,
                                     height=14, width=0)
        self.load_bar.place(x=0, y=0, relheight=1)

        # Autopilot status
        self.ap_frame = tk.Frame(centre, bg=BG_CARD)
        self.ap_frame.pack(fill="x", pady=(0, 8))

        tk.Label(self.ap_frame, text="AUTOPILOT STATUS",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Frame(self.ap_frame, bg=TESLA_RED, height=1).pack(fill="x", padx=14)

        self.ap_level_var = tk.StringVar(value="OFF")
        tk.Label(self.ap_frame, textvariable=self.ap_level_var,
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_CARD, fg=SUCCESS).pack(pady=6)

        self.ap_action_var = tk.StringVar(value="Driver fully in control")
        tk.Label(self.ap_frame, textvariable=self.ap_action_var,
                 font=("Segoe UI", 8),
                 bg=BG_CARD, fg=TEXT_GRAY,
                 wraplength=340).pack(pady=(0, 10))

        # Session stats
        stats = tk.Frame(centre, bg=BG_CARD)
        stats.pack(fill="x")
        tk.Label(stats, text="SESSION STATS",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Frame(stats, bg=TESLA_RED, height=1).pack(fill="x", padx=14)

        self.stat_vars = {}
        for label, key in [
            ("Duration",   "duration"),
            ("Avg Load",   "avg_load"),
            ("Alerts",     "alerts"),
            ("Max Load",   "max_load"),
        ]:
            row = tk.Frame(stats, bg=BG_CARD)
            row.pack(fill="x", padx=14, pady=4)
            tk.Label(row, text=label, font=("Segoe UI", 9),
                     bg=BG_CARD, fg=TEXT_GRAY,
                     width=12, anchor="w").pack(side="left")
            var = tk.StringVar(value="—")
            self.stat_vars[key] = var
            tk.Label(row, textvariable=var,
                     font=("Segoe UI", 9, "bold"),
                     bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
        tk.Frame(stats, height=8, bg=BG_CARD).pack()

        # ── Right: Vehicle + Metrics ──────────────────────────────────────────
        right = tk.Frame(body, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)

        # Vehicle metrics
        veh = tk.Frame(right, bg=BG_CARD)
        veh.pack(fill="x", pady=(0, 8))
        tk.Label(veh, text="VEHICLE & DRIVER METRICS",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Frame(veh, bg=TESLA_RED, height=1).pack(fill="x", padx=14)

        self.metric_vars = {}
        metrics_list = [
            ("🚗  Speed",           "speed",     "km/h"),
            ("🔄  Steering Var",    "steer_var", ""),
            ("🛑  Brake Freq",      "brake_freq","bpm"),
            ("👁  Eye Openness",    "eye_open",  "%"),
            ("💤  Blink Rate",      "blink_rate","bpm"),
            ("😴  Fatigue Score",   "fatigue",   ""),
            ("↕  Head Pitch",      "pitch",     "°"),
            ("↔  Head Yaw",        "yaw",       "°"),
        ]
        grid = tk.Frame(veh, bg=BG_CARD)
        grid.pack(fill="x", padx=14, pady=8)

        for i, (label, key, unit) in enumerate(metrics_list):
            cell = tk.Frame(grid, bg=BG_PANEL)
            cell.grid(row=i//2, column=i%2, padx=5, pady=3, sticky="ew")
            grid.columnconfigure(i%2, weight=1)
            tk.Label(cell, text=label, font=("Segoe UI", 8),
                     bg=BG_PANEL, fg=TEXT_GRAY).pack(anchor="w", padx=8, pady=(5, 0))
            var = tk.StringVar(value="—")
            self.metric_vars[key] = var
            tk.Label(cell, textvariable=var,
                     font=("Segoe UI", 11, "bold"),
                     bg=BG_PANEL, fg=TEXT_WHITE).pack(anchor="w", padx=8, pady=(0, 5))

        # Load history mini chart (canvas)
        chart_frame = tk.Frame(right, bg=BG_CARD)
        chart_frame.pack(fill="both", expand=True)
        tk.Label(chart_frame, text="COGNITIVE LOAD HISTORY",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Frame(chart_frame, bg=TESLA_RED, height=1).pack(fill="x", padx=14)
        self.chart_canvas = tk.Canvas(chart_frame, bg=BG_PANEL,
                                       highlightthickness=0, height=150)
        self.chart_canvas.pack(fill="both", expand=True,
                                padx=14, pady=8)

        # Recent alerts
        alerts_frame = tk.Frame(right, bg=BG_CARD)
        alerts_frame.pack(fill="x")
        tk.Label(alerts_frame, text="RECENT ALERTS",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Frame(alerts_frame, bg=TESLA_RED, height=1).pack(fill="x", padx=14)

        style = ttk.Style()
        style.configure("Tesla.Treeview",
                         background=BG_PANEL, foreground=TEXT_WHITE,
                         fieldbackground=BG_PANEL, rowheight=24,
                         font=("Segoe UI", 8))
        style.configure("Tesla.Treeview.Heading",
                         background=BG_CARD, foreground=TESLA_RED,
                         font=("Segoe UI", 8, "bold"))

        self.alert_tree = ttk.Treeview(alerts_frame,
                                        columns=("Time", "Level", "Action"),
                                        show="headings",
                                        style="Tesla.Treeview", height=4)
        for col, w in zip(("Time", "Level", "Action"), [70, 80, 200]):
            self.alert_tree.heading(col, text=col)
            self.alert_tree.column(col, width=w)
        self.alert_tree.pack(fill="x", padx=14, pady=(0, 10))

    # ── Main Frame Update Loop ────────────────────────────────────────────────
    def update_frame(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        self.frame_count += 1

        # ── Get vehicle inputs ────────────────────────────────────────────────
        try:
            keys = pygame.key.get_pressed()
            self.vehicle_sim.update(keys)
        except Exception:
            self.vehicle_sim.update(None)

        vehicle_metrics = self.vehicle_sim.get_metrics()

        # ── Analyse face every 2nd frame ──────────────────────────────────────
        face_metrics = None
        if ret and frame is not None and self.frame_count % 2 == 0:
            frame        = cv2.resize(frame, (500, 380))
            face_metrics = self.face_analyzer.analyse_frame(frame)
            frame        = self.face_analyzer.draw_annotations(frame, face_metrics)
        elif ret and frame is not None:
            frame = cv2.resize(frame, (500, 380))

        # ── Predict cognitive load ────────────────────────────────────────────
        result = self.cognitive_engine.predict(face_metrics, vehicle_metrics)
        self.current_result = result

        # ── Update load history ───────────────────────────────────────────────
        self.load_history.append(result["score"])
        if len(self.load_history) > 60:
            self.load_history.pop(0)

        # ── Update UI ─────────────────────────────────────────────────────────
        self.root.after(0, lambda: self._update_ui(
            result, face_metrics, vehicle_metrics, frame))

        # ── Save reading every N seconds ──────────────────────────────────────
        if time.time() - self.last_save > self.save_interval:
            threading.Thread(
                target=self.cognitive_engine.save_reading,
                args=(self.session_id, result, face_metrics, vehicle_metrics),
                daemon=True).start()
            self.last_save = time.time()

        # ── Trigger alert if needed ───────────────────────────────────────────
        if (result["level"] >= 2 and
                time.time() - self.last_alert > self.alert_cooldown):
            self._trigger_alert(result)
            self.last_alert = time.time()

        # ── Schedule next frame ───────────────────────────────────────────────
        self.root.after(33, self.update_frame)

    def _update_ui(self, result, face_metrics, vehicle_metrics, frame):
        """Update all UI elements with latest data"""
        try:
            color = result["color"]
            score = result["score"]
            level = result["name"]

            # ── Load gauge ────────────────────────────────────────────────────
            self.load_score_var.set(f"{score:.2f}")
            self.load_level_var.set(level)
            self.load_score_lbl.config(fg=color)
            self.load_level_lbl.config(fg=color)

            # Load bar
            self.load_bar_bg.update_idletasks()
            bar_w = int(score * self.load_bar_bg.winfo_width())
            self.load_bar.place(x=0, y=0, width=bar_w, relheight=1)
            self.load_bar.config(bg=color)

            # ── Autopilot ─────────────────────────────────────────────────────
            ap_names = {0: "OFF", 1: "ASSIST", 2: "ENGAGED"}
            ap_colors = {0: SUCCESS, 1: WARNING, 2: TESLA_RED}
            ap_lv     = result["autopilot"]
            self.ap_level_var.set(f"AUTOPILOT {ap_names[ap_lv]}")
            self.ap_action_var.set(result["action"])
            for w in self.ap_frame.winfo_children():
                if isinstance(w, tk.Label) and w.cget("textvariable") == str(self.ap_level_var):
                    w.config(fg=ap_colors[ap_lv])

            # ── Session stats ─────────────────────────────────────────────────
            elapsed = int(time.time() - self.session_start)
            mins    = elapsed // 60
            secs    = elapsed % 60
            self.stat_vars["duration"].set(f"{mins:02d}:{secs:02d}")
            avg = np.mean(self.load_history) if self.load_history else 0
            self.stat_vars["avg_load"].set(f"{avg:.2f}")
            self.stat_vars["alerts"].set(str(self.alert_count))
            self.stat_vars["max_load"].set(f"{max(self.load_history):.2f}"
                                            if self.load_history else "—")

            # ── Vehicle metrics ───────────────────────────────────────────────
            self.metric_vars["speed"].set(
                f"{vehicle_metrics['speed']:.0f} km/h")
            self.metric_vars["steer_var"].set(
                f"{vehicle_metrics['steering_variance']:.4f}")
            self.metric_vars["brake_freq"].set(
                f"{vehicle_metrics['brake_frequency']:.1f}")

            if face_metrics:
                self.metric_vars["eye_open"].set(
                    f"{face_metrics['eye_open']*100:.0f}%")
                self.metric_vars["blink_rate"].set(
                    f"{face_metrics['blink_rate']:.1f}")
                self.metric_vars["fatigue"].set(
                    f"{face_metrics['fatigue']:.2f}")
                self.metric_vars["pitch"].set(
                    f"{face_metrics['head_pitch']:.1f}°")
                self.metric_vars["yaw"].set(
                    f"{face_metrics['head_yaw']:.1f}°")

                # Eye status
                is_open = face_metrics["ear"] > 0.22
                self.eye_status.config(
                    text="👁  Eyes Open" if is_open else "😴  Eyes Closed",
                    fg=SUCCESS if is_open else DANGER)

                # Head status
                is_fwd = (abs(face_metrics["head_pitch"]) < 12 and
                           abs(face_metrics["head_yaw"]) < 15)
                self.head_status.config(
                    text="🎯  Head Forward" if is_fwd else "⚠  Head Turned",
                    fg=SUCCESS if is_fwd else WARNING)

            # ── Draw load history chart ───────────────────────────────────────
            self._draw_chart()

            # ── Camera feed ───────────────────────────────────────────────────
            if frame is not None:
                img   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img   = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(img)
                self.cam_label.imgtk = imgtk
                self.cam_label.config(image=imgtk, text="")

        except tk.TclError:
            pass

    def _draw_chart(self):
        """Draw load history line chart"""
        try:
            self.chart_canvas.delete("all")
            w = self.chart_canvas.winfo_width()
            h = self.chart_canvas.winfo_height()
            if w < 10 or h < 10:
                return

            pad = 10
            data = self.load_history[-w:]
            n    = len(data)
            if n < 2:
                return

            # Grid lines
            for level, color in [(0.3, "#1A3A1A"), (0.55, "#3A3A0A"),
                                   (0.75, "#3A1A0A"), (1.0, "#3A0A0A")]:
                y = h - pad - int(level * (h - 2*pad))
                self.chart_canvas.create_line(
                    pad, y, w-pad, y, fill=color, width=1)

            # Line chart
            pts = []
            for i, val in enumerate(data):
                x = pad + int(i / (n-1) * (w - 2*pad))
                y = h - pad - int(val * (h - 2*pad))
                pts.append((x, y))

            if len(pts) >= 2:
                for i in range(len(pts)-1):
                    val   = data[i]
                    if val < 0.30:   lc = SUCCESS
                    elif val < 0.55: lc = WARNING
                    elif val < 0.75: lc = "#FF6B35"
                    else:            lc = CRITICAL
                    self.chart_canvas.create_line(
                        pts[i][0], pts[i][1],
                        pts[i+1][0], pts[i+1][1],
                        fill=lc, width=2)

            # Current value dot
            if pts:
                lx, ly = pts[-1]
                self.chart_canvas.create_oval(
                    lx-4, ly-4, lx+4, ly+4,
                    fill=self.current_result["color"],
                    outline="")

        except Exception:
            pass

    def _trigger_alert(self, result):
        """Trigger alert sound + overlay + log"""
        self.alert_count += 1
        play_alert(result["name"])
        show_alert_overlay(self.root, result["name"],
                            result["action"], result["color"])

        # Add to alert tree
        now = datetime.now().strftime("%H:%M:%S")
        self.alert_tree.insert("", 0,
            values=(now, result["name"], result["action"]))
        children = self.alert_tree.get_children()
        if len(children) > 6:
            self.alert_tree.delete(children[-1])

        # Save to DB
        threading.Thread(
            target=self.cognitive_engine.save_alert,
            args=(self.session_id, f"{result['name']} Load Alert", result),
            daemon=True).start()

    def update_clock(self):
        try:
            self.clock_var.set(
                datetime.now().strftime("%A  %d %b %Y  |  %H:%M:%S"))
            self.root.after(1000, self.update_clock)
        except tk.TclError:
            pass

    def on_close(self):
        self.running = False
        # End session in DB
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            avg    = np.mean(self.load_history) if self.load_history else 0
            mx     = max(self.load_history)     if self.load_history else 0
            elapsed = int(time.time() - self.session_start)
            cursor.execute("""
                UPDATE DrivingSessions SET
                    EndTime=GETDATE(), AvgCognitiveLoad=?,
                    MaxCognitiveLoad=?, AlertsTriggered=?,
                    SessionDuration=?
                WHERE SessionID=?
            """, (avg, mx, self.alert_count, elapsed, self.session_id))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"[ERROR] End session: {db_err}")

        self.cap.release()
        self.root.destroy()
        import main_app
        main_app.launch()


def launch(driver_name, session_id):
    root = tk.Tk()
    DriverMonitor(root, driver_name, session_id)
    root.mainloop()